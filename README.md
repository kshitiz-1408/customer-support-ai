# Customer Support AI

Customer Support AI is a production-ready, clean-architecture application template designed to handle multi-agent ticketing workflows and Retrieval-Augmented Generation (RAG) tasks. 

This repository features a fully responsive, dark-mode-optimized Next.js frontend and a modular FastAPI backend, structured with designated packages to host future embeddings generation, vector storage, intent detection, and agent routing tasks.

---

## 📌 Project Overview

The portal serves as an interactive workplace for support agents and customers alike:
- **Intelligent Dashboard**: Displays live ticket statuses (Open, In Progress, Resolved) and knowledge base articles counts.
- **Support Chat Portal**: Allows users to chat with support agents. Currently configured to ping the backend health-check (`GET /health`) and display telemetry configurations.
- **Dynamic Connection Management**: The frontend polls the backend and renders visual indicator states (`Backend Connected` vs `Backend Disconnected`) in real-time.
- **RAG-Ready Skeletons**: Predefined placeholder packages structured to support PDF text parsing, semantic similarity embeddings, and agent routing logic out of the box.

---

## 🏗️ Architecture

The system decouples interfaces and data layers to satisfy Clean Architecture constraints:

```
                          +------------------------+
                          |   Next.js 15 Frontend  |
                          | (React/TS/TailwindCSS) |
                          +-----------+------------+
                                      |
                                      | HTTP Requests (Axios Client)
                                      v
                          +-----------+------------+
                          |    FastAPI Backend     |
                          | (main.py / CORS config) |
                          +-----------+------------+
                                      |
                                      +------------------------+
                                      |                        |
                                      v                        v
                          +-----------+------------+  +--------+---------------+
                          |    API Router v1       |  |  AI Pipeline Modules  |
                          | (tickets.py / kb.py)   |  | (agents, rag, embed)   |
                          +-----------+------------+  +------------------------+
                                      |
                                      v
                          +-----------+------------+
                          |      Services          |
                          | (In-Memory persist)    |
                          +------------------------+
```

1. **Frontend App**: Client-side single page portal communicating with backend APIs using pre-configured Axios handlers.
2. **API Endpoint Handlers**: Validates request parameters and coordinates payloads using Pydantic schemas.
3. **Domain Business Services**: Orchestrates ticket processing and document keyword matching.
4. **AI Packages**: Skeletons designed to route queries, calculate sentence vectors, and search indexes.

---

## 📂 Folder Structure

```text
customer-support-ai/
│
├── frontend/                     # Next.js 15 client
│   ├── public/                   # Static assets & icons
│   ├── src/
│   │   ├── app/                  # App Router pages and custom layout configurations
│   │   ├── components/
│   │   │   ├── chat/             # MessageBubble, TypingIndicator, ChatInput, ChatWindow
│   │   │   └── layout/           # Sidebar navigation and dynamic Navbar status checker
│   │   ├── hooks/                # useChat state manager
│   │   ├── services/             # Axios API base configuration
│   │   └── types/                # TypeScript interfaces
│   ├── .env.example              # Host URL variables config
│   ├── package.json
│   └── tsconfig.json
│
├── backend/                      # FastAPI Python 3.11 server
│   ├── api/                      # Versioned endpoints (v1 tickets and kb routers)
│   ├── agents/                   # Multi-agent modules (Billing, Tech, FAQ, intent classification)
│   ├── rag/                      # Ingestion pipeline and PDF document parsers
│   ├── embeddings/               # Local or managed sentence embedding generators
│   ├── vectorstore/              # Vector database indices adapters (Chroma/Qdrant)
│   ├── database/                 # SQLAlchemy connections and model schemas
│   ├── models/                   # Pydantic schemas validating API inputs/outputs
│   ├── services/                 # Business logic and search simulation handlers
│   ├── config/                   # System configurations and env loader settings
│   ├── middleware/               # Custom HTTP request filters
│   ├── utils/                    # Global log setups and app exception handlers
│   ├── .env.example              # Port parameters and CORS origins arrays settings
│   ├── requirements.txt          # Python dependencies
│   └── main.py                   # Bootstrapping entrypoint
│
├── knowledge_base/               # Markdown documentation source files for AI context retrieval
├── docs/                         # Structural designs and system diagrams
├── datasets/                     # Customer chat histories for model fine-tuning
└── README.md                     # Project manual
```

---

## 🛠️ Technology Stack

- **Frontend**:
  - Next.js (latest App Router)
  - React 19
  - TypeScript
  - Tailwind CSS (v4)
  - Axios (API connection client)
  - Lucide Icons (premium iconography)
- **Backend**:
  - FastAPI
  - Python 3.11+
  - Uvicorn (ASGI web server)
  - Pydantic Settings (env validation)
  - SQLAlchemy (relational database ORM)
- **Testing**:
  - Pytest & HTTPX (for backend integrations)

---

## ⚙️ Installation

### Prerequisites
- Node.js (v18.0.0 or later)
- Python (v3.11 or later)
- npm or yarn

---

## 🚀 Running Frontend

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install package dependencies:
   ```bash
   npm install
   ```
3. Copy environment configuration:
   ```bash
   cp .env.example .env.local
   ```
4. Start the local Next.js development server:
   ```bash
   npm run dev
   ```
   Open [http://localhost:3000](http://localhost:3000) to view the portal.

---

## 🐍 Running Backend

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Set up and activate a Python virtual environment:
   ```bash
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```
3. Install package dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy environment configuration:
   ```bash
   cp .env.example .env
   ```
5. Start the FastAPI development server:
   ```bash
   uvicorn main:app --reload --port 8000
   ```
   Swagger API documentation is served at [http://localhost:8000/docs](http://localhost:8000/docs).

---

## 🗺️ Future Roadmap

- [ ] **Embedding Calculations**: Implement local PyTorch embedding services inside `embeddings/embedding_model.py`.
- [ ] **Vector Database Indexing**: Connect ChromaDB/Qdrant adapters inside `vectorstore/vector_store.py` to persist support documents.
- [ ] **Intent Classifier**: Feed classification LLM queries inside `agents/intent_detector.py` to tag incoming user tickets.
- [ ] **Multi-Agent Routing**: Code transition loops in `agents/router.py` to delegate intents to Billing, FAQ, or Technical agents.
- [ ] **Relational Database Migration**: Connect PostgreSQL instances using SQLAlchemy models inside the `database/` package.

---

## 🚢 Deployment Plan

- **Backend (FastAPI)**:
  - Containerize using Docker (`Dockerfile` stubs).
  - Deploy to AWS ECS or GCP Cloud Run for serverless execution.
  - Set up an RDS PostgreSQL instance for relational persistence.
- **Frontend (Next.js)**:
  - Deploy static assets or Server-Side Rendered (SSR) routes directly on Vercel or Netlify.
  - Place behind Cloudflare CDN for performance optimization.

---

## 🤝 Contributing

We welcome contributions to help expand agent features!
1. Fork this repository.
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Commit your changes: `git commit -m 'Add new agent capability'`
4. Push to the branch: `git push origin feature/your-feature-name`
5. Create a Pull Request.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
