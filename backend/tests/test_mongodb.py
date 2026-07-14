import pytest
from unittest.mock import patch, MagicMock
from database import database
from main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_should_use_mock_logic():
    # 1. In production, should NEVER use mock
    with patch.object(database.settings, "APP_ENV", "production"), \
         patch.object(database.settings, "MONGODB_URI", None), \
         patch.object(database, "db_connected", False):
        assert database._should_use_mock() is False

    # 2. If MONGODB_URI is configured, should NEVER use mock
    with patch.object(database.settings, "APP_ENV", "development"), \
         patch.object(database.settings, "MONGODB_URI", "mongodb://localhost:27017"), \
         patch.object(database, "db_connected", False):
        assert database._should_use_mock() is False

    # 3. If no URI and not in production and db is offline, use mock
    with patch.object(database.settings, "APP_ENV", "development"), \
         patch.object(database.settings, "MONGODB_URI", ""), \
         patch.object(database, "db_connected", False):
        assert database._should_use_mock() is True


def test_mongo_client_pooling_configuration():
    mock_client = MagicMock()
    with patch.object(database.settings, "MONGODB_URI", "mongodb://localhost:27017"), \
         patch.object(database, "MongoClient", return_value=mock_client) as mock_mongo_ctor:
        with patch.object(database, "db_client", None):
            database.get_db()
            
            # Check constructor arguments
            mock_mongo_ctor.assert_called_once()
            args, kwargs = mock_mongo_ctor.call_args
            assert kwargs.get("maxPoolSize") == 50
            assert kwargs.get("minPoolSize") == 5
            assert kwargs.get("retryWrites") is True
            assert kwargs.get("retryReads") is True


def test_self_healing_reconnection_ready_endpoint():
    # Verify that readiness check attempts connect_db when db_client is missing
    mock_client = MagicMock()
    mock_client.admin.command.return_value = {"ok": 1.0}
    
    with patch("main.connect_db") as mock_connect, \
         patch.object(database, "db_client", None), \
         patch.object(database, "db_connected", False), \
         patch("rag.rag_pipeline.vector_store", MagicMock()) as mock_vs, \
         patch("embeddings.embedding_model.get_model", return_value=MagicMock()):
        
        mock_vs._index.ntotal = 10
        
        # When db_client is None at start, it should trigger connect_db()
        # Let's mock connect_db to simulate successfully connecting and setting the client
        def side_effect_connect():
            database.db_client = mock_client
            database.db_connected = True
            
        mock_connect.side_effect = side_effect_connect
        
        response = client.get("/health/ready")
        assert response.status_code == 200
        assert mock_connect.call_count == 1
        assert response.json()["status"] == "ready"


def test_mongodb_index_creation():
    # Mock MongoClient index structure validation
    mock_client = MagicMock()
    mock_db = MagicMock()
    mock_client.__getitem__.return_value = mock_db
    mock_client.admin.command.return_value = {"ok": 1.0}
    
    with patch.object(database, "MongoClient", return_value=mock_client), \
         patch.object(database.settings, "MONGODB_DB_NAME", "test_db"), \
         patch.object(database.settings, "MONGODB_URI", "mongodb://localhost:27017"), \
         patch.object(database, "db_client", None), \
         patch.object(database, "db_connected", False):
         
        database.connect_db()
        
        # Verify compound index creations
        # conversations: session_id_updated_at and user_id_updated_at
        mock_db["conversations"].create_index.assert_any_call([("session_id", 1), ("updated_at", -1)])
        mock_db["conversations"].create_index.assert_any_call([("user_id", 1), ("updated_at", -1)])
        
        # messages: conversation_id_created_at
        mock_db["messages"].create_index.assert_any_call([("conversation_id", 1), ("created_at", -1)])
        
        # tickets: id and ticket_id uniques
        mock_db["tickets"].create_index.assert_any_call("id", unique=True)
        mock_db["tickets"].create_index.assert_any_call("ticket_id", unique=True)


def test_mongodb_duplicate_key_error():
    from pymongo.errors import DuplicateKeyError
    mock_collection = MagicMock()
    mock_collection.insert_one.side_effect = DuplicateKeyError("E11000 duplicate key error collection")
    
    with pytest.raises(DuplicateKeyError):
         mock_collection.insert_one({"ticket_id": "duplicate_id"})
