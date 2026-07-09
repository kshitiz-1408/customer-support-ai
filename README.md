# Customer Support AI

Customer Support AI is a production-ready, clean-architecture application designed to handle multi-agent ticketing workflows and Retrieval-Augmented Generation (RAG) tasks. 

This repository features a fully responsive, dark-mode-optimized Next.js frontend and a modular FastAPI backend, integrated with local sentence embeddings, FAISS vector indexing, dynamic intent detection, specialized agent routing, and MongoDB Atlas database persistence with local file fallback.

---

## 📌 Project Features

The portal serves as an interactive workplace for support agents and customers alike:
- **Intelligent Dashboard**: Displays live ticket statuses (Open, In Progress, Resolved) and database document counts.
- **Support Chat Portal**: Interactive multi-turn chat assistant. Automatically detects user query intents and routes them to specialized agents (FAQ, Product, Billing, Technical, Complaint).
- **Retrieval-Augmented Generation (RAG)**: Chunks, embeds (via SentenceTransformers), and indexes PDF/TXT/MD documentation inside a local FAISS database, grounding Gemini LLM responses with relevant facts.
- **Dynamic Connection Management**: The frontend polls the backend `/health` endpoint and renders visual connection states (`Backend Connected` vs `Backend Disconnected`) in real-time.
- **Persistent Conversation Memory**: Message log history is stored per conversation thread in MongoDB, surviving browser reloads and backend restarts.
- **Support Ticket CRUD**: Fully-featured ticket creation, update, listing, and deletion persist dynamically.

---

## 🏗️ Architecture

The system decouples interfaces and data layers to satisfy Clean Architecture constraints:

```
                          +------------------------+
                          |   Next.js Frontend     |
                          | (React/TS/TailwindCSS) |
                          +-----------+------------+
                                      |
                                      | HTTP Requests (Axios Client)
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
                          | (tickets.py / kb.py)   |  | (agents, RAG, FAISS)   |
                          +-----------+------------+  +--------+---------------+
                                      |                        |
                                      v                        v
                          +-----------+------------+  +--------+---------------+
                          |    Business Services   |  |   Database Adapter     |
                          | (Ticket / Chat logic)  |  |  (MongoDB / Fallback)  |
                          +------------------------+  +------------------------+
```

1. **Frontend App**: Client-side single page portal communicating with backend APIs using Axios handlers.
2. **API Endpoint Handlers**: Validates request parameters and coordinates payloads using Pydantic schemas.
3. **Domain Business Services**: Orchestrates ticket processing and document keyword matching.
4. **AI Packages**: Heuristic intent classification, SentenceTransformer vector embeddings, FAISS indices, and Gemini LLM.
5. **Database Layer**: MongoDB connection adapter with local file-backed JSON database fallback for offline execution.

---

## 📂 Folder Structure

```text
customer-support-ai/
│
├── frontend/                     # Next.js client
│   ├── public/                   # Static assets & icons
│   ├── src/
│   │   ├── app/                  # App Router pages & custom layout configurations
│   │   ├── components/
│   │   │   └── chat/             # MessageBubble, ChatInput, ChatWindow
│   │   ├── hooks/                # useChat state manager (local history cache)
│   │   └── services/             # Axios API base configuration
│   ├── .env.example              # Host URL variables config
│   ├── package.json
│   └── tsconfig.json
│
├── backend/                      # FastAPI server
│   ├── api/                      # Versioned endpoints (v1 chat, tickets, and kb routers)
│   ├── agents/                   # Billing, Tech, FAQ, Complaint, Product Agents & router
│   ├── rag/                      # Ingestion pipeline and PDF document parsers
│   ├── embeddings/               # Local SentenceTransformer embedding generator
│   ├── vectorstore/              # Local FAISS CPU vector index FlatIP adapter
│   ├── database/                 # MongoDB Atlas connection pooling & local fallback definitions
│   ├── models/                   # Pydantic schemas validating API inputs/outputs
│   ├── services/                 # Business logic and LLM connector wrapper
│   ├── config/                   # System configurations and env loader settings
│   ├── tests/                    # Pytest automated integration test suite
│   ├── utils/                    # Global log setups and app exception handlers
│   ├── .env.example              # Port parameters and CORS origins settings
│   ├── requirements.txt          # Python dependencies
│   └── main.py                   # Bootstrapping entrypoint
│
├── knowledge_base/               # Support articles source files & mock local database JSON
├── docs/                         # Structural designs and system diagrams
└── README.md                     # Project manual
```

---

## 🛠️ Technology Stack

- **Frontend**:
  - Next.js (App Router)
  - React 19
  - TypeScript
  - Tailwind CSS (v4)
  - Axios (API connection client)
- **Backend**:
  - FastAPI
  - Python 3.11+
  - Uvicorn (ASGI web server)
  - PyMongo (MongoDB connection driver)
  - FAISS CPU (similarity vector index)
  - Sentence-Transformers (local embedding generation)
  - Google GenAI (Gemini API SDK client)
- **Testing**:
  - Pytest & HTTPX (for backend integrations)

---

## ⚙️ Installation & Configuration

### Prerequisites
- Node.js (v18.0.0 or later)
- Python (v3.11 or later)
- npm or yarn

### Environment Setup

#### Backend Configuration
Copy the environment template:
```bash
cd backend
cp .env.example .env
```
Fill out the variables in `backend/.env` using your credentials:
```env
# Gemini API Key (get from Google AI Studio)
GEMINI_API_KEY="your-gemini-api-key"
GEMINI_MODEL_NAME="gemini-2.5-flash"

# MongoDB Database (Atlas connection URI and Database name)
MONGODB_URI="mongodb+srv://user:pass@cluster.mongodb.net/?appName=customer-support-ai"
MONGODB_DB_NAME="customer_support_ai"
```

#### Frontend Configuration
Copy the environment template:
```bash
cd ../frontend
cp .env.example .env.local
```
Fill out the variables in `frontend/.env.local`:
```env
NEXT_PUBLIC_API_URL="http://localhost:8000"
```

---

## 🚀 Running the Project

### Starting Frontend
1. Install dependencies:
   ```bash
   cd frontend
   npm install
   ```
2. Start Next.js Turbopack dev server:
   ```bash
   npm run dev
   ```
   Open [http://localhost:3000](http://localhost:3000) to view the client console dashboard.

### Starting Backend
1. Install Python packages:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```
2. Run development server:
   ```bash
   uvicorn main:app --reload --port 8000
   ```
   Interactive Swagger documentation is available at [http://localhost:8000/docs](http://localhost:8000/docs).

### Running Tests
Execute the automated integration pytest suite:
```bash
cd backend
python -m pytest tests/ -v
```

---

## 🔍 Observability, Request Tracing, & Resilience

- **Request ID Tracking**: Every API request is correlated using a unique `request_id` passed via the `X-Request-ID` HTTP header and isolated per-request via Python context variables.
- **Structured Logging**: Clean, JSON-formatted structured logging with automatic regex-based credential redaction (`MONGODB_URI`, `GEMINI_API_KEY` placeholders).
- **Latency Instrumentation**: Detailed pipeline stage measurements (`intent_detection`, `history_loading`, `rag_retrieval`, `llm_generation`, `history_persistence`) logged to track bottleneck and execution flow performance.
- **Bounded Failover & Retries**: Automatic exponential backoff retries with jitter for transient dependencies (Gemini rate-limit 429 errors) and isolated FAISS/MongoDB fallback bounds to guarantee graceful service degradation.

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

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
