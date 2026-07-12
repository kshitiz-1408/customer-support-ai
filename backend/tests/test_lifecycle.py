import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from main import app
from database import database
from embeddings import embedding_model
from rag.rag_pipeline import vector_store

client = TestClient(app)


def test_liveness():
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert "timestamp" in response.json()


def test_readiness_success():
    # Mock MongoDB admin command ping to succeed
    mock_client = MagicMock()
    mock_client.admin.command.return_value = {"ok": 1.0}
    
    with patch("main.connect_db") as mock_connect, \
         patch("main.close_db") as mock_close, \
         patch("database.database.db_client", mock_client), \
         patch("database.database.db_connected", True), \
         patch("rag.rag_pipeline.vector_store", MagicMock()) as mock_vs, \
         patch("embeddings.embedding_model.get_model", return_value=MagicMock()):
         
        mock_vs._index.ntotal = 42
        # Run inside context manager to ensure state timings are available
        with TestClient(app) as local_client:
            response = local_client.get("/health/ready")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ready"
            assert data["database"] == "connected"
            assert data["faiss_vectors"] == 42
            assert "startup_timings" in data


def test_readiness_mongo_failure():
    # Mock MongoDB ping to raise exception (unreachable)
    mock_client = MagicMock()
    mock_client.admin.command.side_effect = Exception("Connection Refused")
    
    with patch("main.connect_db") as mock_connect, \
         patch("main.close_db") as mock_close, \
         patch("database.database.db_client", mock_client), \
         patch("database.database.db_connected", True), \
         patch("rag.rag_pipeline.vector_store", MagicMock()), \
         patch("embeddings.embedding_model.get_model", return_value=MagicMock()):
         
        with TestClient(app) as local_client:
            response = local_client.get("/health/ready")
            assert response.status_code == 503
            data = response.json()["detail"]
            assert data["status"] == "unhealthy"
            assert data["database"] == "unavailable"
            assert "mongodb" in data["errors"]


def test_readiness_faiss_failure():
    mock_client = MagicMock()
    mock_client.admin.command.return_value = {"ok": 1}
    
    # Mock vector_store to be None (not loaded)
    with patch("main.connect_db") as mock_connect, \
         patch("main.close_db") as mock_close, \
         patch("database.database.db_client", mock_client), \
         patch("database.database.db_connected", True), \
         patch("rag.rag_pipeline.vector_store", None), \
         patch("embeddings.embedding_model.get_model", return_value=MagicMock()):
         
        with TestClient(app) as local_client:
            response = local_client.get("/health/ready")
            assert response.status_code == 503
            data = response.json()["detail"]
            assert data["status"] == "unhealthy"
            assert "faiss" in data["errors"]


def test_singleton_resource_reuse():
    # Verify client & model reuse patterns
    from services.llm_service import GeminiLLMService
    
    # 1. MongoDB client reuse check
    assert database.db_client is database.db_client
    
    # 2. Embedding model cache check
    model1 = embedding_model.get_model()
    model2 = embedding_model.get_model()
    assert model1 is model2
    
    # 3. Gemini SDK reuse check
    client1 = GeminiLLMService._client
    client2 = GeminiLLMService._client
    assert client1 is client2


def test_startup_timings_recorded():
    with patch("main.connect_db"), \
         patch("main.close_db"), \
         patch("main.initialize_rag_pipeline"), \
         patch("embeddings.embedding_model.get_model"):
        with TestClient(app) as local_client:
            assert hasattr(app.state, "startup_timings")
            timings = app.state.startup_timings
            assert "total_ms" in timings
            assert "mongo_init_ms" in timings
            assert "embedding_load_ms" in timings
            assert "rag_init_ms" in timings
            assert "gemini_init_ms" in timings
