# 📄 DocuMind AI - Intelligent Document Q&A System

> **Multi-Agent RAG System with User Authentication & Chat History**

[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green.svg)](https://fastapi.tiangolo.com/)
[![Azure OpenAI](https://img.shields.io/badge/Azure-OpenAI-orange.svg)](https://azure.microsoft.com/en-us/products/cognitive-services/openai-service)

A powerful **Retrieval-Augmented Generation (RAG)** system that allows users to upload PDFs and have intelligent conversations with their documents using AI. The system features secure authentication, persistent chat history, and a sophisticated multi-agent architecture.

---

## ✨ Key Features

- 🤖 **Multi-Agent RAG System** - Intelligent 4-agent architecture for accurate responses
- 🔐 **Secure Authentication** - JWT-based login with bcrypt password hashing
- 💬 **Persistent Chat History** - MongoDB-backed session management
- 📊 **AI Summarization** - Generate conversation summaries with one click
- 🎨 **Modern UI** - Responsive design with dark/light mode toggle
- 📤 **Smart Upload** - Drag-and-drop PDF upload with no size limits
- 🔍 **Adaptive Retrieval** - Automatically adjusts context based on query complexity
- 📱 **Fully Responsive** - Works seamlessly on desktop and mobile

---

## 🧠 How It Works

### **System Architecture**

```
┌─────────────┐      ┌──────────────┐      ┌─────────────────┐
│   Frontend  │─────▶│FastAPI Server│─────▶│ Azure OpenAI    │
│ (HTML/JS)   │◀─────│  (Python)    │◀─────│ (GPT-4o-mini)   │
└─────────────┘      └──────┬───────┘      └─────────────────┘
                            │
                ┌───────────┼───────────┐
                │           │           │
            ┌───▼───┐  ┌────▼────┐  ┌──▼──────┐
            │MongoDB│  │  FAISS  │  │PyMuPDF  │
            │(Store)│  │(Search) │  │(Parse)  │
            └───────┘  └─────────┘  └─────────┘
```

### **4-Agent RAG Pipeline**

When you ask a question, the system uses **4 specialized AI agents** working together:

#### 1. 🎯 **Question Understanding Agent**

- Analyzes your question to understand intent
- Clarifies ambiguous queries
- Identifies what information is needed
- **Example**: "What's the capital?" → Understands context from previous messages

#### 2. 📜 **History Analysis Agent**

- Reviews previous messages in the conversation
- Maintains context across multiple questions
- Resolves references like "it", "that", "the previous one"
- **Example**: You ask "Tell me more about it" → Agent knows what "it" refers to

#### 3. 🔍 **Document Retrieval Agent**

- Searches document using FAISS vector similarity
- Retrieves 21-40 most relevant text chunks
- Adapts retrieval depth based on query complexity
- **Example**: "Explain in detail" → Retrieves 40 chunks instead of 21

#### 4. ✍️ **Answer Generation Agent**

- Generates response using **ONLY** document content
- Refuses to answer if information is unavailable
- Provides citations and acknowledges limitations
- **Example**: If data isn't in the document, it says "This information is not available in the document"

---

## 📖 User Journey (Step-by-Step)

### **Step 1: Register/Login** 🔐

```
1. Visit http://127.0.0.1:8000/login
2. Create account or login with credentials
3. System generates secure JWT token
4. You're authenticated and redirected to upload page
```

### **Step 2: Upload PDF** 📤

```
1. Drag & drop PDF or click to select
2. PyMuPDF extracts all text from PDF
3. Text is split into manageable chunks (~500 words each)
4. Each chunk is converted to vector embeddings using Azure OpenAI
5. Vectors stored in FAISS for fast similarity search
6. PDF ready for querying! ✅
```

### **Step 3: Create Chat Session** 💬

```
1. System creates a new chat session
2. Session metadata saved to MongoDB
3. Chat interface opens
4. You can now start asking questions
```

### **Step 4: Ask Questions** ❓

```
1. Type your question (e.g., "What is the main conclusion?")
2. Question → 4-Agent RAG Pipeline:
   - Agent 1: Understands question intent
   - Agent 2: Reviews chat history for context
   - Agent 3: Retrieves relevant document chunks
   - Agent 4: Generates answer from retrieved content
3. Answer displayed in chat
4. Question + Answer saved to MongoDB
5. Ask follow-up questions with full context!
```

### **Step 5: Summarize (Optional)** 📊

```
1. Click "Summarize" button
2. System analyzes entire conversation
3. AI generates comprehensive summary
4. Summary displayed in modal popup
```

---

## 🎯 Key Technical Concepts Explained

### **What is RAG (Retrieval-Augmented Generation)?**

Traditional AI models can **hallucinate** (make up information). RAG solves this by:

1. **Retrieving** relevant information from your document
2. **Augmenting** the AI's context with this information
3. **Generating** answers based ONLY on retrieved content

**Example:**

- ❌ **Without RAG**: "The Eiffel Tower is 500 meters tall" (hallucinated/incorrect)
- ✅ **With RAG**: "According to your document, the height is not mentioned" (accurate)

### **Vector Embeddings & FAISS Search**

**How it works:**

1. Your document is converted into **numerical vectors** (embeddings)
   - Each chunk becomes something like `[0.234, -0.123, 0.891, ...]` (1536 dimensions)
2. When you ask a question, it's also converted to a vector
3. FAISS finds the **most similar** document chunks using cosine similarity
4. Similar vectors = similar meanings!

**Why this is powerful:**

- ✅ Understands **meaning**, not just keywords
- ✅ Finds "diabetes treatment" even if you search "managing blood sugar"
- ✅ 1000x faster than scanning entire document
- ✅ Works in any language

### **Adaptive Retrieval System**

The system intelligently adjusts how much context to retrieve based on your question:

| Query Type   | Chunks Retrieved | Example                             |
| ------------ | ---------------- | ----------------------------------- |
| **Standard** | 21 chunks        | "What is X?"                        |
| **Detailed** | 40 chunks        | "Explain X in comprehensive detail" |

**Keywords that trigger detailed retrieval:**
`detail`, `detailed`, `depth`, `in-depth`, `comprehensive`, `thorough`, `complete`, `full`, `extensive`, `elaborate`

---

## 🛠 Tech Stack

| Component          | Technology               | Purpose                  |
| ------------------ | ------------------------ | ------------------------ |
| **Backend**        | FastAPI 0.115            | RESTful API server       |
| **AI Model**       | Azure OpenAI GPT-4o-mini | Answer generation        |
| **Embeddings**     | text-embedding-3-large   | Vector embeddings        |
| **Vector Search**  | FAISS                    | Fast similarity search   |
| **Database**       | MongoDB Atlas            | User data & chat history |
| **PDF Parser**     | PyMuPDF 1.26             | Extract text from PDFs   |
| **Authentication** | JWT + bcrypt             | Secure auth              |
| **Frontend**       | HTML5 + Tailwind CSS     | Responsive UI            |

---

## 🚀 Quick Start

### **Prerequisites**

- Python 3.12+
- MongoDB Atlas account (free tier works!)
- Azure OpenAI API access

### **Installation**

```bash
# 1. Clone repository
git clone https://github.com/Shivang-Karol/OPTIMAL-INTELLECTS-DocuMind.AI-.git
cd OPTIMAL-INTELLECTS-DocuMind.AI-

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your credentials (see Configuration section)

# 5. Run server
uvicorn logmain:app --reload --host 127.0.0.1 --port 8000
```

### **Access Application**

- 🌐 **Main App**: http://127.0.0.1:8000
- 🔐 **Login/Register**: http://127.0.0.1:8000/login
- 📚 **API Docs**: http://127.0.0.1:8000/docs

---

## ⚙️ Configuration

### **1. MongoDB Atlas Setup**

1. Create account at [MongoDB Atlas](https://cloud.mongodb.com)
2. Create a **FREE M0 cluster**
3. Create database user (username + password)
4. Whitelist IP: `0.0.0.0/0` (for development)
5. Get connection string
6. Update `.env`:
   ```env
   MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net
   ```

### **2. Azure OpenAI Setup**

1. Create Azure OpenAI resource in Azure Portal
2. Deploy these models:
   - **gpt-4o-mini** (for chat)
   - **text-embedding-3-large** (for embeddings)
3. Get API key and endpoint
4. Update `.env`:
   ```env
   OPENAI_API_KEY=your_azure_api_key
   OPENAI_API_BASE=https://your-resource.openai.azure.com/
   OPENAI_API_VERSION=2024-12-01-preview
   OPENAI_DEPLOYMENT=gpt-4o-mini
   OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-large
   ```

### **3. JWT Secret**

Generate a strong random string:

```env
JWT_SECRET=your-super-secret-jwt-key-change-this-to-random-string
```

---

## 📡 API Endpoints

| Method | Endpoint                   | Description                   |
| ------ | -------------------------- | ----------------------------- |
| POST   | `/api/v1/auth/register`    | Register new user             |
| POST   | `/api/v1/auth/login`       | Login and get JWT token       |
| POST   | `/api/v1/upload-pdf`       | Upload PDF document           |
| POST   | `/api/v1/sessions/create`  | Create new chat session       |
| GET    | `/api/v1/sessions/list`    | Get all user sessions         |
| POST   | `/api/v1/chat`             | Send message and get response |
| POST   | `/api/v1/hackrx/summarize` | Summarize conversation        |

**Full interactive API documentation:** http://127.0.0.1:8000/docs

---

## 📂 Project Structure

```
📦 OPTIMAL-INTELLECTS-DocuMind.AI-
├── 📄 logmain.py              # Main FastAPI application
├── 📄 requirements.txt        # Python dependencies
├── 📄 .env.example            # Environment variables template
├── 📄 .gitignore              # Git ignore rules
├── 📄 README.md               # This file
├── 📄 LICENSE                 # MIT License
├── 📄 CHANGELOG.md            # Version history
├── 📁 static/                 # Frontend files
│   ├── Index.html             # Main chat interface
│   ├── LoginRegister.html     # Auth page
│   └── pdf upload.html        # Upload page
├── 📁 temp_uploads/           # Temporary PDF storage
└── 📁 .github/                # GitHub templates
    ├── PULL_REQUEST_TEMPLATE.md
    └── ISSUE_TEMPLATE/
        ├── bug_report.md
        └── feature_request.md
```

---

## 🔒 Security Features

- ✅ **Password Hashing**: bcrypt with salt rounds
- ✅ **JWT Authentication**: Secure token-based auth
- ✅ **CORS Protection**: Configured allowed origins
- ✅ **Environment Variables**: All secrets in `.env`
- ✅ **User Session Isolation**: Each user only sees their own data
- ✅ **Input Validation**: FastAPI Pydantic models

---

## 🎨 Special Features

### **Document-Only Responses**

The AI is configured to:

- ✅ Only use content from uploaded document
- ✅ Never add external knowledge or hallucinate
- ✅ Explicitly refuse when information is unavailable
- ✅ Acknowledge limitations in the document

**Example:**

```
User: "What is the population of France?"
AI: "This information is not available in the uploaded document."
```

### **Context-Aware Conversations**

```
User: "What is photosynthesis?"
AI: [Explains from document]

User: "Where does it occur?"
AI: [Understands "it" = photosynthesis, continues with context]
```

### **Dark/Light Mode**

- Toggle between themes
- Preference saved in browser
- Eye-friendly for long reading sessions

---

## 🐛 Troubleshooting

### **MongoDB Connection Failed**

```
ERROR: ServerSelectionTimeoutError
```

**Solution:**

- Check internet connection
- Verify `MONGO_URI` in `.env` is correct
- Ensure IP is whitelisted in MongoDB Atlas
- Confirm cluster is running (not paused)

### **Azure OpenAI Errors**

```
ERROR: 401 Unauthorized
```

**Solution:**

- Verify `OPENAI_API_KEY` is correct
- Check `OPENAI_API_BASE` endpoint is valid
- Ensure deployment names match exactly
- Check Azure OpenAI quota/limits

### **PDF Upload Issues**

```
ERROR: Failed to process PDF
```

**Solution:**

- Ensure PDF is not corrupted
- Check `temp_uploads/` folder exists
- Verify server has write permissions
- Try a different PDF file

### **Authentication Not Working**

```
ERROR: 503 Service Unavailable
```

**Solution:**

- MongoDB might be down
- Check database connection
- Server will return 503 if DB unavailable

---

## 📊 Performance Metrics

| Operation      | Typical Time  |
| -------------- | ------------- |
| PDF Processing | 10-30 seconds |
| Query Response | 2-5 seconds   |
| Summarization  | 3-8 seconds   |
| FAISS Search   | <0.1 seconds  |
| Login/Register | <1 second     |

---

## 💡 Usage Tips

1. **For Better Results:**

   - Upload clear, well-formatted PDFs
   - Ask specific questions
   - Use "explain in detail" for comprehensive answers

2. **For Faster Responses:**

   - Keep questions focused
   - Avoid overly broad queries
   - Use session history for context

3. **For Summarization:**
   - Have at least 3-4 exchanges before summarizing
   - Summarize helps when reviewing long conversations

---

## 🤝 Contributing

Contributions are welcome! To contribute:

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 👥 Team

**OPTIMAL INTELLECTS**

Hackathon Project - 2025

---

## 🙏 Acknowledgments

- **Azure OpenAI** for powerful AI capabilities
- **MongoDB Atlas** for reliable cloud database
- **FastAPI** for the amazing web framework
- **FAISS** for lightning-fast vector search
- **PyMuPDF** for robust PDF parsing

---

## 📞 Support

Having issues? Found a bug? Have suggestions?

- Open an issue on GitHub
- Check the [API Documentation](http://127.0.0.1:8000/docs)
- Review the Troubleshooting section above

---

**Made with ❤️ for intelligent document analysis**

_Empowering users to have meaningful conversations with their documents_
