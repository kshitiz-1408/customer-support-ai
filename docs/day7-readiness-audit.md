# Day 7 Deployment Readiness and Environment Audit Report

## 1. Executive Summary

This audit report evaluates the deployment readiness, environment configuration isolation, containerization boundaries, and portability of the `customer-support-ai` application. While both the Next.js frontend and FastAPI backend function correctly in local development, several critical deployment blockers (P0/P1) must be resolved before the application can be safely deployed to a production-like environment.

* **Deployment Readiness Status**: **NOT READY (WITH CRITICAL BLOCKERS)**

---

## 2. Repository and Project Structure

### 2.1 Entry Points
* **Backend Entry Point**: [`backend/main.py`](file:///C:/Users/HP/.gemini/antigravity-ide/scratch/customer-support-ai/backend/main.py) (run via `uvicorn main:app`).
* **Frontend Entry Point**: [`frontend/src/app/page.tsx`](file:///C:/Users/HP/.gemini/antigravity-ide/scratch/customer-support-ai/frontend/src/app/page.tsx) / [`frontend/src/app/chat/page.tsx`](file:///C:/Users/HP/.gemini/antigravity-ide/scratch/customer-support-ai/frontend/src/app/chat/page.tsx) (Next.js App Router).

### 2.2 Dependencies
* **Backend Dependencies**: [`backend/requirements.txt`](file:///C:/Users/HP/.gemini/antigravity-ide/scratch/customer-support-ai/backend/requirements.txt) (contains unpinned `>=` bounds).
* **Frontend Dependencies**: [`frontend/package.json`](file:///C:/Users/HP/.gemini/antigravity-ide/scratch/customer-support-ai/frontend/package.json) / [`frontend/package-lock.json`](file:///C:/Users/HP/.gemini/antigravity-ide/scratch/customer-support-ai/frontend/package-lock.json) (reproducible locks present).

### 2.3 Runtime Assumptions
* **Python version**: Assumes Python 3.11+.
* **Node.js version**: Assumes Node.js v18+.
* **Runtime-generated directories**: `knowledge_base/` for FAISS indexing; `__pycache__` and `.pytest_cache/`.

---

## 3. Environment Configuration Audit

### 3.1 Variables Inventory

| Variable Name | Required/Optional | Scope | Secret? | Default Present | Safe Production Default | Validation Exist? | Consuming Source |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| `PROJECT_NAME` | Optional | Backend | No | Yes ("Customer Support AI") | Yes | No | `config/config.py` |
| `API_V1_STR` | Optional | Backend | No | Yes ("/api/v1") | Yes | No | `config/config.py` |
| `DEBUG` | Optional | Backend | No | Yes (`True`) | **No (needs False)** | No | `config/config.py` |
| `HOST` | Optional | Backend | No | Yes ("0.0.0.0") | Yes | No | `config/config.py` |
| `PORT` | Optional | Backend | No | Yes (`8000`) | Yes | No | `config/config.py` |
| `ALLOWED_ORIGINS` | Required | Backend | No | Yes (`["http://localhost:3000"]`) | **No (needs prod domain)** | Yes | `config/config.py` |
| `DATABASE_URL` | Optional | Backend | No | Yes (`sqlite://...`) | Yes (SQLite) | No | `config/config.py` |
| `GEMINI_API_KEY` | **Required** | Backend | **Yes** | No (`None`) | **No** | Yes | `config/config.py`, `llm_service.py` |
| `GEMINI_MODEL_NAME` | Optional | Backend | No | Yes ("gemini-2.5-flash") | Yes | No | `config/config.py` |
| `MONGODB_URI` | **Required** | Backend | **Yes** | No (`None`) | **No** | No | `config/config.py`, `database.py` |
| `MONGODB_DB_NAME` | Optional | Backend | No | Yes ("customer_support_ai") | Yes | No | `config/config.py` |
| `NEXT_PUBLIC_API_URL`| Required | Frontend | No | Yes (`http://localhost:8000`) | **No (needs backend domain)** | No | `api.ts`, `Navbar.tsx` |

---

## 4. Hardcoded Development Assumptions

1. **Evaluation report output paths**:
   - **File**: `backend/evaluation/evaluate_answers.py` and `evaluate_intents.py`.
   - **Assumptions**: Hardcoded home-directory folder outputs: `~/.gemini/antigravity-ide/brain/19a93036-5576-4401-8a01-827787595b36/`.
   - **Risk**: Crashes in non-development or CI runtime environments.
2. **Localhost CORS**:
   - **File**: `backend/config/config.py`.
   - **Assumptions**: Allowed CORS defaults to `http://localhost:3000`.
   - **Risk**: Production frontend queries will fail due to CORS policy block.
3. **Frontend API URL**:
   - **File**: `frontend/src/services/api.ts` and `Navbar.tsx`.
   - **Assumptions**: Falls back to `http://localhost:8000` if `NEXT_PUBLIC_API_URL` is omitted.
   - **Risk**: Attempts to query client's localhost in production.

---

## 5. Backend Runtime Readiness

* **Lifespan handlers**: Relies on deprecated `@app.on_event` tags. Needs conversion to standard FastAPI `lifespan` context manager.
* **MongoDB offline failure**: Does not crash the process; logs error and falls back gracefully to `mock_mongo.json`.
* **Gemini missing credentials**: Process starts cleanly; throws exception lazily on first query execution.
* **FAISS index missing**: Process starts cleanly; initializes a blank FAISS CPU index.
* **Shutdown cleanups**: Calls `close_db()` correctly to dispose client sockets.

---

## 6. Frontend Deployment Readiness

* **Production build command**: `npm run build` (generates static Next.js production files cleanly).
* **Production start command**: `npm run start`.
* **TypeScript & Linting**: Verified passing with **0 errors and 0 warnings**.
* **Browser-visible variables**: `NEXT_PUBLIC_API_URL` is exposed in browser bundles, which is safe as it is a public URL, not a secret credential.

---

## 7. Database and API Integration Readiness

### 7.1 MongoDB Atlas
* **MongoClient reuse**: MongoClient pool is stored as a global singleton `db_client` and reused across request threads.
* **TLS & Timeouts**: MongoDB timeouts (`serverSelectionTimeoutMS`) are set to 5000ms.
* **Auto-creation**: PyMongo automatically creates collections and builds indexes (`conversation_id`, `ticket_id`) on startup.

### 7.2 CORS Boundaries
* **Wildcards**: No wildcard origins (`*`) are used when credentials are set to `True`, satisfying strict security policies.

### 7.3 Gemini API
* **SDK client**: Fully updated to the modern `google-genai` SDK package.

---

## 8. FAISS and Embedding Portability

* **Local Cache Dependencies**: `SentenceTransformer` cache folder defaults to `~/.cache/huggingface`.
* **Cold-Start Latency Risk**: Model is downloaded lazily on first request. Initial query triggers a 90MB+ file download, introducing severe latency spikes (5-30s) or failing in offline environments.
* **Multi-replica scale drift**: Since FAISS indexes are saved locally in the container's disk, horizontal scaling introduces index context drift (replicas cannot share RAG updates).

---

## 9. Dependency and Path Portability

* **Dependency reproducibility**: `requirements.txt` has unpinned package definitions, which exposes the system to breaking upstream package updates.
* **Path delimiters**: No hardcoded backslashes are present; paths use `os.path.join` which resolves delimiters natively across platforms.

---

## 10. Health and Readiness Semantics

* `GET /health` proves liveness and lightweight MongoDB client reachability.
* **Readiness Gap**: Does not check if the local FAISS index file is populated or if the local SentenceTransformer embedding model cache is pre-warmed.

---

## 11. Stateful vs Stateless Component Matrix

| Component | State Type | Shared or Local | Persistent? | Multi-replica Risk |
| :--- | :--- | :--- | :---: | :--- |
| **MongoDB Atlas** | Database | Shared | Yes | None (pooled network client) |
| **FAISS Vector Index**| File | Local-only | Yes | **High** (context drift across instances) |
| **mock_mongo.json** | File | Local-only | Yes | **High** (write collisions / loss on restart) |
| **ContextVar** | Memory | Request-local | No | None |
| **_model cache** | Memory | Process-local | No | None |

---

## 12. Production Blockers Classification

### P0 — Prevents Safe Deployment
* **P0-01**: Hardcoded Home Directory Paths in Evaluators.
* **P0-02**: Mutating mock DB file `mock_mongo.json` inside source tree at runtime.

### P1 — Serious Production Risk
* **P1-01**: Unpinned dependencies in `requirements.txt`.
* **P1-02**: Lazy HuggingFace Embedding Model download at first request (cold-start latency).
* **P1-03**: FAISS local file replication context drift (cannot scale horizontally).

### P2 — Important Improvement
* **P2-01**: Deprecated `@app.on_event` lifespan hooks.
* **P2-02**: Hardcoded backend API URL fallbacks in Next.js bundle.

### P3 — Technical Debt
* **P3-01**: Missing readiness checks for FAISS index and embedding caches in `/health`.

---

## 13. Deployment Target Configuration

* **FastAPI Backend**: Requires a Python 3.11 container runtime with outbound access to Gemini and MongoDB Atlas ports, and storage volumes for embedding/FAISS persistence.
* **Next.js Frontend**: Scalable serverless or static export host (e.g. Vercel, Netlify) with environment variable injection.

---

## 14. Revised Day 7 Schedule

We propose following this revised sequence to address all audited P0/P1 blockers:

* **Task 2**: Hardening environment configurations & pinning python dependencies.
* **Task 3**: Dynamic persistence path configurations (moving mock DB / FAISS path variables out of the source tree).
* **Task 4**: Pre-downloading/caching embedding models inside Docker runtime images.
* **Task 5**: Migrating backend startup to the FastAPI `lifespan` manager and strengthening health/readiness endpoints.
* **Task 6**: Hardening CORS, network boundaries, and environment configurations.
* **Task 7**: Implementing Docker configurations and container build files.
* **Task 8**: Designing CI pipelines with GitHub Actions for linting/testing.
* **Task 9**: Security audits, secret detection runs, and final configuration tests.
* **Task 10**: Integration simulation and final git checkpoint.
