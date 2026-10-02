# 🏛️ House Scrutiny AI — Backend Service
### Autonomous Housing-Society Map Scrutiny & Structural Drawing Verification Agent

[![FastAPI](https://img.shields.io/badge/REST%20API-FastAPI%202.0-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Redis](https://img.shields.io/badge/Cache-Redis%20Keyvalue-DC382D.svg?logo=redis)](https://redis.io/)
[![Neon DB](https://img.shields.io/badge/Database-Neon%20PostgreSQL-00e699.svg?logo=postgresql)](https://neon.tech/)
[![Alembic](https://img.shields.io/badge/Migrations-Alembic-blue.svg)](https://alembic.sqlalchemy.org/)
[![LangGraph](https://img.shields.io/badge/Orchestration-LangGraph-orange.svg)](https://github.com/langchain-ai/langgraph)
[![TypeSafe Jev](https://img.shields.io/badge/Decision%20Gate-TypeSafe%20Jev-purple.svg)](https://typesafe.ai/)
[![OpenAI Vision](https://img.shields.io/badge/Vision-GPT--4o%20%2F%20Multimodal-green.svg?logo=openai)](https://platform.openai.com/)
[![ReportLab](https://img.shields.io/badge/Reports-ReportLab%20Vector%20PDF-brightgreen.svg)](https://www.reportlab.com/)

This directory contains the production **FastAPI 2.0** backend service for **House Scrutiny AI**. It handles drawing parsing, CAD geometry analysis, multi-resolution vision extraction, municipal bylaw auditing, Redis caching, and Neon PostgreSQL memory persistence.

---

## 🚀 Running the Backend

### 1. Python Environment Setup
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Configuration (`.env`)
Create a `.env` file in this directory:
```env
OPENAI_API_KEY=sk-proj-...
TYPESAFE_API_KEY=apikey_...
DATABASE_URL=postgresql://user:password@ep-...neon.tech/neondb?sslmode=require
REDIS_URL=rediss://...keyvalue.render.com:6379
FRONTEND_URL=http://localhost:3000
```

### 3. Launching Server
```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
# Or with FastAPI CLI:
fastapi dev app.py
```

- Alembic migrations (`alembic/versions/001_initial_schema.py`) and AI model seeds are automatically executed during server startup (`lifespan`).
- Redis connectivity is verified immediately on startup, displaying:
  ```text
  [REDIS] Connected successfully: rediss://...
  ```
- Interactive Swagger API docs are available at `http://localhost:8000/docs`.

---

## ⚡ Redis Keyvalue Cache (`src/memory/cache.py`)

- **High Speed**: Caches thread listings (`hs:threads:list`), thread records (`hs:thread:<id>`), and chat messages (`hs:chat:<id>`).
- **Resilience**: Operates with a fail-safe fallback to Neon PostgreSQL and in-memory cache if Redis is temporarily unreachable.
- **TTL Strategy**:
  - `hs:threads:list`: 30 seconds (invalidated immediately on new audits or deletes).
  - `hs:thread:<id>`: 300 seconds (5 minutes).
  - `hs:chat:<id>`: 20 seconds.
  - `hs:models`: 600 seconds (10 minutes).

---

## 🏛️ Modular API Router Architecture (`src/api/`)

The backend follows an industry-grade modular folder structure:
- **`src/api/routers/scrutinize.py`**: Autonomous synchronous drawing scrutiny, multi-file packages, and LangGraph milestone SSE stream with HITL cancellation.
- **`src/api/routers/threads.py`**: Thread persistence, chat history, and SSE token streaming with `await request.is_disconnected()` HITL cancellation check.
- **`src/api/routers/cases.py`**: SQLite review cases, engineer approvals, and drawing evidence page rendering.
- **`src/api/routers/models.py`**: Dynamic multimodal AI model catalog, provider listing, custom model registration, and active model selection.
- **`src/api/routers/reports.py`**: Official PDF compliance report generation and statutory municipal bylaws queries.
- **`src/api/schemas.py`**: Typed Pydantic request and response models.
- **`src/api/common.py`**: Shared validation and execution helpers.

---

## 🛑 Human-in-the-Loop (HITL) Stream Cancellation

Both chat streaming (`POST /api/v1/threads/{id}/chat`) and drawing scrutiny streaming (`POST /api/v1/scrutinize/stream`) check for client disconnections on every yielded token or node milestone:
```python
if await request.is_disconnected():
    logger.info("🛑 [HITL] Client stopped generation")
    break
```
When aborted by the client via `AbortController`, the backend immediately stops downstream LLM consumption, closes the stream, and persists the partial response marked with `*(Generation stopped by user)*`.

---

## 🧪 Testing & Evals
```bash
# Run all 74+ automated unit and integration tests
python -m pytest tests/ -v

# Run targeted chatbot evaluation and router tests
python -m pytest tests/test_chatbot_eval.py tests/test_api_routers.py -v

# Run DeepEval golden dataset benchmark
python evals/run_evals.py
```
