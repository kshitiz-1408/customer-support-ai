# Customer Support AI

[![Continuous Integration](https://github.com/your-username/your-repo/actions/workflows/ci.yml/badge.svg)](https://github.com/your-username/your-repo/actions/workflows/ci.yml)

Customer Support AI is a production-ready, clean-architecture application designed to handle multi-agent ticketing workflows and Retrieval-Augmented Generation (RAG) tasks. 

This repository features a fully responsive, dark-mode-optimized Next.js frontend and a modular FastAPI backend, integrated with local sentence embeddings, FAISS vector indexing, dynamic intent detection, specialized agent routing, and MongoDB Atlas database persistence with local file fallback.

---

### 📌 Project Features

The portal serves as an interactive, role-aware support ecosystem:
- **State-of-the-Art Admin Panel**: Complete, consolidated administrator portal to monitor and audit the platform (Manage Users, Manage Tickets, Inspect Chats, Manage KB, Analytics, Audit Logs, and System Status).
- **Intelligent Support Chat**: Interactive multi-turn chat. Automatically detects user query intents and routes them to specialized agents (FAQ, Product, Billing, Technical, Complaint), grounded using RAG.
- **Support Ticket CRUD & Scoping**: Scoped ticket creation, update, listing, and deletion. Standard users are restricted to their own tickets, while admins have global visibility.
- **Document Pipeline Ingestion (RAG)**: Chunks, embeds, and indexes support documents (PDF/TXT/MD/DOCX) into local FAISS vector stores.
- **Structured Audit Logs Registry**: Automatic, append-only logging of security-critical and administrative operations.
- **Uptime & Service Health Monitors**: Live healthchecks, CPU/Memory resource gauges, database latencies, and browser offline triggers.

---

## 🏗️ Architecture

```
                          +------------------------+
                          |    Next.js Client      |
                          | (React/TS/TailwindCSS) |
                          +-----------+------------+
                                      |
                                      | HTTP Requests (Axios Client with Token Rotations)
                                      v
                          +-----------+------------+
                          |    FastAPI Backend     |
                          +-----------+------------+
                                      |
                                      +------------------------+
                                      |                        |
                                      v                        v
                          +-----------+------------+  +--------+---------------+
                          |    API Router v1       |  |  AI Pipeline Modules  |
                          | (tickets.py / admin.py)|  | (agents, RAG, FAISS)   |
                          +-----------+------------+  +--------+---------------+
                                      |                        |
                                      v                        v
                          +-----------+------------+  +--------+---------------+
                          |    Business Services   |  |   Database Adapter     |
                          | (Ticket / Chat / Audit)|  |  (MongoDB / Fallback)  |
                          +------------------------+  +------------------------+
```

1. **Frontend Client**: React Single Page Application utilizing Next.js App Router. Integrates route-guard layouts and dynamic token synchronization.
2. **API Endpoint Router**: Secures paths using FastAPI dependencies and validates payloads using Pydantic validation schemas.
3. **Core Services**: Modular services coordinating business logic (e.g., `TicketService`, `UserService`, `AuditService`).
4. **AI Pipeline**:
   * **Intent Detection**: Context-aware intent classifier routing queries to specialized agents.
   * **RAG Engine**: SentenceTransformers local embedding generator combined with FAISS similarity vector indexing.
   * **LLM Connector**: Resilience-wrapped Google Gemini LLM API client.
5. **Data Registry Layer**: PyMongo Atlas client with persistent failover, optimized connection pools, and automatic collection indexing.

---

## 📂 Folder Structure

```text
customer-support-ai/
│
├── frontend/                     # Next.js client
│   ├── src/
│   │   ├── app/                  # App Router pages (admin panel, chat, tickets, settings)
│   │   ├── components/           # UI elements (Navbar, Sidebar, Chat components)
│   │   ├── context/              # Auth, Theme contexts (theme switcher, session recovery)
│   │   └── services/             # Axios API client (silent token refresh queue interceptors)
│   ├── package.json
│   └── tsconfig.json
│
├── backend/                      # FastAPI server
│   ├── api/                      # API endpoint handlers & security dependencies
│   ├── agents/                   # Micro-agents implementation & intent routers
│   ├── database/                 # MongoDB database adapter & collection setups
│   ├── embeddings/               # SentenceTransformer embedding generators
│   ├── models/                   # Pydantic schemas validating payloads
│   ├── rag/                      # RAG parsing pipeline (PDF, DOCX loaders)
│   ├── services/                 # Business logic wrappers (LLM service, Audit service)
│   ├── tests/                    # 101 E2E automated test cases
│   ├── utils/                    # Observability logging and error handlers
│   └── main.py                   # Lifespan resource setup & FastAPI app startup
│
├── scripts/                      # System promote & password reset command-line tools
├── knowledge_base/               # Knowledge Base raw documents storage
└── compose.yaml                  # Multi-container production deployment setup
```

---

## 🔒 Authentication & RBAC

### JWT Lifecycle & Rotations
* **Access Tokens**: Short-lived (15 minutes) tokens encapsulating `sub`, `email`, `role`, and `type: "access"`.
* **Refresh Tokens**: Long-lived (7 days) tokens. Re-verifies active database sessions against the user's `refresh_token_version` on every rotation check, preventing token hijacking.
* **Axios Interceptors**: The client intercepts `401 Unauthorized` responses and silently requests `/auth/refresh`. Multiple concurrent queries are queued during a refresh cycle to avoid duplicate rotation calls.

### Role-Based Access Controls (RBAC) Matrix
* **`user` role**: Scoped read/write capabilities. Normal registration defaults to user privileges.
* **`admin` role**: Global read/write capabilities across the platform.

| Capability / Resource | User | Admin | Endpoint Protection |
| :--- | :---: | :---: | :--- |
| Create Chat / Ticket | ✓ | ✓ | Scoped to authenticated user token. |
| View Chat / Ticket history | Scoped | ✓ | Scoped ownership checks (403 if mismatch). |
| Manage Users / Roles | ✗ | ✓ | Guarded via `get_current_admin` dependency. |
| Manage KB / Embeddings | ✗ | ✓ | Guarded via `get_current_admin` dependency. |
| View System Monitoring / Audit | ✗ | ✓ | Guarded via `get_current_admin` dependency. |

---

## 📄 Knowledge Base Ingestion Workflow
```
[Raw Files (.docx, .pdf, .txt, .md)] -> [File Upload API] -> [DOCX/PDF Custom Text Extraction]
                                                                        |
                                                                        v
[MongoDB metadata: indexed, chunk_count, file_size] <- [DB Log] <- [Text Chunking & Embedding]
                                                                        |
                                                                        v
[FAISS FlatIP Similarity Vector Storage] <------------------------- [FAISS Indexing]
```
1. **Extraction**: Parsed directly in-process via custom parsers (supporting `.docx` via zip-xml tree extractions).
2. **Chunking**: Chunks document text, maps them to `SentenceTransformer` vectors, and appends them to FAISS.
3. **Reindexing**: Administrators can trigger re-indexing on a single document or rebuild the entire vector store index.

---

## 📊 Analytics, Audits, & System Status

### 1. Structured Audit Log Registry
Every administrative or security-critical action triggers an append-only document write into the `audit_logs` collection:
* **Fields persisted**: `timestamp`, `actor_user_id`, `actor_email`, `actor_role`, `action`, `resource_type`, `resource_id`, `status`, `ip_address`, `user_agent`, and differences (`previous_value`, `new_value`).
* **Logged actions**: Login success/failure (with failure reason context), logout, user activation switches, role changes, file uploads/deletions, KB reindexings, ticket creations, updates, and chat inspections.

### 2. Analytics KPIs Dashboard
Collects usage and latency stats:
* `/analytics/overview`: counters for active users, open/closed tickets, documents count.
* `/analytics/usage`: daily metrics timelines.
* `/analytics/ai`: average confidence score, Gemini api call counts, and intent classification histograms.
* `/analytics/system`: database connection checks, CPU, memory, and FAISS vector index sizes.

### 3. System Status Health Probes
Provides real-time visibility into internal server services:
* `/system/health`: Lightweight liveness indicator checking backend, database, Gemini API, and RAG status.
* `/system/performance`: Measures system memory/CPU percent, requests per minute, database latency, and average response times.
* `/system/services`: Performs checks on individual backend adapters (MongoDB Atlas ping, Gemini API connection, SentenceTransformers caching, and FAISS disk binary status).

---

## ⚙️ Installation & Configuration

### Prerequisites
* Node.js (v18.0.0 or later)
* Python (v3.11 or later)
* Docker (for multi-container deployment)

### Local Development Setup

1. **Configure Environment variables**:
   * Create `backend/.env` using the template `backend/.env.example`.
   * Create `frontend/.env.local` using the template `frontend/.env.example`.
   * *Critical*: Ensure default secrets (e.g. `CHANGE_ME_SECRET_KEY_FOR_PRODUCTION`) are replaced. The backend will refuse to boot in `production` if placeholders are detected.

2. **Initialize Backend**:
   ```bash
   cd backend
   pip install -r requirements.txt
   uvicorn main:app --reload --port 8000
   ```
   *Swagger endpoints documentation is available at [http://localhost:8000/docs](http://localhost:8000/docs).*

3. **Initialize Frontend**:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

4. **Verify Test Suite**:
   ```bash
   cd backend
   python -m pytest tests/ -v
   ```

---

## 🚀 Docker Containerization & Production Deployments

The application is configured to build and start the entire multi-container service stack locally:

1. **Build Container Binaries**:
   ```bash
   docker compose build
   ```
2. **Start Services in Background**:
   ```bash
   docker compose up -d
   ```
3. **Verify Status**:
   ```bash
   docker compose ps
   ```
4. **Stop Containers**:
   ```bash
   docker compose down
   ```


- **Request ID Tracking**: Every API request is correlated using a unique `request_id` passed via the `X-Request-ID` HTTP header and isolated per-request via Python context variables.
- **Structured Logging**: Clean, JSON-formatted structured logging with automatic regex-based credential redaction (`MONGODB_URI`, `GEMINI_API_KEY` placeholders).
- **Latency Instrumentation**: Detailed pipeline stage measurements (`intent_detection`, `history_loading`, `rag_retrieval`, `llm_generation`, `history_persistence`) logged to track bottleneck and execution flow performance.
- **Bounded Failover & Retries**: Automatic exponential backoff retries with jitter for transient dependencies (Gemini rate-limit 429 errors) and isolated FAISS/MongoDB fallback bounds to guarantee graceful service degradation.
- **Health & Diagnostics Probes**:
  - `GET /health/live`: Lightweight liveness probe verifying that the FastAPI process is responsive. No downstream checks are performed.
  - `GET /health/ready`: Deep readiness probe checking MongoDB connection (via ping), FAISS index load, and SentenceTransformer model cache status. Returns `503 Service Unavailable` on failures.
  - `GET /health`: Preserved legacy check for basic client compatibility.

---

## 📊 Quality Evaluation & Benchmarking Suites

The repository contains three reproducible quality benchmarking modules located under `backend/evaluation/`:

### 1. Vector Retrieval Evaluation (Task 7)
Measures the vector similarity search performance against a labeled search set:
```bash
cd backend
python -m evaluation.evaluate_retrieval
```
*Outputs baseline retrieval stats (Hit@5, Recall@5, MRR, nDCG@5).*

### 2. Answer Quality & Hallucination Evaluation (Task 8)
Assesses claim support and hallucination rate of generated LLM assistant answers:
```bash
cd backend
python -m evaluation.evaluate_answers
```
*Evaluates claims groundedness against retrieved context articles.*

### 3. Intent Detection & Agent Routing Evaluation (Task 9)
Measures accuracy and macro F1 metrics of the query classification engine:
```bash
cd backend
python -m evaluation.evaluate_intents
```
*Runs offline experiments (regex word boundary matching, precedence swaps) to optimize query classification.*

---

## 🗄️ MongoDB Production Architecture & Resilience

To meet enterprise durability and reliability standards, the MongoDB persistence layer is hardened with:
- **Optimized Connection Pooling**: Configured with `minPoolSize=5` and `maxPoolSize=50` to support concurrent user sessions. Equipped with connection timeouts and `socketTimeoutMS` to handle network issues.
- **Dynamic Self-Healing Reconnection**: The `/health/ready` check detects database disconnection and automatically triggers reconnection attempts.
- **Enforced DB Indexing**: Auto-creates performance-critical indexes on application startup:
  - `conversations`: Compound indexes on `[("session_id", 1), ("updated_at", -1)]` and `[("user_id", 1), ("updated_at", -1)]` to support rapid dashboard load and conversation retrievals.
  - `messages`: Compound index on `[("conversation_id", 1), ("created_at", -1)]` for quick historical thread rendering.
  - `tickets`: Unique indexes on `id` and `ticket_id` to maintain transactional integrity.
- **Production Safety Controls**: Local file-backed database fallbacks are automatically bypassed in `production` environments or when `MONGODB_URI` is specified. Any failure to connect in production raises a strict `RuntimeError` immediately to prevent silent failure.
- **Automated Validation Suite**: All configurations, pooling settings, liveness endpoints, and index creation logic are tested using `backend/tests/test_mongodb.py`.

---

## 🧪 Testing & Continuous Integration (CI)

The project includes complete unit and integration testing pipelines that can be run both locally and automatically in the cloud.

### Local Test Execution
- **Backend Tests**: Run pytest using `APP_ENV=test` to run tests locally offline (bypassing live Gemini and MongoDB Atlas integrations):
  ```bash
  cd backend
  python -m pytest tests/ -v
  ```
- **Frontend Quality Check**: Run the linter and Next.js compiler locally to verify no build issues:
  ```bash
  cd frontend
  npm run lint
  npm run build
  ```

### GitHub Actions CI Pipeline
On every `push` and `pull_request` to the `main` branch, the [ci.yml](file:///.github/workflows/ci.yml) workflow triggers parallel validation stages:
1. **Backend Tests (Python 3.11)**: Configures dependency caching, runs pip installs, and executes pytest integrations.
2. **Frontend Lint & Build (Node.js 20)**: Configures npm caching, runs eslint, and performs compilation build checks.
3. **Docker Build Verification**: Runs docker builds for both backend and frontend `Dockerfile` binaries to verify compilation success.

---

## 🛠️ Troubleshooting

### 1. Model Download Timeouts / Offline Boot Failures
- **Problem**: The first boot or container launch triggers Hugging Face downloads and times out.
- **Solution**: Pre-download weights and store them in the persistent directory `backend/data/hf_cache` or use the Docker image layer pre-warm.

### 2. MongoDB Connection Failures in Production
- **Problem**: Backend fails to start with `RuntimeError: Database connection is offline`.
- **Solution**: Verify `MONGODB_URI` in `.env` is correctly populated and Atlas IP Access List (firewall) allows connection from your host/container IP.

### 3. CORS Violations
- **Problem**: Next.js frontend console displays CORS error when querying the backend API.
- **Solution**: Check that `ALLOWED_ORIGINS` in `backend/.env` contains your exact frontend origin (e.g. `["http://localhost:3000"]`).

---

## ⚠️ Known Limitations

### 1. FAISS CPU Index Deletions
- The flat vector store `IndexFlatIP` does not support incremental document/chunk deletions. Removing or updating articles requires triggering a full rebuild via `POST /api/v1/kb/rebuild`.

### 2. Memory Mock Database
- In non-production/development settings without MongoDB credentials, the system falls back to a single-file JSON database (`mock_mongo.json`). This fallback does not support high-concurrency transactional locking.

### 3. Local Embedding Latencies
- High local CPU utilization during dense SentenceTransformers computations. For production workloads, consider offloading embeddings to dedicated services.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
