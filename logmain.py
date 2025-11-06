"""
RAG-Based Document & API Question Answering System (MERGED VERSION)
====================================================================
This system combines the best features from both implementations:
- Multi-agent RAG system (4 agents for better accuracy)
- User authentication with JWT tokens
- Session management per user
- PDF upload support
- Chat history with IBM Granite 3.1-3B summarization
- FAISS vector search
- Azure OpenAI embeddings and chat completions
- MongoDB for logging and analytics
"""

# ============================================================================
# IMPORTS - External dependencies for various functionalities
# ============================================================================

import asyncio        # Async/await support for concurrent operations
import io             # Handle binary streams (PDF downloads)
import os             # Access environment variables
import time           # Track execution time and timestamps
import re             # Regular expressions for text normalization
import uuid           # Generate unique session IDs
import jwt            # JWT token generation and verification
import bcrypt         # Password hashing
from datetime import datetime, timedelta

import faiss          # Facebook AI Similarity Search - vector database for fast retrieval
import fitz           # PyMuPDF - PDF text extraction library
import httpx          # Async HTTP client for API calls and PDF downloads
import numpy as np    # Numerical operations on embeddings

from dotenv import load_dotenv                # Load environment variables from .env file
from fastapi import FastAPI, Header, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware  # CORS support for frontend
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from openai import AsyncAzureOpenAI           # Azure OpenAI client for embeddings and chat
from pydantic import BaseModel                # Data validation for API request/response
from pymongo import MongoClient               # MongoDB client for logging
from bson import ObjectId                     # MongoDB ObjectId handling
from typing import Optional
from bs4 import BeautifulSoup                 # HTML parsing for web scraping (secret token extraction)

# ============================================================================
# BASIC SETUP
# ============================================================================

load_dotenv()           # Load .env file containing API keys and configuration
app = FastAPI()         # Initialize FastAPI application for REST endpoints

# ============================================================================
# CORS CONFIGURATION - Allow frontend to access backend
# ============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# JWT Configuration
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24 * 7  # 7 days

security = HTTPBearer()

# ============================================================================
# AZURE OPENAI CONFIGURATION
# ============================================================================
# Configure connection to Azure OpenAI services for:
# 1. Chat completions (GPT-4o-mini) - generating answers
# 2. Embeddings (text-embedding-3-large) - converting text to vectors for similarity search

endpoint = os.getenv("OPENAI_API_BASE")                                                 # Azure OpenAI endpoint URL
chat_deployment = os.getenv("OPENAI_DEPLOYMENT", "gpt-4o-mini")                         # Deployment name for chat model
embedding_deployment = os.getenv("OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-large") # Deployment name for embeddings
api_key = os.getenv("OPENAI_API_KEY")                                                   # API key for authentication
api_version = os.getenv("OPENAI_API_VERSION")                                           # API version (e.g., 2024-02-15-preview)

# Initialize async Azure OpenAI client with retry logic (max 5 retries for robustness)
client = AsyncAzureOpenAI(api_version=api_version, azure_endpoint=endpoint, api_key=api_key, max_retries=5)

# ============================================================================
# IBM GRANITE 3.1 LOCAL MODEL CONFIGURATION (Optional)
# ============================================================================
# IBM Granite 3.1-3B (800M instruct) for local summarization
# This will run locally using transformers/ollama instead of cloud API

GRANITE_MODEL_PATH = os.getenv("GRANITE_MODEL_PATH", "ibm-granite/granite-3.1-3b-a800m-instruct")  # HuggingFace model ID or local path
USE_GRANITE = os.getenv("USE_GRANITE", "false").lower() == "true"     # Enable/disable Granite (default: false)

# ============================================================================
# MONGODB SETUP
# ============================================================================
# MongoDB Atlas is used to log all requests, responses, and analytics data
# Database: hackrx_logs
# Collections:
#   - users: User accounts with authentication
#   - chat_sessions: Chat sessions per user
#   - chat_messages: Individual messages in sessions
#   - ChatSessions: Legacy chat history (kept for backward compatibility)
#   - CheckRequest: Legacy logs (kept for backward compatibility)

mongo_uri = os.getenv("MONGO_URI")          # MongoDB connection string from environment

# Try to connect to MongoDB with error handling
try:
    mongo_client = MongoClient(
        mongo_uri,
        serverSelectionTimeoutMS=5000,  # 5 second timeout
        connectTimeoutMS=5000
    )
    mongo_client.admin.command('ping')           # Test connection to ensure MongoDB is reachable
    db = mongo_client["hackrx_logs"]             # Select database
    
    # Collections
    users_collection = db["users"]
    sessions_collection = db["chat_sessions"]
    messages_collection = db["chat_messages"]
    chat_sessions = db["ChatSessions"]           # Legacy collection for backward compatibility
    collection = db["CheckRequest"]              # Legacy collection for backward compatibility
    
    # Create indexes for better query performance
    chat_sessions.create_index("session_id")
    chat_sessions.create_index([("session_id", 1), ("timestamp", 1)])
    sessions_collection.create_index("user_id")
    messages_collection.create_index("session_id")
    
    print("[MongoDB] ✅ Connected successfully!")
    
except Exception as e:
    print(f"[MongoDB] ⚠️ Connection failed: {str(e)}")
    print("[MongoDB] Server will continue without database features")
    print("[MongoDB] Please check:")
    print("  1. Your internet connection")
    print("  2. MongoDB Atlas cluster is running")
    print("  3. MONGO_URI in .env file is correct")
    print("  4. Your IP is whitelisted in MongoDB Atlas")
    
    # Create dummy collections to prevent errors
    mongo_client = None
    db = None
    users_collection = None
    sessions_collection = None
    messages_collection = None
    chat_sessions = None
    collection = None

# ============================================================================
# PYDANTIC MODELS - Request/Response validation
# ============================================================================
# Defines the structure of incoming API requests and responses

class QueryRequest(BaseModel):
    documents: str           # URL to PDF document or special endpoint
    questions: list[str]     # List of questions to answer about the document
    session_id: str = None   # Optional session ID for chat history tracking

class HistoryRequest(BaseModel):
    session_id: str          # Session ID to retrieve chat history

class SummarizeRequest(BaseModel):
    session_id: str          # Session ID to summarize
    use_granite: bool = True # Use IBM Granite model for summarization (default: True)

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

# ============================================================================
# DOCUMENT CACHE - Performance optimization
# ============================================================================
# In-memory cache to store processed documents (chunks + FAISS index)
# Avoids re-processing the same PDF multiple times
# Key: document URL, Value: (text_chunks, faiss_index)

document_cache = {}

# ============================================================================
# HELPER FUNCTIONS - Session Management & Authentication
# ============================================================================

def generate_session_id() -> str:
    """Generate a unique session ID for chat tracking."""
    return f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

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

# ============================================================================
# STATIC FILES & ROOT ENDPOINT
# ============================================================================

@app.get("/")
async def root():
    """Serve the main page"""
    return FileResponse("static/Index.html")

@app.get("/login")
async def login_page():
    """Serve the login page"""
    return FileResponse("static/LoginRegister.html")

@app.get("/upload")
async def upload_page():
    """Serve the upload page"""
    return FileResponse("static/pdf upload.html")

# Mount static files AFTER defining routes
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except RuntimeError:
    # Static directory doesn't exist yet, skip mounting
    pass

# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================

@app.post("/api/v1/auth/register")
async def register(user_data: UserRegister):
    """Register new user"""
    start_time = time.time()
    print(f"\n[AUTH] Registration attempt for: {user_data.email}")
    
    # Check if MongoDB is connected
    if users_collection is None:
        raise HTTPException(
            status_code=503, 
            detail="Database is currently unavailable. Please contact administrator or try again later."
        )
    
    try:
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
    except HTTPException:
        raise
    except Exception as e:
        print(f"[AUTH] Registration error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

@app.post("/api/v1/auth/login")
async def login(credentials: UserLogin):
    """Login user"""
    start_time = time.time()
    print(f"\n[AUTH] Login attempt for: {credentials.email}")
    
    # Check if MongoDB is connected
    if users_collection is None:
        raise HTTPException(
            status_code=503, 
            detail="Database is currently unavailable. Please contact administrator or try again later."
        )
    
    try:
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
    except HTTPException:
        raise
    except Exception as e:
        print(f"[AUTH] Login error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")

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

# ============================================================================
# SESSION MANAGEMENT ENDPOINTS
# ============================================================================

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
    
    print(f"[SESSION] Session created: {session_id} in {time.time() - start_time:.2f}s")
    
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
async def list_user_sessions(user = Depends(get_current_user)):
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

# ============================================================================
# PDF UPLOAD ENDPOINT
# ============================================================================

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

        # No file size limit
        
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
        
        return {
            "success": True,
            "file_id": file_id,
            "filename": file.filename,
            "file_path": temp_storage_path,
            "message": "PDF uploaded successfully"
        }
    
    except Exception as e:
        print(f"[UPLOAD] Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")

# ============================================================================
# MULTI-AGENT CHAT ENDPOINT - Advanced RAG with 4 agents
# ============================================================================

@app.post("/api/v1/chat")
async def chat_endpoint(
    question: str = Form(...),
    session_id: str = Form(...),
    user = Depends(get_current_user)
):
    """
    Multi-Agentic RAG Chat Endpoint
    Agents:
    1. Question Understanding Agent - Rephrases questions and identifies intent
    2. History Analysis Agent - Determines if question references previous conversation
    3. Context Retrieval Agent - Retrieves relevant document chunks using FAISS
    4. Answer Generation Agent - Generates markdown-formatted answers
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
        chat_history = await get_chat_history_for_agent(session_id)
        relevant_history = await history_analysis_agent(question, chat_history)
        t_agent2 = time.time() - t_agent2_start
        print(f"[AGENT 2] Found {len(relevant_history)} relevant history items")
        print(f"[AGENT 2] Completed in {t_agent2:.2f}s")
        
        # === AGENT 3: Document Processing & Retrieval ===
        t_agent3_start = time.time()
        print(f"\n[AGENT 3] Context Retrieval Agent - Starting...")
        
        # Get document source
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
            
            # Extract text
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
            
            # Check if we have any chunks
            if len(chunks) == 0:
                print(f"[AGENT 3] ERROR: Document too short or empty. Extracted text: '{text[:100]}'")
                raise HTTPException(
                    status_code=400,
                    detail=f"Document is too short to process. Please upload a document with more content. (Extracted only {len(text)} characters)"
                )
            
            # Embed
            t_embed = time.time()
            chunk_embeddings = await get_embeddings(chunks, model=embedding_deployment)
            print(f"[AGENT 3] Embedding generation: {time.time() - t_embed:.2f}s")
            print(f"[AGENT 3] Generated {len(chunk_embeddings)} embeddings")
            
            # Verify embeddings are valid
            if len(chunk_embeddings) == 0 or chunk_embeddings.shape[0] == 0:
                print(f"[AGENT 3] ERROR: Failed to generate embeddings")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to generate embeddings for document chunks"
                )
            
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
        
        # Detect if user wants detailed/in-depth explanation
        detail_keywords = ['detail', 'detailed', 'depth', 'in-depth', 'comprehensive', 'thorough', 'complete', 'full', 'extensive', 'elaborate']
        wants_detail = any(keyword in question.lower() or keyword in understood_question.lower() for keyword in detail_keywords)
        
        # Adjust chunk retrieval based on detail level requested
        if wants_detail:
            k_chunks = 40  # More chunks for detailed explanations
            top_k_rerank = 35
            print(f"[AGENT 3] Detailed explanation requested - retrieving {k_chunks} chunks")
        else:
            k_chunks = 21  # Standard chunk count
            top_k_rerank = 21
        
        question_embeddings = await get_embeddings(expanded_questions, model=embedding_deployment)
        avg_embedding = np.mean(question_embeddings, axis=0, keepdims=True)
        
        retrieved_chunks = search_faiss(avg_embedding, faiss_index, chunks, k=k_chunks)
        top_chunks = rerank_chunks_by_keyword_overlap(understood_question, retrieved_chunks, top_k=top_k_rerank)
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

# ============================================================================
# MULTI-AGENT HELPER FUNCTIONS
# ============================================================================

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

async def get_chat_history_for_agent(session_id: str) -> list[dict]:
    """Get chat history for a session (for agent use)"""
    messages_list = list(messages_collection.find(
        {"session_id": session_id}
    ).sort("created_at", 1).limit(20))  # Last 20 messages
    
    history = []
    for msg in messages_list:
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
    
    prompt = f"""You are a document Q&A assistant. Answer questions using ONLY the document content provided below.

🎯 CRITICAL RULES:

1. **Use ONLY information from the DOCUMENT CONTEXT below** - never add external knowledge
2. **Use ALL the relevant information provided in the context** - don't hold back
3. **If a topic is mentioned in the document, answer about it using whatever content is available**
4. **Do NOT refuse to answer if the topic appears in the document** - share what's there
5. **Do NOT add facts, definitions, or explanations from outside the document**

📋 HOW TO RESPOND:

If the document has content about the topic:
→ Provide a COMPREHENSIVE answer using all available information from the context
→ Structure it clearly with bullet points, sections, or numbered lists
→ Include all relevant details, examples, and explanations found in the document

If the user asks for "detailed" or "in-depth" explanation:
→ Use MORE of the provided context to give a thorough response
→ Break down complex topics into multiple points
→ Include all subtopics and related information

If the document only mentions the topic as a heading/title with no details:
→ Say: "The document mentions '[topic]' as a section/topic, but doesn't provide detailed content about it in the portions I can see."

If the topic is NOT in the document at all:
→ Say: "I cannot find '[topic]' mentioned in this document."

 FORMAT:
- Use **bold** for key terms
- Use bullet points (-) for lists
- Use numbered lists for sequential information
- Break long content into sections with subheadings

---
DOCUMENT CONTEXT (Your ONLY source - {len(document_context)} chunks provided):
{doc_context_text}
{history_context}
---

QUESTION: {original_question}
INTENT: {intent}

Provide a comprehensive answer using ALL relevant information from the document context above. Do not add external knowledge:
"""
    
    response = await client.chat.completions.create(
        messages=[
            {"role": "system", "content": "You are a document Q&A assistant. You answer questions using ONLY the information provided in the document context. Never use external knowledge or facts from your training data. If the document mentions a topic, explain it using only what the document says."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,  # Lower temperature to reduce hallucination and stay focused on document
        max_tokens=2000,
        model=chat_deployment
    )
    
    return response.choices[0].message.content.strip()

async def extract_text_from_pdf_local(file_path: str) -> str:
    """Extract text from locally stored PDF file"""
    def extract_text():
        with fitz.open(file_path) as doc:
            return "\n".join(page.get_text() for page in doc)
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, extract_text)

# ============================================================================
# MAIN API ENDPOINT - Core functionality
# ============================================================================
# POST /api/v1/hackrx/run
# Purpose: Process documents and answer questions using RAG or special logic
# 
# Features:
# 1. Logs all incoming requests to MongoDB
# 2. Handles two types of requests:
#    a) Secret token extraction from HTML pages
#    b) PDF document Q&A using RAG pipeline
# 3. Caches processed documents for performance
# 4. Returns answers to all questions

@app.post("/api/v1/hackrx/run")
async def hackrx_run(request: QueryRequest, authorization: str = Header(None)):
    """
    Main endpoint for document question answering.
    
    Args:
        request: QueryRequest containing document URL, questions, and optional session_id
        authorization: Optional auth header for tracking
    
    Returns:
        {"answers": [...], "session_id": "..."}
    """
    
    # ===== SESSION MANAGEMENT =====
    # Generate session ID if not provided (for chat history tracking)
    session_id = request.session_id or generate_session_id()
    
    # ===== REQUEST LOGGING =====
    # Log incoming request details to MongoDB for analytics and debugging
    request_data = request.dict()
    log_entry = {
        "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
        "session_id": session_id,
        "auth_header": authorization,
        "request_data": request_data
    }
    collection.insert_one(log_entry)

    doc_url = request.documents
    start_time = time.time()

    # ===== SPECIAL CASE: SECRET TOKEN EXTRACTION =====
    # If URL contains "get-secret-token", scrape HTML instead of processing PDF
    if "get-secret-token" in doc_url:
        async with httpx.AsyncClient() as client:
            resp = await client.get(doc_url, timeout=10)
            soup = BeautifulSoup(resp.text, "html.parser")         # Parse HTML
            token_div = soup.find(id="token")                      # Find div with id="token"
            token_text = token_div.text.strip() if token_div else "Token not found"
        answer_text = f"Secret Token: {token_text}"

        # Log the Q&A to MongoDB
        collection.insert_one({
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
            "session_id": session_id,
            "document_url": doc_url,
            "question": request.questions[0] if request.questions else None,
            "answer": answer_text,
            "api_result": answer_text,
            "top_chunks": []                                       # No document chunks for this path
        })
        
        # Store in chat sessions collection for history
        chat_sessions.insert_one({
            "session_id": session_id,
            "timestamp": datetime.now(),
            "document_url": doc_url,
            "question": request.questions[0] if request.questions else None,
            "answer": answer_text,
            "message_type": "secret_token"
        })

        return {"answers": [answer_text], "session_id": session_id}

    # ===== PDF PROCESSING PIPELINE =====
    # Check if document is already cached to avoid reprocessing
    if doc_url in document_cache:
        chunks, faiss_index = document_cache[doc_url]
        print(f"[Cache] Using cached document: {doc_url}")
    else:
        # Step 1: Extract text from PDF
        t0 = time.time()
        text = await extract_text_from_pdf_fast(doc_url)
        print(f"[Time] PDF text extraction: {time.time() - t0:.2f}s")

        # Step 2: Split text into manageable chunks
        t1 = time.time()
        chunks = smart_chunk_text(text)
        print(f"[Time] Smart chunking: {time.time() - t1:.2f}s")

        # Step 3: Generate embeddings (vector representations) for each chunk
        t2 = time.time()
        chunk_embeddings = await get_embeddings(chunks, model=embedding_deployment)
        print(f"[Time] Embedding generation: {time.time() - t2:.2f}s")

        # Step 4: Create FAISS index for fast similarity search
        t3 = time.time()
        embedding_dim = chunk_embeddings.shape[1]
        faiss_index = faiss.IndexFlatL2(embedding_dim)            # L2 distance for similarity
        faiss_index.add(chunk_embeddings)                         # Add all embeddings to index
        print(f"[Time] FAISS index creation: {time.time() - t3:.2f}s")

        # Cache the processed document
        document_cache[doc_url] = (chunks, faiss_index)

    # ===== ANSWER QUESTIONS CONCURRENTLY =====
    # Process all questions in parallel for better performance
    tasks = [answer_question_with_rag(q, chunks, faiss_index, doc_url, session_id) for q in request.questions]
    answers = await asyncio.gather(*tasks)

    print(f"[Time] Overall API call time: {time.time() - start_time:.2f}s")
    return {"answers": answers, "session_id": session_id}

# ============================================================================
# CUSTOM API LOGIC HANDLER
# ============================================================================
# Feature: Detect questions about flights/cities and call external APIs
# Purpose: Retrieve flight numbers based on user's favorite city
# 
# Process:
# 1. Check if question mentions flight-related keywords
# 2. Call HackRx API to get user's favorite city
# 3. Map city to appropriate flight endpoint
# 4. Return combined result (city + flight number)

async def evaluate_custom_logic(question: str) -> str:
    """
    Evaluate if question requires custom API logic (flight numbers, city data).
    
    Args:
        question: The user's question
    
    Returns:
        API result string if applicable, empty string otherwise
    """
    
    # Check if question is related to flights/cities
    keywords = ["flight", "api", "city", "landmark"]
    if not any(kw in question.lower() for kw in keywords):
        return ""

    t_api = time.time()
    async with httpx.AsyncClient() as client:
        try:
            # ===== STEP 1: Get user's favorite city =====
            fav_city_resp = await client.get(
                "https://register.hackrx.in/submissions/myFavouriteCity",
                timeout=3
            )

            fav_city_resp.raise_for_status()
            city_data = fav_city_resp.json()                      # Parse JSON response

            raw_city = city_data["data"]["city"]                  # Extract city name
            print(f"[DEBUG] Raw city from API: {repr(raw_city)}")

            # ===== STEP 2: Normalize city name =====
            # Remove whitespace and convert to lowercase for consistent mapping
            city_key = re.sub(r"\s+", "", raw_city.strip().lower())
            print(f"[DEBUG] Normalized city key: {city_key}")

            # ===== STEP 3: Map city to flight endpoint =====
            # Each city has a specific endpoint for flight number retrieval
            CITY_TO_ENDPOINT = {
                "delhi": "getFirstCityFlightNumber",
                "hyderabad": "getSecondCityFlightNumber",
                "paris": "getSecondCityFlightNumber",
                "newyork": "getThirdCityFlightNumber",
                "tokyo": "getFourthCityFlightNumber",
                "istanbul": "getFourthCityFlightNumber",
            }

            # Default to fifth endpoint if city not in mapping
            endpoint = CITY_TO_ENDPOINT.get(city_key, "getFifthCityFlightNumber")
            print(f"[DEBUG] Selected endpoint: {endpoint}")

            # ===== STEP 4: Get flight number =====
            flight_resp = await client.get(
                f"https://register.hackrx.in/teams/public/flights/{endpoint}",
                timeout=3
            )

            result = f"Favorite city: {raw_city}, Flight Number: {flight_resp.text.strip()}"
            print(result)
            print(f"[Time] API call logic: {time.time() - t_api:.2f}s")
            return result
            
        except Exception as e:
            print(f"[Time] API call failed: {str(e)}")
            return ""


# ============================================================================
# SEMANTIC EXPANSION - Improve question understanding
# ============================================================================
# Feature: Expand questions with synonyms and related terms
# Purpose: Improve retrieval by searching for semantically similar concepts
# 
# Example: "IVF treatment" also searches for:
#   - "in vitro fertilization"
#   - "assisted reproduction"
#   - "ART"
#   - "infertility treatment"

def expand_question_semantics(question: str) -> list[str]:
    """
    Expand question with domain-specific synonyms for better retrieval.
    
    Args:
        question: Original user question
    
    Returns:
        List of questions including original + synonym variations
    """
    
    # Domain-specific synonym mappings (medical/insurance terms)
    synonyms = {
        "IVF": ["in vitro fertilization", "assisted reproduction", "ART", "infertility treatment"],
        "settled": ["paid", "reimbursed", "processed"],
        "hospitalization": ["hospital admission", "inpatient care"],
    }
    
    expanded = [question]  # Start with original question
    
    # For each term found in the question, add variations with synonyms
    for term, alts in synonyms.items():
        if term.lower() in question.lower():
            for alt in alts:
                expanded.append(question.replace(term, alt))
    
    return list(set(expanded))  # Remove duplicates

# ============================================================================
# RAG ANSWER PIPELINE - Complete question answering flow
# ============================================================================
# This is the core RAG (Retrieval-Augmented Generation) pipeline:
# 
# Flow:
# 1. Check for custom API logic (flight numbers, etc.)
# 2. Expand question with synonyms for better retrieval
# 3. Generate embeddings for expanded questions
# 4. Search FAISS index for relevant chunks (top 16)
# 5. Re-rank chunks by keyword overlap (top 5)
# 6. Combine API results + chunks as context
# 7. Send to GPT for final answer generation
# 8. Log Q&A pair to MongoDB

async def answer_question_with_rag(question: str, chunks: list[str], faiss_index: faiss.Index, doc_url: str, session_id: str) -> str:
    """
    Answer a question using RAG pipeline with custom API logic.
    
    Args:
        question: User's question
        chunks: List of document text chunks
        faiss_index: FAISS index containing chunk embeddings
        doc_url: Original document URL for logging
        session_id: Session ID for chat history tracking
    
    Returns:
        Final answer string from GPT
    """
    
    t0 = time.time()
    
    # ===== STEP 1: Check for custom API logic =====
    api_result = await evaluate_custom_logic(question)

    # ===== STEP 2: Semantic expansion for better retrieval =====
    expanded_questions = expand_question_semantics(question)
    
    # ===== STEP 3: Generate embeddings for all question variations =====
    question_embeddings = await get_embeddings(expanded_questions, model=embedding_deployment)
    avg_embedding = np.mean(question_embeddings, axis=0, keepdims=True)  # Average for robust search

    # ===== STEP 4: Vector similarity search - get top 16 chunks =====
    retrieved_chunks = search_faiss(avg_embedding, faiss_index, chunks, k=16)
    
    # ===== STEP 5: Re-rank by keyword overlap - keep top 5 =====
    # This hybrid approach (vector + keyword) improves precision
    top_chunks = rerank_chunks_by_keyword_overlap(question, retrieved_chunks, top_k=5)

    # ===== STEP 6: Build context from API results + document chunks =====
    context = api_result + "\n---\n" + "\n---\n".join(top_chunks) if api_result else "\n---\n".join(top_chunks)

    # ===== STEP 7: Generate answer using GPT =====
    t1 = time.time()
    answer = await ask_gpt(question, context)
    print(f"[Time] GPT answer generation: {time.time() - t1:.2f}s")

    # ===== STEP 8: Log Q&A to MongoDB for analytics =====
    collection.insert_one({
        "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
        "session_id": session_id,
        "document_url": doc_url,
        "question": question,
        "answer": answer,
        "top_chunks": top_chunks,                    # Store retrieved chunks for debugging
        "api_result": api_result                     # Store API call results
    })
    
    # Store in chat sessions collection for history
    chat_sessions.insert_one({
        "session_id": session_id,
        "timestamp": datetime.now(),
        "document_url": doc_url,
        "question": question,
        "answer": answer,
        "top_chunks": top_chunks,
        "api_result": api_result,
        "message_type": "qa_pair"
    })

    print(f"[Time] Total time for answering '{question}': {time.time() - t0:.2f}s")
    return answer

# ============================================================================
# KEYWORD-BASED RE-RANKING
# ============================================================================
# Feature: Hybrid retrieval - combine vector similarity + keyword matching
# Purpose: Improve precision by prioritizing chunks that contain question keywords
# 
# Why this helps:
# - Vector search is good for semantic similarity
# - Keyword matching ensures exact term matches are prioritized
# - Combining both gives better results than either alone

def rerank_chunks_by_keyword_overlap(question: str, chunks: list[str], top_k: int = 5) -> list[str]:
    """
    Re-rank chunks based on keyword overlap with question.
    
    Args:
        question: User's question
        chunks: Chunks retrieved from vector search
        top_k: Number of top chunks to return
    
    Returns:
        Top K chunks sorted by keyword overlap score
    """
    
    # Extract keywords from question (simple word splitting)
    q_words = set(question.lower().split())
    
    # Score each chunk by counting how many question words it contains
    ranked = sorted(chunks, key=lambda c: sum(w in c.lower() for w in q_words), reverse=True)
    
    return ranked[:top_k]

# ============================================================================
# GPT ANSWER GENERATION
# ============================================================================
# Feature: Generate precise answers using GPT-4o-mini with carefully crafted prompt
# Purpose: Convert retrieved context into concise, accurate answers
# 
# Prompt engineering strategies:
# 1. Prioritize document information over general knowledge
# 2. Interpret semantic similarities (IVF ≈ assisted reproduction)
# 3. Combine scattered information into coherent answers
# 4. Never say "information not found" - use general knowledge as fallback
# 5. Keep answers short (1-2 sentences) and keyword-rich

async def ask_gpt(question: str, context: str) -> str:
    """
    Generate answer using Azure OpenAI GPT model.
    
    Args:
        question: User's question
        context: Retrieved chunks + API results combined
    
    Returns:
        GPT-generated answer string
    """
    
    # Carefully engineered prompt for optimal answer quality
    prompt = f"""
You are a precise assistant answering based on a given document and, only if nothing relevant is found, your general knowledge.

Follow these rules strictly:

---
1. keep the answer short concise 1-2 line and **use keywords from document** as much as possible.


2. If the document contains **anything related**, even if surprising or incorrect, **treat it as true** and use it to answer.

3. If the document includes even a **weak or partial match**, use it — you are expected to interpret semantically related ideas. For example:
   - IVF ≈ assisted reproduction
   - Hospitalization ≈ inpatient treatment
   - Settled ≈ paid or reimbursed

4. If multiple pieces of information are scattered, combine them into a **coherent answer**.

5. In no possible scenario your output should mean that the answer to asked question was not in the provided data. If there is absolutely no relevant information in the document, using your general knowledge answer the question, don't say anything like \"the document does not provide any information\" with respect to question or anything semantically equal to that.

Just give the **final answer clearly and directly**, in 2 sentences maximum.


---
Context:
{context}
---
Question: {question}
Answer:
"""
    
    # Call Azure OpenAI with low temperature for consistent, factual responses
    response = await client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,            # Low temperature = more deterministic/factual
        max_tokens=300,             # Limit response length
        model=chat_deployment       # gpt-4o-mini
    )
    
    return response.choices[0].message.content.strip()

# ============================================================================
# PDF TEXT EXTRACTION
# ============================================================================
# Feature: Fast async PDF text extraction using PyMuPDF (fitz)
# Purpose: Download and extract text from PDF URLs efficiently
# 
# Process:
# 1. Download PDF via async HTTP (httpx)
# 2. Load into memory (io.BytesIO)
# 3. Extract text using PyMuPDF in executor (avoid blocking)
# 4. Return combined text from all pages

async def extract_text_from_pdf_fast(pdf_url: str) -> str:
    """
    Extract text from PDF URL asynchronously.
    
    Args:
        pdf_url: URL to PDF document
    
    Returns:
        Extracted text from all pages combined
    """
    
    # Download PDF using async HTTP client
    async with httpx.AsyncClient() as http_client:
        response = await http_client.get(pdf_url, timeout=30.0)
        response.raise_for_status()                    # Raise error if download fails
    
    pdf_file_stream = io.BytesIO(response.content)     # Load PDF into memory

    # Define sync function for PDF processing
    def extract_text():
        with fitz.open(stream=pdf_file_stream, filetype="pdf") as doc:
            # Extract text from each page and join with newlines
            return "\n".join(page.get_text() for page in doc)

    # Run CPU-intensive PDF parsing in executor to avoid blocking event loop
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, extract_text)

# ============================================================================
# SMART TEXT CHUNKING
# ============================================================================
# Feature: Paragraph-aware text chunking with size limits
# Purpose: Split document into chunks that fit in embeddings while preserving context
# 
# Strategy:
# 1. Split by paragraphs (preserve natural boundaries)
# 2. Combine small paragraphs until reaching max_len
# 3. Filter out very short chunks (< 5 words)
# 4. This maintains semantic coherence better than fixed-size splitting

def smart_chunk_text(text: str, max_len: int = 800) -> list[str]:
    """
    Split text into chunks while respecting paragraph boundaries.
    
    Args:
        text: Full document text
        max_len: Maximum characters per chunk
    
    Returns:
        List of text chunks
    """
    
    # Split by newlines to get paragraphs
    paras = [p.strip() for p in text.split('\n') if p.strip()]
    
    chunks, buffer = [], ""
    
    # Combine paragraphs until reaching max length
    for p in paras:
        if len(buffer) + len(p) < max_len:
            buffer += " " + p                          # Add paragraph to current chunk
        else:
            chunks.append(buffer.strip())              # Save current chunk
            buffer = p                                 # Start new chunk
    
    if buffer:
        chunks.append(buffer.strip())                  # Add final chunk
    
    # Filter out very short chunks (likely headers, noise)
    return [c for c in chunks if len(c.split()) > 5]

# ============================================================================
# EMBEDDING GENERATION
# ============================================================================
# Feature: Convert text to vector embeddings using Azure OpenAI
# Purpose: Transform text into numerical representations for similarity search
# 
# Model: text-embedding-3-large (3072 dimensions)
# Batch processing: Process 20 texts at a time for efficiency
# Output: NumPy array of float32 vectors

async def get_embeddings(texts: list[str], model: str, batch_size: int = 20) -> np.ndarray:
    """
    Generate embeddings for a list of texts using Azure OpenAI.
    
    Args:
        texts: List of text strings to embed
        model: Embedding model deployment name
        batch_size: Number of texts to process per API call
    
    Returns:
        NumPy array of embeddings (shape: [num_texts, embedding_dim])
    """
    
    all_embeddings = []
    
    # Process in batches to avoid rate limits and token limits
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        
        # Call Azure OpenAI embeddings API
        response = await client.embeddings.create(input=batch, model=model)
        
        # Extract embedding vectors from response
        all_embeddings.extend([item.embedding for item in response.data])
    
    # Convert to NumPy array for FAISS compatibility
    return np.array(all_embeddings, dtype=np.float32)

# ============================================================================
# FAISS VECTOR SEARCH
# ============================================================================
# Feature: Fast similarity search using FAISS (Facebook AI Similarity Search)
# Purpose: Find most relevant chunks based on vector similarity
# 
# How it works:
# 1. Compare query embedding with all chunk embeddings
# 2. Use L2 distance (Euclidean distance) as similarity metric
# 3. Return top K most similar chunks
# 4. FAISS makes this extremely fast even with thousands of chunks

def search_faiss(query_embedding: np.ndarray, index: faiss.Index, chunks: list[str], k: int = 16):
    """
    Search FAISS index for most similar chunks to query.
    
    Args:
        query_embedding: Query vector (shape: [1, embedding_dim])
        index: FAISS index containing chunk embeddings
        chunks: Original text chunks (parallel to index)
        k: Number of top results to return
    
    Returns:
        List of top K most similar chunks
    """
    
    # Search: returns distances and indices of nearest neighbors
    distances, indices = index.search(query_embedding, k)
    
    # Map indices back to original text chunks
    # Filter out invalid indices (can happen if k > number of chunks)
    return [chunks[i] for i in indices[0] if i < len(chunks)]

# ============================================================================
# CHAT HISTORY ENDPOINT
# ============================================================================
# Feature: Retrieve previous conversations by session ID
# Purpose: Allow users to access and continue past conversations
# 
# This enables:
# - Reviewing past Q&A pairs
# - Continuing previous study sessions
# - Tracking learning progress

@app.post("/api/v1/hackrx/history")
async def get_chat_history(request: HistoryRequest):
    """
    Retrieve chat history for a specific session.
    
    Args:
        request: HistoryRequest containing session_id
    
    Returns:
        {
            "session_id": "...",
            "history": [
                {"question": "...", "answer": "...", "timestamp": "..."},
                ...
            ],
            "total_messages": 10
        }
    """
    
    # Query MongoDB for all messages in this session
    history = list(chat_sessions.find(
        {"session_id": request.session_id},
        {"_id": 0}  # Exclude MongoDB internal ID
    ).sort("timestamp", 1))  # Sort chronologically
    
    if not history:
        return {
            "session_id": request.session_id,
            "history": [],
            "total_messages": 0,
            "message": "No history found for this session"
        }
    
    # Format history for frontend
    formatted_history = []
    for item in history:
        formatted_history.append({
            "question": item.get("question", ""),
            "answer": item.get("answer", ""),
            "timestamp": item.get("timestamp").isoformat() if isinstance(item.get("timestamp"), datetime) else item.get("timestamp"),
            "document_url": item.get("document_url", ""),
            "message_type": item.get("message_type", "qa_pair")
        })
    
    return {
        "session_id": request.session_id,
        "history": formatted_history,
        "total_messages": len(formatted_history)
    }

# ============================================================================
# LIST ALL SESSIONS ENDPOINT
# ============================================================================
# Feature: Get all available chat sessions
# Purpose: Show users their previous study sessions

@app.get("/api/v1/hackrx/sessions")
async def list_sessions():
    """
    List all unique session IDs with metadata.
    
    Returns:
        {
            "sessions": [
                {
                    "session_id": "...",
                    "first_message": "...",
                    "last_message": "...",
                    "message_count": 5,
                    "document_url": "..."
                },
                ...
            ]
        }
    """
    
    # Get all unique session IDs
    pipeline = [
        {
            "$group": {
                "_id": "$session_id",
                "first_timestamp": {"$min": "$timestamp"},
                "last_timestamp": {"$max": "$timestamp"},
                "message_count": {"$sum": 1},
                "first_question": {"$first": "$question"},
                "document_url": {"$first": "$document_url"}
            }
        },
        {
            "$sort": {"last_timestamp": -1}  # Most recent first
        }
    ]
    
    sessions = list(chat_sessions.aggregate(pipeline))
    
    formatted_sessions = []
    for session in sessions:
        formatted_sessions.append({
            "session_id": session["_id"],
            "first_message": session.get("first_question", "")[:100],  # Truncate for preview
            "first_timestamp": session["first_timestamp"].isoformat() if isinstance(session.get("first_timestamp"), datetime) else str(session.get("first_timestamp")),
            "last_timestamp": session["last_timestamp"].isoformat() if isinstance(session.get("last_timestamp"), datetime) else str(session.get("last_timestamp")),
            "message_count": session["message_count"],
            "document_url": session.get("document_url", "")
        })
    
    return {
        "sessions": formatted_sessions,
        "total_sessions": len(formatted_sessions)
    }

# ============================================================================
# SUMMARIZE CHAT HISTORY ENDPOINT
# ============================================================================
# Feature: Summarize entire chat session using IBM Granite or Azure OpenAI
# Purpose: Quick revision - get gist without reading full conversation
# 
# Use case: Students can review key points from study sessions quickly

@app.post("/api/v1/hackrx/summarize")
async def summarize_session(request: SummarizeRequest):
    """
    Summarize a chat session for quick revision.
    
    Args:
        request: SummarizeRequest with session_id and optional use_granite flag
    
    Returns:
        {
            "session_id": "...",
            "summary": "...",
            "key_points": [...],
            "model_used": "granite" or "gpt-4o-mini"
        }
    """
    
    print(f"[SUMMARIZE] Request to summarize session: {request.session_id}")
    
    # Retrieve chat history from the correct collection (messages_collection)
    history = list(messages_collection.find(
        {"session_id": request.session_id}
    ).sort("created_at", 1))
    
    print(f"[SUMMARIZE] Found {len(history)} messages in session")
    
    if not history:
        # Try to find session info
        session_info = sessions_collection.find_one({"_id": ObjectId(request.session_id)})
        if session_info:
            print(f"[SUMMARIZE] Session exists but has no messages yet")
        else:
            print(f"[SUMMARIZE] Session not found in database")
        
        return {
            "session_id": request.session_id,
            "summary": "No conversation found for this session.",
            "key_points": [],
            "model_used": "none"
        }
    
    # Format conversation for summarization
    conversation_text = "Conversation History:\n\n"
    for i, item in enumerate(history, 1):
        msg_type = item.get('type', 'unknown')
        content = item.get('content', 'N/A')
        if msg_type == 'user':
            conversation_text += f"User: {content}\n"
        elif msg_type == 'bot':
            conversation_text += f"Assistant: {content}\n\n"
    
    # Choose model based on request and availability
    use_granite = request.use_granite and USE_GRANITE
    
    try:
        if use_granite:
            # Use IBM Granite model for summarization (with 30s timeout)
            print(f"[SUMMARIZE] Using IBM Granite model...")
            summary, key_points = await asyncio.wait_for(
                summarize_with_granite(conversation_text),
                timeout=30.0  # 30 second timeout
            )
            model_used = "ibm-granite"
        else:
            # Use Azure OpenAI GPT
            print(f"[SUMMARIZE] Using Azure OpenAI GPT...")
            summary, key_points = await summarize_with_gpt(conversation_text)
            model_used = "gpt-4o-mini"
    except asyncio.TimeoutError:
        print(f"[SUMMARIZE] Granite timed out, falling back to GPT...")
        summary, key_points = await summarize_with_gpt(conversation_text)
        model_used = "gpt-4o-mini (granite timeout)"
    except Exception as e:
        print(f"[SUMMARIZE] Error with Granite: {str(e)}, falling back to GPT...")
        summary, key_points = await summarize_with_gpt(conversation_text)
        model_used = f"gpt-4o-mini (granite error)"
    
    return {
        "session_id": request.session_id,
        "summary": summary,
        "key_points": key_points,
        "total_messages": len(history),
        "model_used": model_used
    }

# ============================================================================
# SUMMARIZATION HELPER FUNCTIONS
# ============================================================================

async def summarize_with_gpt(conversation_text: str) -> tuple[str, list[str]]:
    """
    Summarize conversation using Azure OpenAI GPT.
    
    Args:
        conversation_text: Full conversation history as text
    
    Returns:
        (summary_text, key_points_list)
    """
    
    prompt = f"""You are an expert study assistant helping students review their learning sessions.

Please analyze the following conversation and provide:
1. A concise summary (2-3 paragraphs) covering the main topics discussed
2. A bulleted list of key points and important information

Format your response as:
SUMMARY:
[Your summary here]

KEY POINTS:
- [Point 1]
- [Point 2]
- [Point 3]
...

---
{conversation_text}
---
"""
    
    response = await client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=800,
        model=chat_deployment
    )
    
    result = response.choices[0].message.content.strip()
    
    # Parse summary and key points
    parts = result.split("KEY POINTS:")
    summary = parts[0].replace("SUMMARY:", "").strip()
    
    key_points = []
    if len(parts) > 1:
        points_text = parts[1].strip()
        key_points = [line.strip("- ").strip() for line in points_text.split("\n") if line.strip().startswith("-")]
    
    return summary, key_points

async def summarize_with_granite(conversation_text: str) -> tuple[str, list[str]]:
    """
    Summarize conversation using local IBM Granite 3.1-3B model.
    
    Args:
        conversation_text: Full conversation history as text
    
    Returns:
        (summary_text, key_points_list)
    """
    
    try:
        # Local IBM Granite 3.1-3B (800M instruct) model
        # Install: pip install transformers torch accelerate
        
        from transformers import AutoTokenizer, AutoModelForCausalLM
        import torch
        
        print(f"[Info] Loading Granite model: {GRANITE_MODEL_PATH}")
        
        # Load model and tokenizer
        tokenizer = AutoTokenizer.from_pretrained(GRANITE_MODEL_PATH)
        model = AutoModelForCausalLM.from_pretrained(
            GRANITE_MODEL_PATH,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            device_map="auto"  # Automatically use GPU if available
        )
        
        # Use proper chat template format for instruct model
        messages = [
            {
                "role": "user",
                "content": f"""You are an expert study assistant. Summarize this conversation for a student's quick revision.

Provide:
1. A concise summary (2-3 paragraphs)
2. Key points as a bulleted list

Format your response as:
SUMMARY:
[Your summary here]

KEY POINTS:
- [Point 1]
- [Point 2]
- [Point 3]

{conversation_text}"""
            }
        ]
        
        # Apply chat template (proper format for Granite instruct model)
        inputs = tokenizer.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
        ).to(model.device)
        
        # Run inference in executor to avoid blocking
        loop = asyncio.get_running_loop()
        
        def generate():
            with torch.no_grad():
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=800,
                    temperature=0.3,
                    do_sample=True,
                    top_p=0.95
                )
            # Decode only the generated part (skip input prompt)
            return tokenizer.decode(outputs[0][inputs["input_ids"].shape[-1]:], skip_special_tokens=True)
        
        result = await loop.run_in_executor(None, generate)
        
        print(f"[Debug] Granite output: {result[:200]}...")  # Log first 200 chars
        
        # Parse result
        parts = result.split("KEY POINTS:")
        summary = parts[0].replace("SUMMARY:", "").strip()
        
        key_points = []
        if len(parts) > 1:
            points_text = parts[1].strip()
            key_points = [line.strip("- ").strip() for line in points_text.split("\n") if line.strip().startswith("-")]
        
        return summary, key_points
        
    except Exception as e:
        print(f"[Error] Granite summarization failed: {str(e)}")
        print("[Info] Falling back to GPT summarization")
        # Fallback to GPT if Granite fails
        return await summarize_with_gpt(conversation_text)
