# API Testing Examples

## Using cURL

### 1. Ask Questions (Create Session)

```bash
curl -X POST http://localhost:8000/api/v1/hackrx/run \
  -H "Content-Type: application/json" \
  -d '{
    "documents": "https://hackrx.blob.core.windows.net/hackrx/rounds/FinalRound4SubmissionPDF.pdf",
    "questions": [
      "What is this document about?",
      "What are the key topics covered?"
    ]
  }'
```

**Response:**

```json
{
  "answers": ["This document is about...", "Key topics include..."],
  "session_id": "session_20250106_143022_a1b2c3d4"
}
```

---

### 2. Continue Existing Session

```bash
curl -X POST http://localhost:8000/api/v1/hackrx/run \
  -H "Content-Type: application/json" \
  -d '{
    "documents": "https://hackrx.blob.core.windows.net/hackrx/rounds/FinalRound4SubmissionPDF.pdf",
    "questions": ["Can you explain more about topic X?"],
    "session_id": "session_20250106_143022_a1b2c3d4"
  }'
```

---

### 3. Get Chat History

```bash
curl -X POST http://localhost:8000/api/v1/hackrx/history \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "session_20250106_143022_a1b2c3d4"
  }'
```

**Response:**

```json
{
  "session_id": "session_20250106_143022_a1b2c3d4",
  "history": [
    {
      "question": "What is this document about?",
      "answer": "This document is about...",
      "timestamp": "2025-01-06T14:30:22",
      "document_url": "https://...",
      "message_type": "qa_pair"
    }
  ],
  "total_messages": 2
}
```

---

### 4. List All Sessions

```bash
curl http://localhost:8000/api/v1/hackrx/sessions
```

**Response:**

```json
{
  "sessions": [
    {
      "session_id": "session_20250106_143022_a1b2c3d4",
      "first_message": "What is this document about?",
      "first_timestamp": "2025-01-06T14:30:22",
      "last_timestamp": "2025-01-06T14:35:10",
      "message_count": 5,
      "document_url": "https://..."
    }
  ],
  "total_sessions": 1
}
```

---

### 5. Summarize Session (GPT)

```bash
curl -X POST http://localhost:8000/api/v1/hackrx/summarize \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "session_20250106_143022_a1b2c3d4",
    "use_granite": false
  }'
```

---

### 6. Summarize Session (IBM Granite)

```bash
curl -X POST http://localhost:8000/api/v1/hackrx/summarize \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "session_20250106_143022_a1b2c3d4",
    "use_granite": true
  }'
```

**Response:**

```json
{
  "session_id": "session_20250106_143022_a1b2c3d4",
  "summary": "This study session covered...",
  "key_points": ["Key point 1", "Key point 2", "Key point 3"],
  "total_messages": 5,
  "model_used": "ibm-granite"
}
```

---

## Using Postman

### Collection Setup

1. Create new collection: "RAG Chat History API"
2. Set base URL variable: `{{base_url}}` = `http://localhost:8000`
3. Add requests:

#### Request 1: Create Session

- **Method:** POST
- **URL:** `{{base_url}}/api/v1/hackrx/run`
- **Body (JSON):**

```json
{
  "documents": "https://hackrx.blob.core.windows.net/hackrx/rounds/FinalRound4SubmissionPDF.pdf",
  "questions": ["What is this about?"]
}
```

- **Tests (JavaScript):**

```javascript
pm.test("Status is 200", function () {
  pm.response.to.have.status(200);
});

// Save session_id for next requests
const response = pm.response.json();
pm.environment.set("session_id", response.session_id);
```

#### Request 2: Get History

- **Method:** POST
- **URL:** `{{base_url}}/api/v1/hackrx/history`
- **Body (JSON):**

```json
{
  "session_id": "{{session_id}}"
}
```

#### Request 3: Summarize

- **Method:** POST
- **URL:** `{{base_url}}/api/v1/hackrx/summarize`
- **Body (JSON):**

```json
{
  "session_id": "{{session_id}}",
  "use_granite": false
}
```

---

## Using Python Requests

```python
import requests

API_BASE = "http://localhost:8000/api/v1/hackrx"

# 1. Create session and ask questions
response = requests.post(f"{API_BASE}/run", json={
    "documents": "https://hackrx.blob.core.windows.net/hackrx/rounds/FinalRound4SubmissionPDF.pdf",
    "questions": [
        "What is this document about?",
        "What are the main topics?"
    ]
})

data = response.json()
session_id = data["session_id"]
print(f"Session ID: {session_id}")
print(f"Answers: {data['answers']}")

# 2. Get history
response = requests.post(f"{API_BASE}/history", json={
    "session_id": session_id
})

history = response.json()
print(f"Total messages: {history['total_messages']}")
for item in history['history']:
    print(f"Q: {item['question']}")
    print(f"A: {item['answer'][:100]}...")

# 3. Summarize
response = requests.post(f"{API_BASE}/summarize", json={
    "session_id": session_id,
    "use_granite": False
})

summary = response.json()
print(f"\nSummary: {summary['summary']}")
print(f"Key Points:")
for point in summary['key_points']:
    print(f"  • {point}")
```

---

## Using JavaScript/Fetch

```javascript
const API_BASE = "http://localhost:8000/api/v1/hackrx";

// 1. Create session
async function createSession() {
  const response = await fetch(`${API_BASE}/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      documents:
        "https://hackrx.blob.core.windows.net/hackrx/rounds/FinalRound4SubmissionPDF.pdf",
      questions: ["What is this about?", "What are key topics?"],
    }),
  });

  const data = await response.json();
  console.log("Session ID:", data.session_id);
  return data.session_id;
}

// 2. Get history
async function getHistory(sessionId) {
  const response = await fetch(`${API_BASE}/history`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId }),
  });

  const data = await response.json();
  console.log("History:", data.history);
  return data;
}

// 3. Summarize
async function summarize(sessionId) {
  const response = await fetch(`${API_BASE}/summarize`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: sessionId,
      use_granite: false,
    }),
  });

  const data = await response.json();
  console.log("Summary:", data.summary);
  console.log("Key Points:", data.key_points);
  return data;
}

// Run all
async function run() {
  const sessionId = await createSession();
  await new Promise((r) => setTimeout(r, 2000)); // Wait 2s for MongoDB
  await getHistory(sessionId);
  await summarize(sessionId);
}

run();
```

---

## Error Responses

### Session Not Found

```json
{
  "session_id": "session_invalid",
  "history": [],
  "total_messages": 0,
  "message": "No history found for this session"
}
```

### Invalid Request

```json
{
  "detail": [
    {
      "loc": ["body", "session_id"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### Server Error

```json
{
  "detail": "Internal server error"
}
```

---

## Rate Limiting (Production)

For production, add rate limiting:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/api/v1/hackrx/run")
@limiter.limit("10/minute")  # 10 requests per minute
async def hackrx_run(...):
    ...
```

---

## Health Check Endpoint (Add this)

```python
@app.get("/health")
async def health_check():
    """Check if server is running and dependencies are accessible."""
    try:
        # Test MongoDB
        mongo_client.admin.command('ping')
        mongo_status = "connected"
    except:
        mongo_status = "disconnected"

    return {
        "status": "healthy",
        "mongodb": mongo_status,
        "azure_openai": "configured" if api_key else "not configured",
        "ibm_granite": "configured" if USE_GRANITE else "not configured"
    }
```

Test health:

```bash
curl http://localhost:8000/health
```

---

## WebSocket Support (Future Enhancement)

For real-time updates:

```python
from fastapi import WebSocket

@app.websocket("/ws/chat/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    await websocket.accept()
    while True:
        question = await websocket.receive_text()
        # Process question
        answer = await answer_question_with_rag(...)
        await websocket.send_json({
            "question": question,
            "answer": answer
        })
```

---

**Ready to test! 🚀**

Start with the Python test script (`test_features.py`) for automated testing,
then move to manual testing with cURL or Postman.
