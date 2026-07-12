import os
import json
import pytest
from unittest.mock import patch, MagicMock
from database import database
from config.config import settings
from vectorstore.vector_store import LocalVectorStore
from main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_rag_cache_folder_configuration():
    # Verify environment variables for caching are set upon Settings load
    assert "HF_HOME" in os.environ
    assert "SENTENCE_TRANSFORMERS_HOME" in os.environ
    assert os.environ["HF_HOME"].endswith(settings.HF_HOME.replace("/", os.sep))


def test_rag_missing_index_fallback():
    # Test that LocalVectorStore initializes an empty index when persistent files are missing
    with patch("os.path.exists", return_value=False):
        store = LocalVectorStore(dimension=384)
        assert store._index.ntotal == 0
        assert len(store._metadata_store) == 0


def test_rag_corrupt_index_backup(tmp_path):
    # Test backup of corrupt index files during load_from_disk
    index_file = tmp_path / "faiss_index.bin"
    metadata_file = tmp_path / "faiss_metadata.json"
    
    # Write invalid data to simulate corruption
    index_file.write_text("corrupted index content")
    metadata_file.write_text("{invalid json corrupt")
    
    store = LocalVectorStore(dimension=384)
    # Reconfigure paths to tmp_path files
    store.index_path = str(index_file)
    store.metadata_path = str(metadata_file)
    
    # Try loading the corrupt files
    store.load_from_disk()
    
    # Assert fallback to empty initialized index
    assert store._index.ntotal == 0
    assert len(store._metadata_store) == 0
    
    # Assert corrupt files were backed up with .corrupt extension and original removed
    assert not os.path.exists(str(index_file))
    assert not os.path.exists(str(metadata_file))
    assert os.path.exists(str(index_file) + ".corrupt")
    assert os.path.exists(str(metadata_file) + ".corrupt")


def test_rag_rebuild_endpoint():
    # Test explicitly triggering rebuilding via API endpoint
    with patch("api.v1.endpoints.kb.initialize_rag_pipeline") as mock_rebuild, \
         patch("api.v1.endpoints.kb.vector_store") as mock_store:
         
        mock_store._index.ntotal = 15
        
        response = client.post("/api/v1/kb/rebuild")
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        assert response.json()["indexed_chunks"] == 15
        mock_rebuild.assert_called_once_with(force_rebuild=True)
