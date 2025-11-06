# 📄 DocuMind AI - Intelligent Document Q&A System# 📄 DocuMind AI - Intelligent Document Q&A System

> **Multi-Agent RAG System with User Authentication & Chat History**> **Multi-Agent RAG System with User Authentication & Chat History**

[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/downloads/)[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/downloads/)

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green.svg)](https://fastapi.tiangolo.com/)[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green.svg)](https://fastapi.tiangolo.com/)

[![Azure OpenAI](https://img.shields.io/badge/Azure-OpenAI-orange.svg)](https://azure.microsoft.com/en-us/products/cognitive-services/openai-service)[![Azure OpenAI](https://img.shields.io/badge/Azure-OpenAI-orange.svg)](https://azure.microsoft.com/en-us/products/cognitive-services/openai-service)

A powerful **Retrieval-Augmented Generation (RAG)** system that allows users to upload PDFs and have intelligent conversations with their documents using AI. The system features secure authentication, persistent chat history, and a sophisticated multi-agent architecture.A powerful **Retrieval-Augmented Generation (RAG)** system that allows users to upload PDFs and have intelligent conversations with their documents using AI. The system features secure authentication, persistent chat history, and a sophisticated multi-agent architecture.

---## ✨ Key Features---

## ✨ Key Features- 🤖 **4-Agent RAG System** - Question understanding, history analysis, retrieval, and answer generation## ✨ Features

- 🤖 **Multi-Agent RAG System** - Intelligent 4-agent architecture for accurate responses- 🔐 **User Authentication** - Secure JWT-based login/registration with bcrypt- **Smart PDF Text Extraction** (via `PyMuPDF`)

- 🔐 **Secure Authentication** - JWT-based login with bcrypt password hashing

- 💬 **Persistent Chat History** - MongoDB-backed session management- 💬 **Chat History** - Persistent sessions stored in MongoDB- **Intelligent Text Chunking** for better retrieval

- 📊 **AI Summarization** - Generate conversation summaries with one click

- 🎨 **Modern UI** - Responsive design with dark/light mode toggle- 📊 **Session Summarization** - AI-powered conversation summaries- **Embeddings Generation** with Azure OpenAI (`text-embedding-3-large`)

- 📤 **Smart Upload** - Drag-and-drop PDF upload with no size limits

- 🔍 **Adaptive Retrieval** - Automatically adjusts context based on query complexity- 🎨 **Modern UI** - Dark/light mode with Tailwind CSS- **FAISS Vector Search** for high-speed retrieval

- 📱 **Fully Responsive** - Works seamlessly on desktop and mobile

- 📤 **Smart Upload** - Drag-and-drop PDF upload with no size limits- **Custom Logic** for:

---

- 🔍 **Semantic Search** - FAISS vector search with adaptive retrieval - Retrieving flight numbers based on a user's favorite city

## 🧠 How It Works

- 📱 **Responsive Design** - Works on desktop and mobile - Extracting secret tokens from HTML pages

### **System Architecture**

- **Semantic Understanding**: interprets related terms like _IVF ≈ assisted reproduction_

``````

┌─────────────┐      ┌──────────────┐      ┌─────────────────┐---- **Detailed MongoDB Logging** of:

│   Frontend  │─────▶│FastAPI Server│─────▶│ Azure OpenAI    │

│ (HTML/JS)   │◀─────│  (Python)    │◀─────│ (GPT-4o-mini)   │- Incoming request

└─────────────┘      └──────┬───────┘      └─────────────────┘

                            │## 🏗️ Architecture - Extracted context chunks

                ┌───────────┼───────────┐

                │           │           │- Final answers & API results

            ┌───▼───┐  ┌────▼────┐  ┌──▼──────┐

            │MongoDB│  │  FAISS  │  │PyMuPDF  │`````- **Optimized GPT Prompting** for short, keyword-rich answers

            │(Store)│  │(Search) │  │(Parse)  │

            └───────┘  └─────────┘  └─────────┘Frontend (HTML/JS/Tailwind) → FastAPI Backend → Multi-Agent RAG → Azure OpenAI + MongoDB

``````

````---

### **4-Agent RAG Pipeline**



When you ask a question, the system uses **4 specialized AI agents** working together:

**4 AI Agents:**## 🛠 Tech Stack

#### 1. 🎯 **Question Understanding Agent**

- Analyzes your question to understand intent1. **Question Understanding** - Clarifies intent- **Backend Framework:** [FastAPI](https://fastapi.tiangolo.com/)

- Clarifies ambiguous queries

- Identifies what information is needed2. **History Analysis** - Maintains context- **LLM Provider:** [Azure OpenAI](https://learn.microsoft.com/en-us/azure/cognitive-services/openai/)

- **Example**: "What's the capital?" → Understands context from previous messages

3. **Document Retrieval** - FAISS semantic search (21-40 chunks)- **Vector Store:** [FAISS](https://faiss.ai/)

#### 2. 📜 **History Analysis Agent**

- Reviews previous messages in the conversation4. **Answer Generation** - Document-grounded responses- **Database:** [MongoDB Atlas](https://www.mongodb.com/atlas/database)

- Maintains context across multiple questions

- Resolves references like "it", "that", "the previous one"- **PDF Parsing:** [PyMuPDF](https://pymupdf.readthedocs.io/)

- **Example**: You ask "Tell me more about it" → Agent knows what "it" refers to

---- **HTML Parsing:** [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/)

#### 3. 🔍 **Document Retrieval Agent**

- Searches document using FAISS vector similarity

- Retrieves 21-40 most relevant text chunks

- Adapts retrieval depth based on query complexity## 🚀 Quick Start---

- **Example**: "Explain in detail" → Retrieves 40 chunks instead of 21



#### 4. ✍️ **Answer Generation Agent**

- Generates response using **ONLY** document content### Prerequisites## 📂 Project Structure

- Refuses to answer if information is unavailable

- Provides citations and acknowledges limitations- Python 3.12+

- **Example**: If data isn't in the document, it says "This information is not available in the document"

- MongoDB Atlas account (free tier)```yaml

---

- Azure OpenAI API access📦 hackrx-rag-system

## 📖 User Journey (Step-by-Step)

├── log.py               # Main FastAPI server

### **Step 1: Register/Login** 🔐

```### Installation├── .env                 # Environment variables

1. Visit http://127.0.0.1:8000/login

2. Create account or login with credentials├── requirements.txt     # Python dependencies

3. System generates secure JWT token

4. You're authenticated and redirected to upload page```bash└── README.md            # Project documentation

````

# Clone repo````

### **Step 2: Upload PDF** 📤

```git clone https://github.com/Shivang-Karol/OPTIMAL-INTELLECTS-DocuMind.AI-.git

1. Drag & drop PDF or click to select

2. PyMuPDF extracts all text from PDFcd OPTIMAL-INTELLECTS-DocuMind.AI----

3. Text is split into manageable chunks (~500 words each)

4. Each chunk is converted to vector embeddings using Azure OpenAI

5. Vectors stored in FAISS for fast similarity search

6. PDF ready for querying! ✅# Create virtual environment## ⚙️ Installation

```

python -m venv venv

### **Step 3: Create Chat Session** 💬

````venv\Scripts\activate # Windows### 1️⃣ Clone the Repository

1. System creates a new chat session

2. Session metadata saved to MongoDB# source venv/bin/activate  # Linux/Mac```bash

3. Chat interface opens

4. You can now start asking questionsgit clone https://github.com/nahargourav/RAG-ANSWERING-SYSTEM.git

````

# Install dependencies````

### **Step 4: Ask Questions** ❓

````pip install -r requirements.txt

1. Type your question (e.g., "What is the main conclusion?")

2. Question → 4-Agent RAG Pipeline:### 2️⃣ Create a Virtual Environment

   - Agent 1: Understands question intent

   - Agent 2: Reviews chat history for context# Configure environment

   - Agent 3: Retrieves relevant document chunks

   - Agent 4: Generates answer from retrieved contentcp .env.example .env```bash

3. Answer displayed in chat

4. Question + Answer saved to MongoDB# Edit .env with your credentialspython -m venv venv

5. Ask follow-up questions with full context!

```source venv/bin/activate   # On Windows: venv\Scripts\activate



### **Step 5: Summarize (Optional)** 📊# Run server```

````

1. Click "Summarize" buttonSTART_SERVER.bat # Windows

2. System analyzes entire conversation

3. AI generates comprehensive summary# uvicorn logmain:app --reload --host 127.0.0.1 --port 8000 # Manual### 3️⃣ Install Dependencies

4. Summary displayed in modal popup

`````



---```bash



## 🎯 Key Technical Concepts Explained### Accesspip install -r requirements.txt



### **What is RAG (Retrieval-Augmented Generation)?**```



Traditional AI models can **hallucinate** (make up information). RAG solves this by:- **App**: http://127.0.0.1:8000

1. **Retrieving** relevant information from your document

2. **Augmenting** the AI's context with this information- **Login**: http://127.0.0.1:8000/login### 4️⃣ Create `.env` File

3. **Generating** answers based ONLY on retrieved content

- **API Docs**: http://127.0.0.1:8000/docs

**Example:**

- ❌ **Without RAG**: "The Eiffel Tower is 500 meters tall" (hallucinated/incorrect)````env

- ✅ **With RAG**: "According to your document, the height is not mentioned" (accurate)

---OPENAI_API_BASE=https://your-azure-openai-endpoint

### **Vector Embeddings & FAISS Search**

OPENAI_API_KEY=your-azure-api-key

**How it works:**

1. Your document is converted into **numerical vectors** (embeddings)## ⚙️ ConfigurationOPENAI_API_VERSION=2024-02-15-preview

   - Each chunk becomes something like `[0.234, -0.123, 0.891, ...]` (1536 dimensions)

2. When you ask a question, it's also converted to a vectorOPENAI_DEPLOYMENT=gpt-4o-mini

3. FAISS finds the **most similar** document chunks using cosine similarity

4. Similar vectors = similar meanings!### 1. MongoDB Atlas SetupOPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-large



**Why this is powerful:**MONGO_URI=mongodb+srv://<user>:<pass>@<cluster>.mongodb.net

- ✅ Understands **meaning**, not just keywords

- ✅ Finds "diabetes treatment" even if you search "managing blood sugar"1. Create account at [MongoDB Atlas](https://cloud.mongodb.com)```

- ✅ 1000x faster than scanning entire document

- ✅ Works in any language2. Create FREE M0 cluster



### **Adaptive Retrieval System**3. Create database user (username + password)---



The system intelligently adjusts how much context to retrieve based on your question:4. Whitelist IP: `0.0.0.0/0` (for dev)



| Query Type | Chunks Retrieved | Example |5. Get connection string## ▶️ Running the Server

|------------|------------------|---------|

| **Standard** | 21 chunks | "What is X?" |6. Update `MONGO_URI` in `.env`

| **Detailed** | 40 chunks | "Explain X in comprehensive detail" |

```bash

**Keywords that trigger detailed retrieval:**

`detail`, `detailed`, `depth`, `in-depth`, `comprehensive`, `thorough`, `complete`, `full`, `extensive`, `elaborate`### 2. Azure OpenAI Setupuvicorn log:app --reload --host 0.0.0.0 --port 8000



---````



## 🛠 Tech Stack1. Create Azure OpenAI resource



| Component | Technology | Purpose |2. Deploy models:Your API will be available at:

|-----------|-----------|---------|

| **Backend** | FastAPI 0.115 | RESTful API server |   - `gpt-4o-mini` (chat)**`http://localhost:8000`**

| **AI Model** | Azure OpenAI GPT-4o-mini | Answer generation |

| **Embeddings** | text-embedding-3-large | Vector embeddings |   - `text-embedding-3-large` (embeddings)

| **Vector Search** | FAISS | Fast similarity search |

| **Database** | MongoDB Atlas | User data & chat history |3. Get API key and endpoint---

| **PDF Parser** | PyMuPDF 1.26 | Extract text from PDFs |

| **Authentication** | JWT + bcrypt | Secure auth |4. Update `.env`:

| **Frontend** | HTML5 + Tailwind CSS | Responsive UI |

   ```env## 📡 API Endpoints

---

   OPENAI_API_KEY=your_key

## 🚀 Quick Start

   OPENAI_API_BASE=https://your-resource.openai.azure.com/### **POST** `/api/v1/hackrx/run`

### **Prerequisites**

- Python 3.12+   OPENAI_DEPLOYMENT=gpt-4o-mini

- MongoDB Atlas account (free tier works!)

- Azure OpenAI API access   OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-large#### Request Body:



### **Installation**   ```



```bash````json

# 1. Clone repository

git clone https://github.com/Shivang-Karol/OPTIMAL-INTELLECTS-DocuMind.AI-.git### 3. JWT Secret{

cd OPTIMAL-INTELLECTS-DocuMind.AI-

  "documents": "https://example.com/document.pdf",

# 2. Create virtual environment

python -m venv venvGenerate strong random string and update:  "questions": ["What is my flight number?"]

venv\Scripts\activate  # Windows

# source venv/bin/activate  # Linux/Mac```env}



# 3. Install dependenciesJWT_SECRET=your-super-secret-jwt-key-change-this```

pip install -r requirements.txt

````

# 4. Configure environment

cp .env.example .env#### Special Cases:

# Edit .env with your credentials (see Configuration section)

---

# 5. Run server

uvicorn logmain:app --reload --host 127.0.0.1 --port 8000- If the `documents` URL contains `"get-secret-token"`, the system fetches the HTML and extracts the token.

```

## 📚 API Endpoints\* If the question involves flights, the system calls HackRx APIs to get the flight number.

### **Access Application**

- 🌐 **Main App**: http://127.0.0.1:8000| Method | Endpoint | Description |#### Response:

- 🔐 **Login/Register**: http://127.0.0.1:8000/login

- 📚 **API Docs**: http://127.0.0.1:8000/docs|--------|----------|-------------|



---| POST | `/api/v1/auth/register` | Register new user |```json



## ⚙️ Configuration| POST | `/api/v1/auth/login` | Login user |{



### **1. MongoDB Atlas Setup**| POST | `/api/v1/upload-pdf` | Upload PDF | "answers": ["Favorite city: New York, Flight Number: XYZ123"]



1. Create account at [MongoDB Atlas](https://cloud.mongodb.com)| POST | `/api/v1/sessions/create` | Create chat session |}

2. Create a **FREE M0 cluster**

3. Create database user (username + password)| GET | `/api/v1/sessions/list` | Get user sessions |```

4. Whitelist IP: `0.0.0.0/0` (for development)

5. Get connection string| POST | `/api/v1/chat` | Chat with document |

6. Update `.env`:

   ```env| POST | `/api/v1/hackrx/summarize` | Summarize conversation |---

   MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net

   ```Full API docs available at `/docs` when server is running.## 🧪 Example Requests



### **2. Azure OpenAI Setup**---**Secret Token Retrieval**



1. Create Azure OpenAI resource in Azure Portal## 🛠️ Tech Stack```json

2. Deploy these models:

   - **gpt-4o-mini** (for chat){

   - **text-embedding-3-large** (for embeddings)

3. Get API key and endpoint**Backend:** "documents": "https://register.hackrx.in/utils/get-secret-token?hackTeam=5563",

4. Update `.env`:

   ```env- FastAPI, Python 3.12 "questions": ["Go to the link and get the secret token and return it"]

   OPENAI_API_KEY=your_azure_api_key

   OPENAI_API_BASE=https://your-resource.openai.azure.com/- PyMuPDF (PDF processing)}

   OPENAI_API_VERSION=2024-12-01-preview

   OPENAI_DEPLOYMENT=gpt-4o-mini- FAISS (vector search)```

   OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-large

   ```- MongoDB (database)



### **3. JWT Secret**- PyJWT + bcrypt (auth)**Flight Number Retrieval**



Generate a strong random string:**AI/ML:**```json

```env

JWT_SECRET=your-super-secret-jwt-key-change-this-to-random-string- Azure OpenAI (GPT-4o-mini){

```

- text-embedding-3-large "documents": "https://hackrx.blob.core.windows.net/hackrx/rounds/FinalRound4SubmissionPDF.pdf",

---

- tiktoken, scikit-learn "questions": ["What is my flight number?"]

## 📡 API Endpoints

}

| Method | Endpoint | Description |

|--------|----------|-------------|**Frontend:**```

| POST | `/api/v1/auth/register` | Register new user |

| POST | `/api/v1/auth/login` | Login and get JWT token |- HTML5, Tailwind CSS, JavaScript

| POST | `/api/v1/upload-pdf` | Upload PDF document |

| POST | `/api/v1/sessions/create` | Create new chat session |- Fetch API for HTTP requests---

| GET | `/api/v1/sessions/list` | Get all user sessions |

| POST | `/api/v1/chat` | Send message and get response |---## 🗄 MongoDB Logging

| POST | `/api/v1/hackrx/summarize` | Summarize conversation |

## 📂 Project StructureEvery request is logged in MongoDB:

**Full interactive API documentation:** http://127.0.0.1:8000/docs

```* `timestamp`

---

├── logmain.py # Main FastAPI application\* `auth_header`

## 📂 Project Structure

├── requirements.txt # Python dependencies\* `request_data`

```

📦 OPTIMAL-INTELLECTS-DocuMind.AI-├── .env.example # Environment template\* `document_url`

├── 📄 logmain.py              # Main FastAPI application (1929 lines)

├── 📄 requirements.txt        # Python dependencies├── static/ # Frontend files\* `question`

├── 📄 .env.example            # Environment variables template

├── 📄 .gitignore              # Git ignore rules│ ├── LoginRegister.html\* `answer`

├── 📄 README.md               # This file

├── 📁 static/                 # Frontend files│ ├── pdf upload.html\* `top_chunks` (retrieved document chunks)

│   ├── Index.html             # Main chat interface

│   ├── LoginRegister.html     # Auth page│ └── Index.html\* `api_result` (for special API logic)

│   └── pdf upload.html        # Upload page

└── 📁 temp_uploads/           # Temporary PDF storage├── temp_uploads/ # Temporary PDF storage

```

└── README.md # This file---

---

```

## 🔒 Security Features

## 📌 Notes

- ✅ **Password Hashing**: bcrypt with salt rounds

- ✅ **JWT Authentication**: Secure token-based auth---

- ✅ **CORS Protection**: Configured allowed origins

- ✅ **Environment Variables**: All secrets in `.env`* Ensure **Azure OpenAI** and **MongoDB Atlas** credentials are set in `.env`

- ✅ **User Session Isolation**: Each user only sees their own data

- ✅ **Input Validation**: FastAPI Pydantic models## 🎯 Usage* Install system packages for PyMuPDF if running on Linux:



---



## 🎨 Special Features1. **Register/Login** - Create account or login



### **Document-Only Responses**2. **Upload PDF** - Drag & drop or click to upload---

The AI is configured to:

- ✅ Only use content from uploaded document3. **Chat** - Ask questions about your document

- ✅ Never add external knowledge or hallucinate

- ✅ Explicitly refuse when information is unavailable4. **Summarize** - Get AI-generated summary of conversation

- ✅ Acknowledge limitations in the document

---

**Example:**

```## 🔒 Security

User: "What is the population of France?"

AI: "This information is not available in the uploaded document."- ✅ Password hashing with bcrypt

```- ✅ JWT token authentication

- ✅ CORS protection

### **Context-Aware Conversations**- ✅ Environment variables for secrets

```- ✅ User session isolation

User: "What is photosynthesis?"

AI: [Explains from document]---



User: "Where does it occur?"## 🎨 Special Features

AI: [Understands "it" = photosynthesis, continues with context]

```### Adaptive Retrieval

System adjusts chunk retrieval based on query:

### **Dark/Light Mode**- **Standard**: 21 chunks

- Toggle between themes- **Detailed** (keywords: detail, depth, comprehensive, etc.): 40 chunks

- Preference saved in browser

- Eye-friendly for long reading sessions### Document-Only Responses

AI configured to:

---- Only use document content

- Never add external knowledge

## 🐛 Troubleshooting- Refuse when info unavailable

- Acknowledge limited content

### **MongoDB Connection Failed**

```---

ERROR: ServerSelectionTimeoutError

```## 🐛 Troubleshooting

**Solution:**

- Check internet connection**MongoDB Connection Failed:**

- Verify `MONGO_URI` in `.env` is correct- Check internet connection

- Ensure IP is whitelisted in MongoDB Atlas- Verify `MONGO_URI` in `.env`

- Confirm cluster is running (not paused)- Ensure IP whitelisted in Atlas

- Check cluster is running

### **Azure OpenAI Errors**

```**Azure OpenAI Errors:**

ERROR: 401 Unauthorized- Verify API key and endpoint

```- Check deployment names match

**Solution:**- Monitor rate limits

- Verify `OPENAI_API_KEY` is correct

- Check `OPENAI_API_BASE` endpoint is valid**PDF Upload Issues:**

- Ensure deployment names match exactly- Ensure valid PDF file

- Check Azure OpenAI quota/limits- Check `temp_uploads/` folder exists

- Verify server has write permissions

### **PDF Upload Issues**

```---

ERROR: Failed to process PDF

```## 📊 Performance

**Solution:**

- Ensure PDF is not corrupted- PDF Processing: 10-30 seconds

- Check `temp_uploads/` folder exists- Query Response: 2-5 seconds

- Verify server has write permissions- Summarization: 3-8 seconds

- Try a different PDF file- FAISS Search: <0.1 seconds



### **Authentication Not Working**---

```

ERROR: 503 Service Unavailable## 🤝 Contributing

```

**Solution:**1. Fork the repository

- MongoDB might be down2. Create feature branch

- Check database connection3. Commit changes

- Server will return 503 if DB unavailable4. Push to branch

5. Open Pull Request

---

---

## 📊 Performance Metrics

## 📄 License

| Operation | Typical Time |

|-----------|-------------|Educational/Hackathon Project

| PDF Processing | 10-30 seconds |

| Query Response | 2-5 seconds |---

| Summarization | 3-8 seconds |

| FAISS Search | <0.1 seconds |## 👥 Team

| Login/Register | <1 second |

**OPTIMAL INTELLECTS**

---

Hackathon Project 2025

## 💡 Usage Tips

---

1. **For Better Results:**

   - Upload clear, well-formatted PDFs## 🙏 Acknowledgments

   - Ask specific questions

   - Use "explain in detail" for comprehensive answers- Azure OpenAI for AI capabilities

- MongoDB Atlas for database

2. **For Faster Responses:**- FastAPI for web framework

   - Keep questions focused- FAISS for vector search

   - Avoid overly broad queries

   - Use session history for context---



3. **For Summarization:****Made with ❤️ for intelligent document analysis**

   - Have at least 3-4 exchanges before summarizing```

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

This is an educational/hackathon project. Feel free to use and modify for learning purposes.

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

*Empowering users to have meaningful conversations with their documents*
`````
