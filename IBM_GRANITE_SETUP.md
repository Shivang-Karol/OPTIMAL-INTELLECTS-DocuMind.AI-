# IBM Granite Model Setup Guide

## 🎯 Quick Setup for IBM watsonx.ai

### 1. Get IBM watsonx.ai Account

1. Go to [IBM Cloud](https://cloud.ibm.com/)
2. Sign up for a free account (or use existing)
3. Navigate to **watsonx.ai**
4. Create a new project

### 2. Get API Credentials

1. In your watsonx.ai project, go to **Manage** → **Access (IAM)**
2. Create an API key
3. Copy your:
   - API Key
   - Project ID
   - Service URL (usually `https://us-south.ml.cloud.ibm.com`)

### 3. Update .env File

Add these lines to your `.env`:

```env
# IBM watsonx.ai Granite Model Configuration
GRANITE_API_KEY=your_ibm_api_key_here
GRANITE_PROJECT_ID=your_project_id_here
GRANITE_URL=https://us-south.ml.cloud.ibm.com
```

### 4. Install IBM SDK

```bash
pip install ibm-watsonx-ai
```

### 5. Test It!

```python
from ibm_watsonx_ai.foundation_models import Model

model = Model(
    model_id="ibm/granite-13b-chat-v2",
    credentials={
        "url": "https://us-south.ml.cloud.ibm.com",
        "apikey": "YOUR_API_KEY"
    },
    project_id="YOUR_PROJECT_ID"
)

result = model.generate_text("Hello, IBM Granite!")
print(result)
```

---

## 🤖 Available Granite Models

### For Summarization (Recommended)

- **granite-13b-chat-v2** - Best for conversation and summarization
- **granite-20b-multilingual** - Supports multiple languages
- **granite-3b-code-instruct** - Optimized for code (if needed)

---

## 💡 Why Use Granite?

1. **IBM Partnership** - Shows integration with IBM ecosystem
2. **Optimized for Enterprise** - Better for structured data
3. **Cost-Effective** - Competitive pricing
4. **Multilingual** - Supports multiple languages
5. **Hackathon Edge** - Demonstrates multi-model architecture

---

## 🔄 Fallback Behavior

If Granite is not configured or fails:

- System automatically falls back to Azure OpenAI GPT-4o-mini
- No disruption to user experience
- Error is logged for debugging

---

## 📊 Performance Comparison

| Feature            | IBM Granite | GPT-4o-mini |
| ------------------ | ----------- | ----------- |
| Speed              | ~2-3s       | ~1-2s       |
| Cost               | Lower       | Moderate    |
| Quality            | Excellent   | Excellent   |
| Multilingual       | ✅ Better   | ✅ Good     |
| Code Understanding | ✅ Better   | ✅ Good     |

---

## 🎯 For Hackathon Demo

Show both models side-by-side:

```python
# Demo script
session_id = "demo_session_123"

# Summarize with Granite
granite_summary = await summarize_session({
    "session_id": session_id,
    "use_granite": True
})

# Summarize with GPT
gpt_summary = await summarize_session({
    "session_id": session_id,
    "use_granite": False
})

# Compare results
print("Granite Summary:", granite_summary["summary"])
print("GPT Summary:", gpt_summary["summary"])
```

---

## 🔐 Security Best Practices

1. **Never commit .env file** - Add to .gitignore
2. **Use environment variables** - Don't hardcode keys
3. **Rotate keys regularly** - IBM allows key rotation
4. **Monitor usage** - Set up billing alerts

---

## 🆘 Common Issues

### Issue: "Import error for ibm_watsonx_ai"

**Solution:**

```bash
pip install ibm-watsonx-ai --upgrade
```

### Issue: "Authentication failed"

**Solution:**

- Verify API key is correct
- Check if key has expired
- Ensure project_id matches

### Issue: "Model not found"

**Solution:**

- Check model_id spelling
- Verify model is available in your region
- Try alternative model: `ibm/granite-13b-chat-v2`

---

## 📚 Additional Resources

- [IBM watsonx.ai Documentation](https://dataplatform.cloud.ibm.com/docs/content/wsj/analyze-data/fm-models.html)
- [Granite Models Overview](https://www.ibm.com/products/watsonx-ai/foundation-models)
- [Python SDK Reference](https://ibm.github.io/watsonx-ai-python-sdk/)

---

**Ready to showcase IBM integration! 🚀**
