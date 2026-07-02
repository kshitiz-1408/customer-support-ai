# System Architecture Design

This document details the architectural principles and folder structure for the Customer Support AI project.

## High-Level Overview

```
                   +------------------------+
                   |       Frontend         |
                   |  (Next.js / Tailwind)  |
                   +-----------+------------+
                               |
                               | HTTP Requests
                               v
                   +-----------+------------+
                   |    FastAPI Gateway     |
                   |  (CORS / Router / App) |
                   +-----------+------------+
                               |
                               v
                   +-----------+------------+
                   |     Service Layer      |
                   | (Business Logic Logic) |
                   +-----------+------------+
                               |
                               v
                   +-----------+------------+
                   |  In-Memory Storage DB  |
                   |  (Schemas / Models)    |
                   +------------------------+
```

## Clean Architecture Directory Separation

### 1. Frontend Layer (`frontend/`)
- **React / Next.js**: Component-based layout leveraging App Router.
- **Service Adaptors (`services/api.ts`)**: Custom Axios configs communicating with backend ports.
- **State Flow**: Fully interactive Client Side hooks.

### 2. API / Interface Layer (`backend/app/api/`)
- **Endpoints (`endpoints/*.py`)**: Handles FastAPI path operations, parses query parameters, and raises HTTP exceptions. Decoupled from service implementations.
- **Schemas (`schemas/*.py`)**: Standardizes input and output payloads using Pydantic validation.

### 3. Business / Service Layer (`backend/app/services/`)
- **Services (`*_service.py`)**: Intermediates CRUD queries and houses algorithmic scoring for knowledge bases. Fully decoupled from FastAPI endpoints.

### 4. Future Integrations
- **AI RAG Pipeline**: Placeholders for loaders indexing documents under the `knowledge_base/` directory and writing answers using language models.
- **Dataset fine-tuning**: Train model weights using sample chats under the `datasets/` directory.
