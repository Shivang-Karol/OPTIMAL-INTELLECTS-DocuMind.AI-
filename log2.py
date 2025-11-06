import asyncio
import io
import os
import time
from datetime import datetime, timedelta
import faiss
import fitz  # PyMuPDF
import httpx
import numpy as np
import tiktoken
from dotenv import load_dotenv
from fastapi import FastAPI, Header, UploadFile, File, Form, HTTPException, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from openai import AsyncAzureOpenAI
from pydantic import BaseModel
from pymongo import MongoClient
from typing import List, Optional
import jwt
import bcrypt
from bson import ObjectId

# --- Basic Setup ---
load_dotenv()
app = FastAPI()

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# JWT Configuration
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24 * 7  # 7 days

security = HTTPBearer()

# --- Azure OpenAI Configuration ---
endpoint = os.getenv("OPENAI_API_BASE")
chat_deployment = os.getenv("OPENAI_DEPLOYMENT", "gpt-4o-mini")
embedding_deployment = os.getenv("OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-large")
api_key = os.getenv("OPENAI_API_KEY")
api_version = os.getenv("OPENAI_API_VERSION")

client = AsyncAzureOpenAI(api_version=api_version, azure_endpoint=endpoint, api_key=api_key, max_retries=5)

# --- MongoDB Setup ---
mongo_uri = os.getenv("MONGO_URI")
mongo_client = MongoClient(mongo_uri)
mongo_client.admin.command('ping')
db = mongo_client["hackrx_logs"]

# Collections
users_collection = db["users"]
sessions_collection = db["chat_sessions"]
messages_collection = db["chat_messages"]
logs_collection = db["CheckRequest"]

# --- Pydantic Models ---
class QueryRequest(BaseModel):
    documents: str
    questions: list[str]

class UserRegister(BaseModel):
    username: str
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class CreateSession(BaseModel):
    title: str
    document_id: Optional[str] = None
    document_url: Optional[str] = None

# --- In-Memory Caches ---
document_cache = {}  # {doc_id: (chunks, faiss_index)}

# --- Helper Functions ---
def create_jwt_token(user_id: str, email: str) -> str:
    """Create JWT token for user"""
    payload = {
        "user_id": user_id,
        "email": email,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_jwt_token(token: str) -> dict:
    """Verify JWT token and return payload"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user from JWT token"""
    token = credentials.credentials
    payload = verify_jwt_token(token)
    user = users_collection.find_one({"_id": ObjectId(payload["user_id"])})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

# --- Authentication Routes ---
@app.post("/api/v1/auth/register")
async def register(user_data: UserRegister):
    """Register new user"""
    start_time = time.time()
    print(f"\n[AUTH] Registration attempt for: {user_data.email}")
    
    # Check if user exists
    if users_collection.find_one({"email": user_data.email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    
    if users_collection.find_one({"username": user_data.username}):
        raise HTTPException(status_code=400, detail="Username already taken")
    
    # Create user
    user_doc = {
        "username": user_data.username,
        "email": user_data.email,
        "password": hash_password(user_data.password),
        "created_at": datetime.utcnow(),
        "last_login": datetime.utcnow()
    }
    
    result = users_collection.insert_one(user_doc)
    user_id = str(result.inserted_id)
    
    # Create JWT token
    token = create_jwt_token(user_id, user_data.email)
    
    print(f"[AUTH] User registered successfully in {time.time() - start_time:.2f}s")
    
    return {
        "success": True,
        "token": token,
        "user": {
            "id": user_id,
            "username": user_data.username,
            "email": user_data.email
        }
    }

@app.post("/api/v1/auth/login")
async def login(credentials: UserLogin):
    """Login user"""
    start_time = time.time()
    print(f"\n[AUTH] Login attempt for: {credentials.email}")
    
    # Find user
    user = users_collection.find_one({"email": credentials.email})
    if not user or not verify_password(credentials.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Update last login
    users_collection.update_one(
        {"_id": user["_id"]},
        {"$set": {"last_login": datetime.utcnow()}}
    )
    
    # Create JWT token
    token = create_jwt_token(str(user["_id"]), user["email"])
    
    print(f"[AUTH] Login successful in {time.time() - start_time:.2f}s")
    
    return {
        "success": True,
        "token": token,
        "user": {
            "id": str(user["_id"]),
            "username": user["username"],
            "email": user["email"]
        }
    }

@app.get("/api/v1/auth/me")
async def get_me(user = Depends(get_current_user)):
    """Get current user info"""
    return {
        "success": True,
        "user": {
            "id": str(user["_id"]),
            "username": user["username"],
            "email": user["email"]
        }
    }

# --- Session Management Routes ---
@app.post("/api/v1/sessions/create")
async def create_session(session_data: CreateSession, user = Depends(get_current_user)):
    """Create new chat session"""
    start_time = time.time()
    print(f"\n[SESSION] Creating new session for user: {user['username']}")
    
    session_doc = {
        "user_id": str(user["_id"]),
        "title": session_data.title,
        "document_id": session_data.document_id,
        "document_url": session_data.document_url,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "message_count": 0
    }
    
    result = sessions_collection.insert_one(session_doc)
    session_id = str(result.inserted_id)
    
    print(f"[SESSION] Session created: {session_id}")
    print(f"[SESSION] Document ID: {session_data.document_id}")
    print(f"[SESSION] Document URL: {session_data.document_url}")
    print(f"[SESSION] Created in {time.time() - start_time:.2f}s")
    
    return {
        "success": True,
        "session_id": session_id,
        "session": {
            "id": session_id,
            "title": session_data.title,
            "created_at": session_doc["created_at"].isoformat(),
            "message_count": 0
        }
    }

@app.get("/api/v1/sessions/list")
async def list_sessions(user = Depends(get_current_user)):
    """Get all sessions for current user"""
    start_time = time.time()
    print(f"\n[SESSION] Fetching sessions for user: {user['username']}")
    
    sessions = list(sessions_collection.find(
        {"user_id": str(user["_id"])}
    ).sort("updated_at", -1))
    
    session_list = []
    for session in sessions:
        session_list.append({
            "id": str(session["_id"]),
            "title": session["title"],
            "message_count": session.get("message_count", 0),
            "created_at": session["created_at"].isoformat(),
            "updated_at": session["updated_at"].isoformat()
        })
    
    print(f"[SESSION] Fetched {len(session_list)} sessions in {time.time() - start_time:.2f}s")
    
    return {
        "success": True,
        "sessions": session_list
    }

@app.get("/api/v1/sessions/{session_id}/messages")
async def get_session_messages(session_id: str, user = Depends(get_current_user)):
    """Get all messages in a session"""
    start_time = time.time()
    print(f"\n[SESSION] Fetching messages for session: {session_id}")
    
    # Verify session belongs to user
    session = sessions_collection.find_one({
        "_id": ObjectId(session_id),
        "user_id": str(user["_id"])
    })
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get messages
    messages = list(messages_collection.find(
        {"session_id": session_id}
    ).sort("created_at", 1))
    
    message_list = []
    for msg in messages:
        message_list.append({
            "id": str(msg["_id"]),
            "type": msg["type"],
            "content": msg["content"],
            "processing_time": msg.get("processing_time"),
            "created_at": msg["created_at"].isoformat()
        })
    
    print(f"[SESSION] Fetched {len(message_list)} messages in {time.time() - start_time:.2f}s")
    
    return {
        "success": True,
        "session": {
            "id": str(session["_id"]),
            "title": session["title"],
            "document_id": session.get("document_id"),
            "document_url": session.get("document_url")
        },
        "messages": message_list
    }

@app.delete("/api/v1/sessions/{session_id}")
async def delete_session(session_id: str, user = Depends(get_current_user)):
    """Delete a session and all its messages"""
    start_time = time.time()
    print(f"\n[SESSION] Deleting session: {session_id}")
    
    # Verify session belongs to user
    result = sessions_collection.delete_one({
        "_id": ObjectId(session_id),
        "user_id": str(user["_id"])
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Delete all messages
    messages_result = messages_collection.delete_many({"session_id": session_id})
    
    print(f"[SESSION] Session deleted with {messages_result.deleted_count} messages in {time.time() - start_time:.2f}s")
    
    return {"success": True}

# --- Document Upload Route ---
@app.post("/api/v1/upload-pdf")
async def upload_pdf(file: UploadFile = File(...), user = Depends(get_current_user)):
    """Handle PDF file uploads"""
    start_time = time.time()
    print(f"\n[UPLOAD] User {user['username']} uploading: {file.filename}")
    
    try:
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")
        
        # Read file content
        t0 = time.time()
        content = await file.read()
        print(f"[UPLOAD] File read in {time.time() - t0:.2f}s ({len(content)} bytes)")

        if len(content) > 100 * 1024 * 1024:  # 100MB limit
            raise HTTPException(status_code=400, detail="File size must be less than 100MB")

        # Generate unique identifier
        file_id = f"upload_{int(time.time())}_{user['username']}_{file.filename}"
        
        # Store in temporary cache
        temp_storage_path = f"temp_uploads/{file_id}"
        os.makedirs("temp_uploads", exist_ok=True)
        
        t1 = time.time()
        with open(temp_storage_path, "wb") as f:
            f.write(content)
        print(f"[UPLOAD] File saved to {temp_storage_path} in {time.time() - t1:.2f}s")
        
        print(f"[UPLOAD] Total upload time: {time.time() - start_time:.2f}s")
        
        return JSONResponse({
            "success": True,
            "file_id": file_id,
            "filename": file.filename,
            "message": "PDF uploaded successfully"
        })
    
    except Exception as e:
        print(f"[UPLOAD] Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")

# --- Multi-Agentic RAG Chat Endpoint ---
@app.post("/api/v1/chat")
async def chat_endpoint(
    question: str = Form(...),
    session_id: str = Form(...),
    user = Depends(get_current_user)
):
    """
    Multi-Agentic RAG Chat Endpoint
    Agents:
    1. Question Understanding Agent
    2. History Analysis Agent
    3. Context Retrieval Agent
    4. Answer Generation Agent
    """
    overall_start = time.time()
    print(f"\n{'='*80}")
    print(f"[CHAT] User: {user['username']} | Session: {session_id}")
    print(f"[CHAT] Question: {question}")
    print(f"{'='*80}")
    
    try:
        # Verify session belongs to user
        session = sessions_collection.find_one({
            "_id": ObjectId(session_id),
            "user_id": str(user["_id"])
        })
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        print(f"[CHAT] Session found - Document ID: {session.get('document_id')}, Document URL: {session.get('document_url')}")
        
        # Save user message
        user_message = {
            "session_id": session_id,
            "type": "user",
            "content": question,
            "created_at": datetime.utcnow()
        }
        messages_collection.insert_one(user_message)
        
        # === AGENT 1: Question Understanding ===
        t_agent1_start = time.time()
        print(f"\n[AGENT 1] Question Understanding Agent - Starting...")
        understood_question, intent = await question_understanding_agent(question)
        t_agent1 = time.time() - t_agent1_start
        print(f"[AGENT 1] Understood Question: {understood_question}")
        print(f"[AGENT 1] Intent: {intent}")
        print(f"[AGENT 1] Completed in {t_agent1:.2f}s")
        
        # === AGENT 2: History Analysis ===
        t_agent2_start = time.time()
        print(f"\n[AGENT 2] History Analysis Agent - Starting...")
        chat_history = await get_chat_history(session_id)
        relevant_history = await history_analysis_agent(question, chat_history)
        t_agent2 = time.time() - t_agent2_start
        print(f"[AGENT 2] Found {len(relevant_history)} relevant history items")
        print(f"[AGENT 2] Completed in {t_agent2:.2f}s")
        
        # === AGENT 3: Document Processing & Retrieval ===
        t_agent3_start = time.time()
        print(f"\n[AGENT 3] Context Retrieval Agent - Starting...")
        
        # Get document source - FIXED
        doc_source = None
        is_local_file = False
        
        if session.get("document_id"):
            doc_source = f"temp_uploads/{session['document_id']}"
            is_local_file = True
            print(f"[AGENT 3] Document source (local file): {doc_source}")
        elif session.get("document_url"):
            doc_source = session["document_url"]
            is_local_file = False
            print(f"[AGENT 3] Document source (URL): {doc_source}")
        else:
            raise HTTPException(status_code=400, detail="No document associated with session")
        
        # Check cache
        if doc_source in document_cache:
            print(f"[AGENT 3] Using cached document embeddings")
            chunks, faiss_index = document_cache[doc_source]
        else:
            print(f"[AGENT 3] Processing document for first time...")
            
            # Extract text - FIXED
            t_extract = time.time()
            if is_local_file:
                # Verify file exists
                if not os.path.exists(doc_source):
                    print(f"[AGENT 3] ERROR: File not found at {doc_source}")
                    raise HTTPException(
                        status_code=404, 
                        detail=f"Uploaded file not found. Please upload the document again."
                    )
                print(f"[AGENT 3] File exists, extracting text from local PDF...")
                text = await extract_text_from_pdf_local(doc_source)
                print(f"[AGENT 3] Successfully extracted text from local file")
            else:
                print(f"[AGENT 3] Downloading and extracting text from URL...")
                text = await extract_text_from_pdf_fast(doc_source)
                print(f"[AGENT 3] Successfully extracted text from URL")
            
            print(f"[AGENT 3] Text extraction: {time.time() - t_extract:.2f}s")
            print(f"[AGENT 3] Extracted {len(text)} characters")
            
            # Chunk
            t_chunk = time.time()
            chunks = smart_chunk_text(text)
            print(f"[AGENT 3] Chunking: {time.time() - t_chunk:.2f}s")
            print(f"[AGENT 3] Created {len(chunks)} chunks")
            
            # Embed
            t_embed = time.time()
            chunk_embeddings = await get_embeddings(chunks, model=embedding_deployment)
            print(f"[AGENT 3] Embedding generation: {time.time() - t_embed:.2f}s")
            print(f"[AGENT 3] Generated {len(chunk_embeddings)} embeddings")
            
            # Create FAISS index
            t_faiss = time.time()
            embedding_dim = chunk_embeddings.shape[1]
            faiss_index = faiss.IndexFlatL2(embedding_dim)
            faiss_index.add(chunk_embeddings)
            print(f"[AGENT 3] FAISS index creation: {time.time() - t_faiss:.2f}s")
            print(f"[AGENT 3] Index dimension: {embedding_dim}")
            
            # Cache
            document_cache[doc_source] = (chunks, faiss_index)
            print(f"[AGENT 3] Document cached for future queries")
        
        # Semantic search with expanded questions
        t_search = time.time()
        expanded_questions = expand_question_semantics(understood_question)
        print(f"[AGENT 3] Expanded question into {len(expanded_questions)} variations")
        
        question_embeddings = await get_embeddings(expanded_questions, model=embedding_deployment)
        avg_embedding = np.mean(question_embeddings, axis=0, keepdims=True)
        
        retrieved_chunks = search_faiss(avg_embedding, faiss_index, chunks, k=21)
        top_chunks = rerank_chunks_by_keyword_overlap(understood_question, retrieved_chunks, top_k=21)
        print(f"[AGENT 3] Semantic search & reranking: {time.time() - t_search:.2f}s")
        print(f"[AGENT 3] Retrieved {len(top_chunks)} most relevant chunks")
        
        t_agent3 = time.time() - t_agent3_start
        print(f"[AGENT 3] Completed in {t_agent3:.2f}s")
        
        # === AGENT 4: Answer Generation ===
        t_agent4_start = time.time()
        print(f"\n[AGENT 4] Answer Generation Agent - Starting...")
        
        answer = await answer_generation_agent(
            original_question=question,
            understood_question=understood_question,
            intent=intent,
            document_context=top_chunks,
            chat_history=relevant_history
        )
        
        t_agent4 = time.time() - t_agent4_start
        print(f"[AGENT 4] Answer generated ({len(answer)} characters)")
        print(f"[AGENT 4] Completed in {t_agent4:.2f}s")
        
        # Save bot message
        total_time = time.time() - overall_start
        bot_message = {
            "session_id": session_id,
            "type": "bot",
            "content": answer,
            "processing_time": f"{total_time:.2f}s",
            "created_at": datetime.utcnow(),
            "metadata": {
                "intent": intent,
                "chunks_used": len(top_chunks),
                "history_items": len(relevant_history),
                "agent_timings": {
                    "question_understanding": f"{t_agent1:.2f}s",
                    "history_analysis": f"{t_agent2:.2f}s",
                    "context_retrieval": f"{t_agent3:.2f}s",
                    "answer_generation": f"{t_agent4:.2f}s"
                }
            }
        }
        messages_collection.insert_one(bot_message)
        
        # Update session
        sessions_collection.update_one(
            {"_id": ObjectId(session_id)},
            {
                "$set": {"updated_at": datetime.utcnow()},
                "$inc": {"message_count": 2}
            }
        )
        
        print(f"\n{'='*80}")
        print(f"[CHAT] Total Processing Time: {total_time:.2f}s")
        print(f"[CHAT] Breakdown:")
        print(f"  - Question Understanding: {t_agent1:.2f}s ({t_agent1/total_time*100:.1f}%)")
        print(f"  - History Analysis: {t_agent2:.2f}s ({t_agent2/total_time*100:.1f}%)")
        print(f"  - Context Retrieval: {t_agent3:.2f}s ({t_agent3/total_time*100:.1f}%)")
        print(f"  - Answer Generation: {t_agent4:.2f}s ({t_agent4/total_time*100:.1f}%)")
        print(f"{'='*80}\n")
        
        return JSONResponse({
            "success": True,
            "answer": answer,
            "processing_time": f"{total_time:.2f}s",
            "question": question,
            "metadata": {
                "intent": intent,
                "chunks_used": len(top_chunks),
                "history_items_referenced": len(relevant_history)
            }
        })
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"[CHAT] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error processing question: {str(e)}")

# --- Multi-Agent Functions ---
async def question_understanding_agent(question: str) -> tuple[str, str]:
    """
    Agent 1: Understands the question and determines intent
    Returns: (understood_question, intent)
    """
    prompt = f"""You are a Question Understanding Agent. Analyze the user's question and:
1. Rephrase it for better clarity and semantic search
2. Identify the intent (e.g., "factual_query", "clarification", "follow_up", "comparison", "summarization")

Question: {question}

Respond in this format:
UNDERSTOOD: [rephrased question]
INTENT: [intent type]
"""
    
    response = await client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=150,
        model=chat_deployment
    )
    
    result = response.choices[0].message.content.strip()
    lines = result.split('\n')
    
    understood = question  # Default
    intent = "factual_query"  # Default
    
    for line in lines:
        if line.startswith("UNDERSTOOD:"):
            understood = line.replace("UNDERSTOOD:", "").strip()
        elif line.startswith("INTENT:"):
            intent = line.replace("INTENT:", "").strip()
    
    return understood, intent

async def get_chat_history(session_id: str) -> list[dict]:
    """Get chat history for a session"""
    messages = list(messages_collection.find(
        {"session_id": session_id}
    ).sort("created_at", 1).limit(20))  # Last 20 messages
    
    history = []
    for msg in messages:
        history.append({
            "type": msg["type"],
            "content": msg["content"],
            "timestamp": msg["created_at"]
        })
    
    return history

async def history_analysis_agent(question: str, chat_history: list[dict]) -> list[dict]:
    """
    Agent 2: Analyzes chat history to find relevant context
    Returns: List of relevant history items
    """
    if not chat_history or len(chat_history) < 2:
        return []
    
    # Format history for analysis
    history_text = "\n".join([
        f"{msg['type'].upper()}: {msg['content']}"
        for msg in chat_history[-10:]  # Last 5 exchanges
    ])
    
    prompt = f"""You are a History Analysis Agent. Determine if the current question references or relates to previous conversation.

Chat History:
{history_text}

Current Question: {question}

Does this question reference previous conversation? Answer YES or NO, then explain which parts are relevant.

Format:
REFERENCES_HISTORY: [YES/NO]
RELEVANT_CONTEXT: [brief explanation]
"""
    
    response = await client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=200,
        model=chat_deployment
    )
    
    result = response.choices[0].message.content.strip()
    
    if "REFERENCES_HISTORY: YES" in result:
        # Return last few relevant exchanges
        return chat_history[-6:]  # Last 3 exchanges (user + bot)
    
    return []

async def answer_generation_agent(
    original_question: str,
    understood_question: str,
    intent: str,
    document_context: list[str],
    chat_history: list[dict]
) -> str:
    """
    Agent 4: Generates the final answer using all context
    """
    # Format document context
    doc_context_text = "\n---\n".join(document_context)
    
    # Format chat history
    history_context = ""
    if chat_history:
        history_context = "\n\nPREVIOUS CONVERSATION:\n" + "\n".join([
            f"{msg['type'].upper()}: {msg['content']}"
            for msg in chat_history[-6:]
        ])
    
    prompt = f"""You are an AI Assistant specializing in document analysis and question answering. You have access to:
1. The current document's relevant sections
2. Previous conversation history (if applicable)

Your task is to provide accurate, well-formatted, and contextually relevant answers.

FORMATTING GUIDELINES:
1. Use **markdown formatting** for better readability
2. Use **bold** for important terms or concepts
3. Use numbered lists (1., 2., 3.) for sequential information
4. Use bullet points (-, *) for non-sequential lists
5. Use ```sql or ```python code blocks for queries or code examples
6. Use `inline code` for short code snippets, table names, or column names
7. Break long paragraphs into smaller ones for readability

CONTENT GUIDELINES:
1. **Primary Source**: Always prioritize information from the document context
2. **Conversation Awareness**: If this is a follow-up question, reference previous answers naturally
3. **Clarity**: Be concise but comprehensive
4. **Keywords**: Use terminology from the document when possible
5. **Semantic Understanding**: Interpret related concepts intelligently
6. **Examples**: When explaining SQL queries or code, provide formatted examples

INTENT: {intent}
- If "follow_up": Connect to previous answers
- If "clarification": Expand on previous information with examples
- If "comparison": Use tables or lists to compare
- If "factual_query": Provide direct, well-structured information
- If "summarization": Use bullet points and sections

---
DOCUMENT CONTEXT:
{doc_context_text}
{history_context}
---

ORIGINAL QUESTION: {original_question}
UNDERSTOOD AS: {understood_question}

Provide a clear, well-formatted answer using markdown:
"""
    
    response = await client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=2000,  # Increased for formatted responses
        model=chat_deployment
    )
    
    return response.choices[0].message.content.strip()

# --- Original Endpoint (Keep for backward compatibility) ---
@app.post("/api/v1/hackrx/run")
async def hackrx_run(request: QueryRequest, authorization: str = Header(None)):
    request_data = request.dict()
    log_entry = {
        "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
        "auth_header": authorization,
        "request_data": request_data
    }
    logs_collection.insert_one(log_entry)

    doc_url = request.documents
    start_time = time.time()

    if doc_url in document_cache:
        chunks, faiss_index = document_cache[doc_url]
    else:
        t0 = time.time()
        text = await extract_text_from_pdf_fast(doc_url)
        print(f"[Time] PDF text extraction: {time.time() - t0:.2f}s")

        t1 = time.time()
        chunks = smart_chunk_text(text)
        print(f"[Time] Smart chunking: {time.time() - t1:.2f}s")

        t2 = time.time()
        chunk_embeddings = await get_embeddings(chunks, model=embedding_deployment)
        print(f"[Time] Embedding generation: {time.time() - t2:.2f}s")

        t3 = time.time()
        embedding_dim = chunk_embeddings.shape[1]
        faiss_index = faiss.IndexFlatL2(embedding_dim)
        faiss_index.add(chunk_embeddings)
        print(f"[Time] FAISS index creation: {time.time() - t3:.2f}s")

        document_cache[doc_url] = (chunks, faiss_index)

    tasks = [answer_question_simple(q, chunks, faiss_index) for q in request.questions]
    answers = await asyncio.gather(*tasks)

    print(f"[Time] Overall API call time: {time.time() - start_time:.2f}s")
    return {"answers": answers}

async def answer_question_simple(question: str, chunks: list[str], faiss_index: faiss.Index) -> str:
    """Simple answer for backward compatibility"""
    expanded_questions = expand_question_semantics(question)
    question_embeddings = await get_embeddings(expanded_questions, model=embedding_deployment)
    avg_embedding = np.mean(question_embeddings, axis=0, keepdims=True)
    retrieved_chunks = search_faiss(avg_embedding, faiss_index, chunks, k=21)
    top_chunks = rerank_chunks_by_keyword_overlap(question, retrieved_chunks, top_k=21)
    context = "\n---\n".join(top_chunks)
    
    prompt = f"""Answer this question based on the document context provided.
Keep the answer concise (1-2 sentences) and use keywords from the document.

Context:
{context}

Question: {question}
Answer:"""
    
    response = await client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        max_tokens=300,
        model=chat_deployment
    )
    return response.choices[0].message.content.strip()

# --- Home Page Route ---
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Render the home page"""
    return templates.TemplateResponse("index.html", {"request": request})

# --- Helper Functions (Existing) ---
def expand_question_semantics(question: str) -> list[str]:
    synonyms = {
        "IVF": ["in vitro fertilization", "assisted reproduction", "ART", "infertility treatment"],
        "settled": ["paid", "reimbursed", "processed"],
        "hospitalization": ["hospital admission", "inpatient care"],
        "SQL": ["structured query language", "database query", "SQL statement"],
        "query": ["queries", "statement", "command"],
    }
    expanded = [question]
    for term, alts in synonyms.items():
        if term.lower() in question.lower():
            for alt in alts:
                expanded.append(question.replace(term, alt))
    return list(set(expanded))

async def extract_text_from_pdf_local(file_path: str) -> str:
    """Extract text from locally stored PDF"""
    def extract_text():
        with fitz.open(file_path) as doc:
            return "\n".join(page.get_text() for page in doc)
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, extract_text)

async def extract_text_from_pdf_fast(pdf_url: str) -> str:
    """Extract text from PDF URL"""
    async with httpx.AsyncClient() as http_client:
        response = await http_client.get(pdf_url, timeout=30.0)
        response.raise_for_status()
    pdf_file_stream = io.BytesIO(response.content)
    def extract_text():
        with fitz.open(stream=pdf_file_stream, filetype="pdf") as doc:
            return "\n".join(page.get_text() for page in doc)
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, extract_text)

def smart_chunk_text(text: str, max_len: int = 800) -> list[str]:
    """Smart text chunking"""
    paras = [p.strip() for p in text.split('\n') if p.strip()]
    chunks, buffer = [], ""
    for p in paras:
        if len(buffer) + len(p) < max_len:
            buffer += " " + p
        else:
            if buffer:
                chunks.append(buffer.strip())
            buffer = p
    if buffer:
        chunks.append(buffer.strip())
    return [c for c in chunks if len(c.split()) > 5]

async def get_embeddings(texts: list[str], model: str, batch_size: int = 20) -> np.ndarray:
    """Generate embeddings for texts"""
    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        response = await client.embeddings.create(input=batch, model=model)
        all_embeddings.extend([item.embedding for item in response.data])
    return np.array(all_embeddings, dtype=np.float32)

def search_faiss(query_embedding: np.ndarray, index: faiss.Index, chunks: list[str], k: int = 21):
    """Search FAISS index"""
    distances, indices = index.search(query_embedding, k)
    return [chunks[i] for i in indices[0] if i < len(chunks)]

def rerank_chunks_by_keyword_overlap(question: str, chunks: list[str], top_k: int = 21) -> list[str]:
    """Rerank chunks by keyword overlap"""
    q_words = set(question.lower().split())
    ranked = sorted(chunks, key=lambda c: sum(w in c.lower() for w in q_words), reverse=True)
    return ranked[:top_k]