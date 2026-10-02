# 🏛️ House Scrutiny AI
### Autonomous Enterprise Housing-Society Map Scrutiny & Structural Drawing Verification Agent

[![Next.js](https://img.shields.io/badge/Frontend-Next.js%2016%20%2F%20React%2019-black.svg?logo=next.js)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/REST%20API-FastAPI%202.0-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Redis](https://img.shields.io/badge/Cache-Redis%20Keyvalue-DC382D.svg?logo=redis)](https://redis.io/)
[![Neon DB](https://img.shields.io/badge/Database-Neon%20PostgreSQL-00e699.svg?logo=postgresql)](https://neon.tech/)
[![Alembic](https://img.shields.io/badge/Migrations-Alembic-blue.svg)](https://alembic.sqlalchemy.org/)
[![TanStack Query](https://img.shields.io/badge/State-TanStack%20React%20Query%20v5-FF4154.svg?logo=react-query)](https://tanstack.com/query)
[![LangGraph](https://img.shields.io/badge/Orchestration-LangGraph-orange.svg)](https://github.com/langchain-ai/langgraph)
[![TypeSafe Jev](https://img.shields.io/badge/Decision%20Gate-TypeSafe%20Jev-purple.svg)](https://typesafe.ai/)
[![OpenAI Vision](https://img.shields.io/badge/Vision-GPT--4o%20%2F%20Multimodal-green.svg?logo=openai)](https://platform.openai.com/)
[![ReportLab](https://img.shields.io/badge/Reports-ReportLab%20Vector%20PDF-brightgreen.svg)](https://www.reportlab.com/)

**House Scrutiny AI** is a production-grade autonomous agentic auditing platform engineered to automate municipal regulatory scrutiny and structural engineering validation of architectural blueprints, structural drawings, and stability certificates. It rigorously evaluates compliance against municipal building authorities (e.g., **CDA Islamabad**, **DHA Lahore**, **LDA**, **Bahria Town**, and **OPF Islamabad**) and civil engineering codes.

Featuring a monorepo architecture, House Scrutiny AI pairs a high-performance **Next.js 16** frontend (powered by TanStack React Query and Server-Sent Events) with a **FastAPI** backend orchestrating a deterministic **LangGraph** pipeline, **TypeSafe Jev** eligibility gating, **Neon PostgreSQL** persistent memory, **Alembic** migrations, and an ultra-fast **Redis** keyvalue cache.

---

## 📑 Table of Contents
- [✨ Key Capabilities & What's New](#-key-capabilities--whats-new)
- [🔄 Architecture Overview](#-architecture-overview)
- [📂 Repository Structure](#-repository-structure)
- [🚀 Quickstart & Setup](#-quickstart--setup)
  - [Prerequisites](#prerequisites)
  - [Backend Setup & Alembic Migrations](#1-backend-setup--alembic-migrations)
  - [Frontend Setup](#2-frontend-setup)
  - [Environment Variables (.env)](#3-environment-variables-env)
- [⚡ Redis Cache & Resilience](#-redis-cache--resilience)
- [🧠 Scrutiny Memory Architecture](#-scrutiny-memory-architecture)
- [🌐 REST API Reference](#-rest-api-reference)
- [🤖 Multimodal Model Switching](#-multimodal-model-switching)
- [🧪 Evaluation & Automated Testing](#-evaluation--automated-testing)
- [🔒 Security & Anti-Injection Architecture](#-security--anti-injection-architecture)
- [📄 License](#-license)

---

## ✨ Key Capabilities & What's New

- **Modular Industry-Grade FastAPI 2.0 Backend Architecture**:
  - Replaced monolithic single-file routing with a modular `src/api/` layout featuring dedicated routers (`cases.py`, `models.py`, `reports.py`, `threads.py`, `scrutinize.py`), typed Pydantic schemas, and centralized common execution utilities.
- **Human-in-the-Loop (HITL) Real-Time Cancellation**:
  - Interactive "Stop Generating" and "Stop Pipeline" controls in the frontend powered by `AbortController`.
  - Backend real-time client disconnection detection via `await request.is_disconnected()`, saving partial replies cleanly with `*(Generation stopped by user)*`.
- **Chatbot Evaluation & Grounding Suite**:
  - Post-report follow-up chat evaluated against ground-truth audit verdicts for factual accuracy, structural parameter citation (PSI, thickness, rebar grade), anti-hallucination guardrails, and markdown formatting.
- **Modern Next.js 16 + React 19 Frontend**:
  - Powered by **TanStack React Query v5** for instant cache synchronization, background re-fetching, and fast UI transitions.
  - **Thread Synchronization via URL**: Preserves session state directly in the URL (`/?thread_id=...`) so refreshing the page maintains active thread, report, and chat history.
  - **Real-Time Streaming Chat (SSE)**: Chat with technical scrutiny reports in real-time with smooth token-by-token typewriter rendering.
  - **Official PDF Reader Dialog & Clipboard Tools**: Read generated PDF audit reports directly in an embedded viewer with download and new tab options, plus instant message copy actions.
  - **Glassmorphic Engineering UI**: Interactive inspection panels, vector CAD drawing viewer, bylaw checklist breakdown, and downloadable PDF reports.
- **Resilient Redis Keyvalue Caching**:
  - Thin, fail-safe caching layer ([`backend/src/memory/cache.py`](backend/src/memory/cache.py)) for Render Keyvalue, Redis Cloud, or local instances.
  - Real-time terminal feedback on startup (`[REDIS] Connected successfully: <url>`).
  - Automatic graceful degradation to Neon DB and in-memory cache if Redis is temporarily unreachable.
- **Alembic Migration Pipeline**:
  - Production schema versioning managed via Alembic ([`backend/alembic/`](backend/alembic/)).
  - Runs migrations automatically upon FastAPI startup via `lifespan(app)`.
- **Real-Time HTTP Request Middleware**:
  - Detailed terminal logging of all API requests with color status indicators, HTTP method, path, and millisecond execution duration.
- **Dynamic Multimodal AI Model Switcher**:
  - Runtime model switching backed by the database model catalog (`ai_models`), supporting OpenAI GPT-4o, Claude 3.5 Sonnet, Gemini 1.5 Pro, and specialized engineering vision models.

---

## 🔄 Architecture Overview

```
                      ┌─────────────────────────────────────────┐
                      │        NEXT.JS 16 WEB FRONTEND          │
                      │   • TanStack React Query v5             │
                      │   • URL-driven state (?thread_id=...)   │
                      │   • Real-time SSE Chat Stream           │
                      └────────────────────┬────────────────────┘
                                           │ HTTP / SSE
                                           ▼
                      ┌─────────────────────────────────────────┐
                      │           FASTAPI REST BACKEND          │
                      │   • Request logging middleware          │
                      │   • Lifespan startup migrations         │
                      │   • Dynamic Model Switcher              │
                      └───────┬─────────────────────────┬───────┘
                              │                         │
               ┌──────────────┴──────────────┐          │
               ▼                             ▼          ▼
┌─────────────────────────────┐ ┌─────────────────────────┐ ┌─────────────────────────┐
│     REDIS CACHE LAYER       │ │   NEON POSTGRESQL DB    │ │  LANGGRAPH STATE GRAPH  │
│ • TTL-based thread listing  │ │ • Alembic migrations    │ │ 1. n_ingest (CAD parse) │
│ • Instant chat retrieval    │ │ • scrutiny_threads      │ │ 2. n_gate (TypeSafe Jev)│
│ • Graceful fallback logic   │ │ • thread_messages       │ │ 3. n_crop (Focus zones) │
│ • Immediate terminal logs   │ │ • ai_models catalog     │ │ 4. n_extract (Vision)   │
└─────────────────────────────┘ └─────────────────────────┘ │ 5. n_judge (Bylaws)     │
                                                            │ 6. n_report (Verdict)   │
                                                            └─────────────────────────┘
```

---

## 📂 Repository Structure

```text
house-securinity/
├── backend/
│   ├── alembic/                # Alembic database migrations
│   │   ├── versions/           # Versioned migration scripts (001_initial_schema.py)
│   │   └── env.py              # Migration environment
│   ├── alembic.ini             # Alembic configuration
│   ├── app.py                  # Production FastAPI REST application & endpoints
│   ├── bylaw.json              # Authority bylaw limits & guidelines
│   ├── docs.md                 # In-depth architectural & technical specification
│   ├── evals/                  # DeepEval benchmarks & golden evaluation dataset
│   ├── pdf_generator.py        # Vector PDF audit report generator
│   ├── requirements.txt        # Backend Python dependencies
│   ├── src/
│   │   ├── api/                # Modular FastAPI 2.0 routers, schemas & common helpers
│   │   │   ├── routers/        # Dedicated endpoints (cases, models, reports, threads, scrutinize)
│   │   │   ├── common.py       # Shared execution & validation handlers
│   │   │   └── schemas.py      # Pydantic V2 request & response models
│   │   ├── auditors/           # Bylaw, completeness, evidence & conflict auditors
│   │   ├── config/             # Bylaw rules, schemas, prompts & pydantic settings
│   │   ├── core/               # PyMuPDF CAD vector extraction, security & duplicates
│   │   ├── memory/             # Dual-tier memory (database.py, cache.py, long_term.py)
│   │   ├── pipeline/           # LangGraph StateGraph nodes (ingest, gate, crop, extract, judge, report)
│   │   ├── reporting/          # ReportLab signed PDF generator
│   │   └── vision/             # Dynamic crop selector & high-res vision extraction
│   └── tests/                  # 74+ automated pytest & chatbot evaluation test suites
├── frontend/
│   ├── app/                    # Next.js 16 App Router (layout, page, providers)
│   ├── components/             # UI components, ThreadSidebar, ReportViewer, ChatDrawer
│   ├── hooks/                  # Custom hooks & TanStack Query mutations/queries
│   ├── lib/                    # API client, utility functions & types
│   ├── package.json            # Node.js dependencies
│   └── public/                 # Static assets & brand icons
├── .gitignore                  # Production gitignore (excludes .env, node_modules, .venv)
├── docs.md                     # Root technical architecture documentation
└── README.md                   # Root repository README
```

---

## 🚀 Quickstart & Setup

### Prerequisites
- **Python**: `3.10` or higher
- **Node.js**: `18.0` or higher (`npm` or `pnpm`)
- **PostgreSQL**: Neon DB connection string or local PostgreSQL 15+
- **Redis** *(Optional but recommended)*: Render Keyvalue / Redis Cloud / local Docker

---

### 1. Backend Setup & Alembic Migrations

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # macOS / Linux:
   source .venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure your `.env` file (see [Environment Variables](#3-environment-variables-env)).
5. Launch the FastAPI server:
   ```bash
   uvicorn api:app --host 0.0.0.0 --port 8000 --reload
   ```
   > **Note**: Database migrations (`alembic upgrade head`) and model seeding run automatically on startup via FastAPI's `lifespan` handler!

---

### 2. Frontend Setup

1. Open a new terminal and navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install frontend dependencies:
   ```bash
   npm install
   ```
3. Start the Next.js development server:
   ```bash
   npm run dev
   ```
4. Access the application in your browser at `http://localhost:3000`.

---

### 3. Environment Variables (.env)

Create a `backend/.env` file with the following keys:

```env
# ── AI Providers ─────────────────────────────────────────────────────────────
OPENAI_API_KEY=sk-proj-...
TYPESAFE_API_KEY=apikey_...

# ── Observability (LangSmith Tracing) ─────────────────────────────────────────
LANGSMITH_TRACING=true
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_API_KEY=lsv2_pt_...
LANGSMITH_PROJECT=house-scrutiny-ai

# ── Primary Database (Neon PostgreSQL) ────────────────────────────────────────
DATABASE_URL=postgresql://user:password@ep-shiny-breeze-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require

# ── Cache Layer (Redis Keyvalue) ──────────────────────────────────────────────
# Render Keyvalue External URL (or local redis://localhost:6379)
REDIS_URL=rediss://red-dav42tu0tbcc73dh444g:YOUR_PASSWORD@oregon-keyvalue.render.com:6379
```

---

## ⚡ Redis Cache & Resilience

The Redis caching layer is implemented in [`backend/src/memory/cache.py`](backend/src/memory/cache.py) and operates with **zero hard dependencies**:
- **Automatic Connection Verification**: On startup, the backend establishes a connection and logs confirmation immediately:
  ```text
  [REDIS] Connected successfully: rediss://...
  ```
- **Graceful Fallback**: If Redis is offline or DNS resolution fails, the app logs a clean warning and transparently falls back to Neon PostgreSQL and local memory without dropping requests.
- **Configured TTLs**:
  - Scrutiny Threads List (`hs:threads:list`): `30s` (invalidated on new scrutiny / delete)
  - Individual Thread Record (`hs:thread:{id}`): `300s` (5 min)
  - Thread Chat History (`hs:chat:{id}`): `20s`
  - Multimodal AI Model Catalog (`hs:models`): `600s` (10 min)

---

## 🧠 Scrutiny Memory Architecture

The system utilizes a dual-tier persistence model:

1. **Short-Term Working Memory** ([`src/memory/short_term.py`](backend/src/memory/short_term.py)):
   - Stores per-page CAD vector geometry, title block extractions, and temporary bounding crops in LangGraph state.
2. **Long-Term Knowledge Memory** ([`src/memory/long_term.py`](backend/src/memory/long_term.py)):
   - **Neon PostgreSQL**: Stores complete scrutiny audits, engineering parameters (concrete PSI, slab thickness, completeness scores), execution runtimes, and thread messages.
   - **Redis Cache-Aside**: Accelerates thread listing, audit retrieval, and chat history queries.

---

## 🌐 REST API Reference

| Method | Endpoint | Description | Cache Layer |
| :--- | :--- | :--- | :--- |
| `GET` | `/` | Service discovery & root metadata | Direct |
| `GET` | `/health` | Service health & liveness probe | Direct |
| `POST` | `/api/v1/scrutinize` | Run scrutiny on single uploaded PDF | DB write + Cache invalidation |
| `POST` | `/api/v1/scrutinize/package`| Scrutinize multi-page package with model selection | DB write + Cache invalidation |
| `GET` | `/api/v1/threads` | List all historical scrutiny threads | **Redis Cache** (`hs:threads:list`) |
| `GET` | `/api/v1/threads/{id}` | Get complete audit verdict for thread | **Redis Cache** (`hs:thread:{id}`) |
| `DELETE`| `/api/v1/threads/{id}` | Delete thread and audit data | DB write + Cache invalidation |
| `POST` | `/api/v1/threads/{id}/chat` | Ask technical questions about scrutiny | DB write + Cache invalidation |
| `GET` | `/api/v1/threads/{id}/chat/stream` | Stream real-time answers (SSE) | Direct Stream |
| `GET` | `/api/v1/models` | List available multimodal AI models | **Redis Cache** (`hs:models`) |
| `GET` | `/api/v1/reports/pdf` | Download signed ReportLab PDF report | Dynamic generation |
| `GET` | `/api/v1/bylaws` | Retrieve society bylaw parameters | In-memory |

---

## 🤖 Multimodal Model Switching

House Scrutiny AI supports dynamic runtime switching across leading multimodal models without restarting the service:

| Provider | Model Identifier | Strengths |
| :--- | :--- | :--- |
| **OpenAI** | `gpt-4o` *(Default)* | Exceptional spatial reasoning, structural table analysis |
| **OpenAI** | `gpt-4o-mini` | Low latency, cost-effective for initial screening |
| **Anthropic** | `claude-3-5-sonnet-20241022` | Ultra-high OCR fidelity on dense CAD blueprints |
| **Google** | `gemini-1.5-pro` | Massive context window for large 100+ page sets |
| **Google** | `gemini-1.5-flash` | Rapid classification & eligibility verification |

Models are managed in the database catalog table `ai_models` and can be switched dynamically per scrutiny request.

---

## 🧪 Evaluation & Automated Testing

### Unit & Integration Tests
Run the comprehensive test suite (74+ tests covering routers, nodes, auditors, and memory):
```bash
cd backend
python -m pytest tests/ -v
```

### Chatbot Grounding & HITL Evaluation Suite
Run the targeted chatbot evaluation suite:
```bash
cd backend
python -m pytest tests/test_chatbot_eval.py tests/test_api_routers.py -v
```
Evaluates:
- **Structural Grounding**: Cites precise concrete PSI, slab thickness, and steel grade from audit context.
- **Anti-Hallucination Guardrails**: Detects when structural-only drawings lack architectural floor plans and refuses to invent heights or setbacks.
- **HITL Cancellation Protocol**: Verifies prompt and stream formatting when response generation is terminated early by the user.

### DeepEval Benchmark Suite
Run the rigorous Golden Dataset evaluation:
```bash
cd backend
python evals/run_evals.py
```
Evaluates:
- **Spatial Precision**: Ground truth vs. extracted setback & height numbers.
- **Hallucination Rate**: Zero-tolerance checks against raw vector CAD coordinates.
- **Bylaw Accuracy**: Verifies mathematical verdicts against municipal codes.

---

## 🔒 Security & Anti-Injection Architecture

Construction drawings and architectural PDFs frequently contain untrusted user text, layered PDF comments, and obscure CAD annotations. House Scrutiny AI incorporates multi-layer defenses:

1. **Vector-Layer Prompt Injection Sanitization**: Strips hidden text layers, white-on-white text, and deceptive prompt override strings before vision prompting.
2. **File De-duplication**: MD5 vector geometry hashing prevents denial-of-service from redundant page processing.
3. **TypeSafe Jev Gating**: Non-engineering documents (e.g., invoices, bank statements, resumes) are rejected immediately at Node 2, spending 0 expensive multimodal vision tokens.
4. **Isolated Extraction Batches**: Architectural, Structural, and Certificate passes run in isolated contexts to prevent cross-contamination of values.

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.
