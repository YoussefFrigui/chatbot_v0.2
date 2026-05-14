# Quick Deploy Guide - Activiity Chatbot v0.2

## Prerequisites
- Python 3.10+
- OpenRouter API key (get free key at https://openrouter.ai/keys)

## 1. Install Dependencies
```powershell
cd chatbot_v0.2
pip install -r requirements.txt
```

## 2. Start Server
```powershell
# Set your API key
$env:OPENROUTER_API_KEY = "sk-or-v1-YOUR-KEY-HERE"

# Start the server
python -m uvicorn webapp.server:app --port 8788 --host 127.0.0.1
```

## 3. Use
Open http://localhost:8788 in your browser.

## Troubleshooting

**Error: NotImplementedError**
- Make sure you set `OPENROUTER_API_KEY` before starting
- Restart the server after setting the key
- Check your API key is valid at https://openrouter.ai/keys

**No models work**
- Verify API key: `curl https://openrouter.ai/api/v1/models -H "Authorization: Bearer YOUR-KEY"`
- If using naive mode - ensure `lib/baseline` is available
- If using agentic mode - ensure `lib/activiity` is available and Qdrant is running

**Want to use UI to enter API key instead?**
1. Start server without env var: `python -m uvicorn webapp.server:app --port 8788`
2. Open http://localhost:8788
3. Go to **Settings** tab
4. Enter your API key and click "Save API Key"

## Quick Check
```powershell
# Check server is running
Invoke-WebRequest -Uri http://localhost:8788/api/config
```

Should return JSON with `"rag_available": true` if everything works.