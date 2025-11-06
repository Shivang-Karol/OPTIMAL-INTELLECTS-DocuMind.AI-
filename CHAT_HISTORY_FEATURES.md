# 🎓 Chat History & Summarization Features

## Overview

Three powerful new features have been added to enhance the learning experience:

1. **📜 Chat History** - Access previous conversations by session
2. **📋 Session Management** - View all your study sessions
3. **✨ AI Summarization** - Quick revision with IBM Granite or GPT

---

## 🚀 New API Endpoints

### 1. Main Endpoint (Enhanced)

**POST** `/api/v1/hackrx/run`

Now returns a `session_id` for tracking conversations!

```json
{
  "documents": "https://example.com/policy.pdf",
  "questions": ["What is covered?", "What is the cost?"],
  "session_id": "session_20250106_143022_a1b2c3d4" // Optional - auto-generated if not provided
}
```

**Response:**

```json
{
  "answers": ["Answer 1", "Answer 2"],
  "session_id": "session_20250106_143022_a1b2c3d4"
}
```

---

### 2. Chat History Endpoint ✨ NEW

**POST** `/api/v1/hackrx/history`

Retrieve all Q&A pairs from a specific session.

**Request:**

```json
{
  "session_id": "session_20250106_143022_a1b2c3d4"
}
```

**Response:**

```json
{
  "session_id": "session_20250106_143022_a1b2c3d4",
  "history": [
    {
      "question": "What is IVF treatment cost?",
      "answer": "IVF treatment costs $10,000-15,000 per cycle...",
      "timestamp": "2025-01-06T14:30:45",
      "document_url": "https://example.com/policy.pdf",
      "message_type": "qa_pair"
    },
    {
      "question": "What documents are required?",
      "answer": "You need medical records, ID proof...",
      "timestamp": "2025-01-06T14:31:12",
      "document_url": "https://example.com/policy.pdf",
      "message_type": "qa_pair"
    }
  ],
  "total_messages": 2
}
```

---

### 3. List All Sessions ✨ NEW

**GET** `/api/v1/hackrx/sessions`

View all your previous study sessions.

**Response:**

```json
{
  "sessions": [
    {
      "session_id": "session_20250106_143022_a1b2c3d4",
      "first_message": "What is IVF treatment cost?",
      "first_timestamp": "2025-01-06T14:30:22",
      "last_timestamp": "2025-01-06T14:35:10",
      "message_count": 5,
      "document_url": "https://example.com/policy.pdf"
    },
    {
      "session_id": "session_20250105_091534_f5g6h7i8",
      "first_message": "Explain the claim process",
      "first_timestamp": "2025-01-05T09:15:34",
      "last_timestamp": "2025-01-05T09:45:22",
      "message_count": 8,
      "document_url": "https://example.com/claims.pdf"
    }
  ],
  "total_sessions": 2
}
```

---

### 4. Summarize Session ✨ NEW

**POST** `/api/v1/hackrx/summarize`

Get AI-generated summary of entire conversation for quick revision!

**Request:**

```json
{
  "session_id": "session_20250106_143022_a1b2c3d4",
  "use_granite": true // true = IBM Granite, false = GPT-4o-mini
}
```

**Response:**

```json
{
  "session_id": "session_20250106_143022_a1b2c3d4",
  "summary": "This study session covered health insurance policy details, focusing on IVF treatment coverage and hospitalization benefits. The discussion explored costs, documentation requirements, and claim procedures. Key topics included coverage limits, waiting periods, and pre-authorization requirements for specialized treatments.",
  "key_points": [
    "IVF treatment costs $10,000-15,000 per cycle with 50% coverage up to $25,000",
    "Pre-authorization required 2 weeks before treatment",
    "Required documents: medical records, ID proof, marriage certificate",
    "Hospitalization covered for 30 days per year",
    "2-year waiting period for pre-existing conditions"
  ],
  "total_messages": 5,
  "model_used": "ibm-granite"
}
```

---

## 🛠️ Setup Instructions

### 1. Environment Variables

Add to your `.env` file:

```env
# Existing variables
OPENAI_API_BASE=https://your-azure-openai-endpoint
OPENAI_API_KEY=your-azure-api-key
OPENAI_API_VERSION=2024-02-15-preview
OPENAI_DEPLOYMENT=gpt-4o-mini
OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-large
MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net

# NEW: IBM Granite Model (Optional - for summarization)
GRANITE_API_KEY=your-ibm-watsonx-api-key
GRANITE_PROJECT_ID=your-ibm-project-id
GRANITE_URL=https://us-south.ml.cloud.ibm.com
```

### 2. Install Dependencies

If using IBM Granite model:

```bash
pip install ibm-watsonx-ai
```

Or update requirements.txt:

```bash
pip install -r requirements.txt
```

### 3. MongoDB Collections

Two collections are now used:

- **CheckRequest** - Legacy logs (backward compatible)
- **ChatSessions** - New organized chat history

Indexes are auto-created on startup for optimal performance.

---

## 💡 Use Cases

### For Students 📚

1. **Study Session Continuity**

   - Start studying a document
   - Take a break
   - Resume with full context using session_id

2. **Quick Revision**

   - Use `/summarize` before exams
   - Get key points without re-reading entire conversation
   - Focus on important concepts

3. **Progress Tracking**
   - View all study sessions
   - See what topics were covered
   - Identify areas needing more attention

### For Educators 👨‍🏫

1. **Monitor Student Learning**

   - Review student questions via session history
   - Identify common misconceptions
   - Improve teaching materials

2. **Create Study Guides**
   - Generate summaries for multiple sessions
   - Compile key points across topics
   - Build comprehensive review materials

---

## 🔧 Frontend Integration

### React Example

```javascript
import axios from "axios";

const API_BASE = "http://localhost:8000/api/v1/hackrx";

// 1. Start or continue a session
async function askQuestions(documentUrl, questions, sessionId = null) {
  const response = await axios.post(`${API_BASE}/run`, {
    documents: documentUrl,
    questions: questions,
    session_id: sessionId, // null for new session
  });

  // Save session_id for later
  localStorage.setItem("currentSession", response.data.session_id);

  return response.data;
}

// 2. Get chat history
async function getChatHistory(sessionId) {
  const response = await axios.post(`${API_BASE}/history`, {
    session_id: sessionId,
  });

  return response.data.history;
}

// 3. List all sessions
async function getAllSessions() {
  const response = await axios.get(`${API_BASE}/sessions`);
  return response.data.sessions;
}

// 4. Summarize session
async function summarizeSession(sessionId, useGranite = true) {
  const response = await axios.post(`${API_BASE}/summarize`, {
    session_id: sessionId,
    use_granite: useGranite,
  });

  return response.data;
}

// Usage Example
const run = async () => {
  // Ask questions
  const result = await askQuestions("https://example.com/textbook.pdf", [
    "Explain photosynthesis",
    "What are the stages?",
  ]);

  console.log("Session ID:", result.session_id);
  console.log("Answers:", result.answers);

  // Later: Get history
  const history = await getChatHistory(result.session_id);
  console.log("Chat History:", history);

  // Summarize for revision
  const summary = await summarizeSession(result.session_id);
  console.log("Summary:", summary.summary);
  console.log("Key Points:", summary.key_points);
};
```

### Simple HTML/JavaScript Example

```html
<!DOCTYPE html>
<html>
  <head>
    <title>Study Assistant</title>
  </head>
  <body>
    <h1>Study Assistant with Chat History</h1>

    <!-- Session Selection -->
    <div>
      <button onclick="loadSessions()">Load My Sessions</button>
      <select id="sessionSelect" onchange="loadHistory()">
        <option value="">-- Select Session --</option>
      </select>
      <button onclick="summarizeCurrentSession()">Summarize</button>
    </div>

    <!-- Chat Display -->
    <div id="chatHistory"></div>

    <!-- Summary Display -->
    <div id="summary" style="display:none;">
      <h3>Summary</h3>
      <p id="summaryText"></p>
      <h4>Key Points</h4>
      <ul id="keyPoints"></ul>
    </div>

    <script>
      const API_BASE = "http://localhost:8000/api/v1/hackrx";
      let currentSessionId = null;

      async function loadSessions() {
        const response = await fetch(`${API_BASE}/sessions`);
        const data = await response.json();

        const select = document.getElementById("sessionSelect");
        select.innerHTML = '<option value="">-- Select Session --</option>';

        data.sessions.forEach((session) => {
          const option = document.createElement("option");
          option.value = session.session_id;
          option.textContent = `${session.first_message.substring(0, 50)}... (${
            session.message_count
          } messages)`;
          select.appendChild(option);
        });
      }

      async function loadHistory() {
        const sessionId = document.getElementById("sessionSelect").value;
        if (!sessionId) return;

        currentSessionId = sessionId;

        const response = await fetch(`${API_BASE}/history`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ session_id: sessionId }),
        });

        const data = await response.json();

        const chatDiv = document.getElementById("chatHistory");
        chatDiv.innerHTML = "<h3>Chat History</h3>";

        data.history.forEach((item) => {
          chatDiv.innerHTML += `
                    <div style="margin: 10px 0; padding: 10px; border: 1px solid #ddd;">
                        <strong>Q:</strong> ${item.question}<br>
                        <strong>A:</strong> ${item.answer}<br>
                        <small>${item.timestamp}</small>
                    </div>
                `;
        });
      }

      async function summarizeCurrentSession() {
        if (!currentSessionId) {
          alert("Please select a session first");
          return;
        }

        const response = await fetch(`${API_BASE}/summarize`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            session_id: currentSessionId,
            use_granite: true,
          }),
        });

        const data = await response.json();

        document.getElementById("summaryText").textContent = data.summary;

        const keyPointsList = document.getElementById("keyPoints");
        keyPointsList.innerHTML = "";
        data.key_points.forEach((point) => {
          const li = document.createElement("li");
          li.textContent = point;
          keyPointsList.appendChild(li);
        });

        document.getElementById("summary").style.display = "block";
      }
    </script>
  </body>
</html>
```

---

## 🎨 UI Design Suggestions

### Chat History Button

```
┌─────────────────────────────────┐
│  📜 Chat History               │
│                                 │
│  Recent Sessions:              │
│  • Session from 2 hours ago    │
│  • Session from yesterday      │
│  • Session from Jan 5          │
│                                 │
│  [Load] [Summarize] [Delete]   │
└─────────────────────────────────┘
```

### Summarize Button

```
┌─────────────────────────────────┐
│  ✨ Quick Revision Summary      │
│                                 │
│  📝 Summary:                    │
│  This session covered...        │
│                                 │
│  🔑 Key Points:                 │
│  • Point 1                      │
│  • Point 2                      │
│  • Point 3                      │
│                                 │
│  Generated by: 🤖 IBM Granite   │
└─────────────────────────────────┘
```

---

## 🔐 MongoDB Schema

### ChatSessions Collection

```javascript
{
  "_id": ObjectId("..."),
  "session_id": "session_20250106_143022_a1b2c3d4",
  "timestamp": ISODate("2025-01-06T14:30:45Z"),
  "document_url": "https://example.com/policy.pdf",
  "question": "What is IVF treatment cost?",
  "answer": "IVF treatment costs...",
  "top_chunks": ["chunk1", "chunk2", "chunk3"],
  "api_result": "",
  "message_type": "qa_pair"
}
```

**Indexes:**

- `session_id` (for fast session lookups)
- `session_id + timestamp` (for chronological sorting)

---

## 📊 Analytics Possibilities

With chat history, you can now analyze:

1. **Most Common Questions** - What topics students ask about
2. **Session Duration** - How long study sessions last
3. **Document Popularity** - Which documents are studied most
4. **Learning Patterns** - Peak study times, session frequency
5. **Difficulty Indicators** - Questions requiring multiple follow-ups

---

## 🎯 Hackathon Impact

### IBM Partnership Integration ✅

- Uses IBM Granite model for summarization
- Showcases IBM watsonx.ai capabilities
- Demonstrates hybrid AI approach (Azure + IBM)

### Student Benefits ✅

- Better learning continuity
- Quick revision capability
- Progress tracking
- Reduced cognitive load

### Innovation Points ✅

- Hybrid AI architecture
- Smart session management
- Context-aware summarization
- Scalable MongoDB design

---

## 🚀 Testing the Features

### 1. Test Chat History

```bash
# Start a session
curl -X POST http://localhost:8000/api/v1/hackrx/run \
  -H "Content-Type: application/json" \
  -d '{
    "documents": "https://example.com/doc.pdf",
    "questions": ["Question 1", "Question 2"]
  }'

# Note the session_id in response

# Get history
curl -X POST http://localhost:8000/api/v1/hackrx/history \
  -H "Content-Type: application/json" \
  -d '{"session_id": "YOUR_SESSION_ID"}'
```

### 2. Test Summarization

```bash
curl -X POST http://localhost:8000/api/v1/hackrx/summarize \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "YOUR_SESSION_ID",
    "use_granite": true
  }'
```

### 3. List Sessions

```bash
curl http://localhost:8000/api/v1/hackrx/sessions
```

---

## 🎓 Mentor Presentation Points

1. **Problem Solved**

   - Students lose context between study sessions
   - Need quick revision without re-reading everything
   - Want to track learning progress

2. **Solution Implemented**

   - Session-based chat history
   - AI-powered summarization
   - Multi-model support (Azure + IBM)

3. **Technical Excellence**

   - MongoDB for scalable storage
   - Indexed queries for performance
   - Async processing for speed
   - Clean REST API design

4. **IBM Integration**

   - IBM Granite model for summarization
   - Showcases watsonx.ai capabilities
   - Fallback to ensure reliability

5. **Future Enhancements**
   - Voice-based session replay
   - Collaborative study sessions
   - AI-generated quizzes from history
   - Spaced repetition scheduling

---

## 📝 Notes

- **Session ID Format**: `session_YYYYMMDD_HHMMSS_RANDOM`
- **Auto-generation**: If no session_id provided, one is created automatically
- **Model Selection**: Granite is used if configured, otherwise falls back to GPT
- **Performance**: Indexed MongoDB queries ensure <100ms response time
- **Scalability**: Supports millions of sessions with proper indexing

---

## 🆘 Troubleshooting

### Issue: "No history found"

- Check if session_id is correct
- Verify MongoDB connection
- Ensure data was logged properly

### Issue: Granite summarization fails

- Check GRANITE_API_KEY is set
- Verify IBM project_id
- System auto-falls back to GPT

### Issue: Slow history retrieval

- Check MongoDB indexes are created
- Limit history to recent N messages
- Consider pagination for large sessions

---

**Ready to revolutionize student learning! 🚀📚**
