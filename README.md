# Activiity Chatbot v0.2

Multi-model RAG chatbot for the Activiity knowledge base. Compare answers from different LLMs with live RAGAS evaluation.

## Quick Start

```bash
# 1. Install
pip install -r requirements.txt

# 2. Set API key
#    Get one at https://openrouter.ai/keys
set OPENROUTER_API_KEY=sk-or-v1-YOUR-KEY

# 3. Start
python -m uvicorn webapp.server:app --port 8788 --host 127.0.0.1
```

Open http://localhost:8788

## Features

- **Compare mode** — Ask one question, get answers from multiple models side-by-side
- **RAG retrieval** — Vector search over the Activiity knowledge base (28 documents)
- **RAGAS metrics** — Live evaluation: Faithfulness, Answer Relevancy, Correctness
- **Two modes** — Naive (retrieve + generate) or Agentic (ReAct router)
- **History** — Past conversations saved locally, searchable and exportable

## Stack

Python · FastAPI · LlamaIndex · Qdrant · OpenRouter · RAGAS

## Docs

| File | What |
|------|------|
| [guide.md](guide.md) | Full deployment guide |
| [release_notes.md](release_notes.md) | What's new |
| [.env.example](.env.example) | Configure your API key |
