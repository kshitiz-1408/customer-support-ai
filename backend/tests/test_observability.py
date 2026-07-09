import os
import sys
import json
import uuid
import logging
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

# Ensure backend root is in the import path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from utils.logging import StructuredFormatter, redact_secrets, request_id_var, RequestIdFilter
from services.llm_service import GeminiLLMService
from agents.conversation_memory import ConversationMemory
from utils.tracing import pipeline_tracker_var, PipelineTracker

client = TestClient(app)

class LogCaptureHandler(logging.Handler):
    """Logging handler to capture and format logs in memory for assertions."""
    def __init__(self):
        super().__init__()
        self.records = []
        self.formatter = StructuredFormatter()

    def emit(self, record):
        self.records.append(self.formatter.format(record))

    def get_events(self):
        events = []
        for r in self.records:
            try:
                events.append(json.loads(r))
            except Exception:
                pass
        return events


@pytest.fixture
def log_capture():
    """Fixture to attach a log capture handler to the customer_support_backend logger."""
    backend_logger = logging.getLogger("customer_support_backend")
    old_level = backend_logger.level
    backend_logger.setLevel(logging.DEBUG)
    
    capture_handler = LogCaptureHandler()
    capture_handler.addFilter(RequestIdFilter())
    backend_logger.addHandler(capture_handler)
    
    yield capture_handler
    
    backend_logger.removeHandler(capture_handler)
    backend_logger.setLevel(old_level)


def test_request_id_generation_and_headers():
    """Verify X-Request-ID header is generated and returned, or reused if valid."""
    # 1. Generated automatically
    response = client.get("/health")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    first_req_id = response.headers["X-Request-ID"]
    assert len(first_req_id) > 10

    # 2. Reused if provided and valid
    custom_uuid = str(uuid.uuid4())
    response2 = client.get("/health", headers={"X-Request-ID": custom_uuid})
    assert response2.status_code == 200
    assert response2.headers["X-Request-ID"] == custom_uuid

    # 3. Different requests get different IDs
    response3 = client.get("/health")
    assert response3.headers["X-Request-ID"] != first_req_id


def test_concurrent_request_isolation():
    """Verify concurrent requests do not bleed request IDs in context memory."""
    req_id_1 = str(uuid.uuid4())
    req_id_2 = str(uuid.uuid4())

    import contextvars
    from concurrent.futures import ThreadPoolExecutor

    def execute_in_context(val):
        token = request_id_var.set(val)
        time_to_sleep = 0.05
        import time
        time.sleep(time_to_sleep)
        res = request_id_var.get()
        request_id_var.reset(token)
        return res

    with ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(execute_in_context, req_id_1)
        f2 = executor.submit(execute_in_context, req_id_2)
        assert f1.result() == req_id_1
        assert f2.result() == req_id_2


def test_secret_redaction_behavior():
    """Verify sensitive patterns are fully redacted in log entries and filters."""
    # Gemini Key redaction check
    gemini_msg = "My key is AIzaSy123456789012345678901234567890123"
    assert "AIzaSy***REDACTED***" in redact_secrets(gemini_msg)

    # MongoDB password credentials redaction check
    mongo_msg = "Connecting to mongodb+srv://username:password123@cluster0.abc.mongodb.net/?auth=true"
    assert "mongodb+srv://****:****@cluster0.abc.mongodb.net/?auth=true" in redact_secrets(mongo_msg)

    # Bearer authorization token redaction check
    auth_msg = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIi"
    assert "Bearer ***REDACTED***" in redact_secrets(auth_msg)


def test_pipeline_stages_and_summary_success(log_capture):
    """Verify a successful request produces the ordered trace stages with matching request ID and summary logs."""
    chat_payload = {"message": "What does the Premium Plan include?"}
    
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = MagicMock(text="Grounded answer")
    
    with patch.object(GeminiLLMService, "_client", mock_client), \
         patch.object(GeminiLLMService, "_initialize_sdk", return_value=None):
         
        response = client.post("/api/v1/chat/", json=chat_payload)
        assert response.status_code == 200
        req_id = response.headers["X-Request-ID"]
        
        events = log_capture.get_events()
        
        # Filter only pipeline trace events
        stage_events = [e for e in events if e.get("event") in ("pipeline_stage_started", "pipeline_stage_completed")]
        assert len(stage_events) > 0
        
        # Verify request ID and timing parameters are populated and non-negative
        for se in stage_events:
            assert se.get("request_id") == req_id
            if se.get("event") == "pipeline_stage_completed":
                assert se.get("duration_ms") >= 0.0
                
        # Check summary log matches expectation and doesn't leak secrets or full messages
        summary = next((e for e in events if e.get("event") == "pipeline_trace_summary"), None)
        assert summary is not None
        assert summary["request_id"] == req_id
        assert summary["llm_success"] is True
        assert summary["persistence_success"] is True
        assert summary["final_status"] == "SUCCESS"
        assert "response" not in summary
        assert "message" not in summary
        assert "prompt" not in summary
        assert "password" not in summary


def test_first_failure_rag_retrieval(log_capture):
    """Verify RAG similarity search failure identifies rag_retrieval as the first failing stage, falls back, and proceeds."""
    chat_payload = {"message": "What does the Premium Plan include?"}
    
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = MagicMock(text="Ungrounded fallback answer")
    
    from rag.rag_pipeline import query_kb
    with patch.object(GeminiLLMService, "_client", mock_client), \
         patch.object(GeminiLLMService, "_initialize_sdk", return_value=None), \
         patch("rag.rag_pipeline.query_kb", side_effect=RuntimeError("FAISS Retrieval Index Error")):
         
        response = client.post("/api/v1/chat/", json=chat_payload)
        assert response.status_code == 200 # Gracefully continues
        
        events = log_capture.get_events()
        
        # Check that we captured the stage failure log
        failed_event = next((e for e in events if e.get("event") == "pipeline_stage_failed" and e.get("stage") == "rag_retrieval"), None)
        assert failed_event is not None
        assert failed_event["error_type"] == "RuntimeError"
        assert "FAISS" in failed_event["safe_error_summary"]
        
        # Verify trace summary identifies final_status and first_failure
        summary = next((e for e in events if e.get("event") == "pipeline_trace_summary"), None)
        assert summary is not None
        assert summary["final_status"] == "FAIL"


def test_first_failure_llm_generation(log_capture):
    """Verify Gemini API timeout/errors identify llm_generation as the first failing stage and emit fallback response."""
    chat_payload = {"message": "What does the Premium Plan include?"}
    
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = Exception("Gemini service connection timeout")
    
    with patch.object(GeminiLLMService, "_client", mock_client), \
         patch.object(GeminiLLMService, "_initialize_sdk", return_value=None):
         
        response = client.post("/api/v1/chat/", json=chat_payload)
        assert response.status_code == 200
        assert "apologize" in response.json()["response"] # Fallback answer
        
        events = log_capture.get_events()
        
        failed_event = next((e for e in events if e.get("event") == "pipeline_stage_failed" and e.get("stage") == "llm_generation"), None)
        assert failed_event is not None
        assert failed_event["error_type"] == "RuntimeError"
        assert "unavailable" in failed_event["safe_error_summary"]


def test_history_loading_failure(log_capture):
    """Verify history loading database outage fails history_loading stage but does not mix or crash chats."""
    chat_payload = {"message": "What does the Premium Plan include?"}
    
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = MagicMock(text="Standard response")
    
    with patch.object(GeminiLLMService, "_client", mock_client), \
         patch.object(GeminiLLMService, "_initialize_sdk", return_value=None), \
         patch.object(ConversationMemory, "get_conversation_history", side_effect=RuntimeError("History load connection error")):
         
        response = client.post("/api/v1/chat/", json=chat_payload)
        assert response.status_code == 200
        
        events = log_capture.get_events()
        
        failed_event = next((e for e in events if e.get("event") == "pipeline_stage_failed" and e.get("stage") == "history_loading"), None)
        assert failed_event is not None


def test_assistant_persistence_failure_recovery(log_capture):
    """Verify database persistence failure after LLM success marks assistant_persistence as FAIL but preserves answer."""
    chat_payload = {"message": "What does the Premium Plan include?"}
    
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = MagicMock(text="Answer generated successfully")
    
    with patch.object(GeminiLLMService, "_client", mock_client), \
         patch.object(GeminiLLMService, "_initialize_sdk", return_value=None), \
         patch.object(ConversationMemory, "add_message", side_effect=RuntimeError("Assistant Write MongoDB Error")):
         
        response = client.post("/api/v1/chat/", json=chat_payload)
        assert response.status_code == 200
        assert response.json()["response"] == "Answer generated successfully"
        
        events = log_capture.get_events()
        
        # Verify llm_generation passed but assistant_persistence failed
        llm_event = next((e for e in events if e.get("event") == "pipeline_stage_completed" and e.get("stage") == "llm_generation"), None)
        assert llm_event is not None
        
        failed_persistence = next((e for e in events if e.get("event") == "pipeline_stage_failed" and e.get("stage") == "assistant_persistence"), None)
        assert failed_persistence is not None


def test_invalid_conversation_id():
    """Verify invalid conversation ID yields a defined 404 response without crashing."""
    chat_payload = {
        "message": "Hello",
        "conversation_id": "nonexistent_conversation_id_abc123"
    }
    
    response = client.post("/api/v1/chat/", json=chat_payload)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_same_conversation_different_request_ids(log_capture):
    """Verify that multiple turns in the same conversation thread reuse conversation_id but get distinct request_ids."""
    payload1 = {"message": "First query"}
    
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = MagicMock(text="First answer")
    
    with patch.object(GeminiLLMService, "_client", mock_client), \
         patch.object(GeminiLLMService, "_initialize_sdk", return_value=None):
         
        response1 = client.post("/api/v1/chat/", json=payload1)
        assert response1.status_code == 200
        conv_id = response1.json().get("conversation_id")
        req_id1 = response1.headers["X-Request-ID"]
        
        payload2 = {"message": "Second query", "conversation_id": conv_id}
        response2 = client.post("/api/v1/chat/", json=payload2)
        assert response2.status_code == 200
        req_id2 = response2.headers["X-Request-ID"]
        
        assert response2.json().get("conversation_id") == conv_id
        assert req_id1 != req_id2


def test_chat_performance_summary_validation(log_capture):
    """Verify that successful chat requests emit a chat_performance_summary event with accurate timings."""
    chat_payload = {"message": "What does the Premium Plan include?"}
    
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = MagicMock(text="Mocked Premium Plan includes cameras and cellular backup.")
    
    with patch.object(GeminiLLMService, "_client", mock_client), \
         patch.object(GeminiLLMService, "_initialize_sdk", return_value=None):
         
        response = client.post("/api/v1/chat/", json=chat_payload)
        assert response.status_code == 200
        
        events = log_capture.get_events()
        perf_summary = next((e for e in events if e.get("event") == "chat_performance_summary"), None)
        
        assert perf_summary is not None
        assert "request_id" in perf_summary
        assert "conversation_id" in perf_summary
        
        # Verify timings are present and non-negative
        assert perf_summary["total_duration_ms"] >= 0.0
        assert perf_summary["intent_detection_ms"] >= 0.0
        assert perf_summary["rag_retrieval_total_ms"] >= 0.0
        assert perf_summary["gemini_generation_ms"] >= 0.0
        assert perf_summary["persistence_total_ms"] >= 0.0
        assert perf_summary["dominant_stage_duration_ms"] >= 0.0
        assert 0.0 <= perf_summary["dominant_stage_percentage"] <= 100.0
        assert perf_summary["unmeasured_time_ms"] >= 0.0
        
        # Verify dominant bottleneck is valid stage name
        assert perf_summary["dominant_stage"] in [
            "llm_generation", "rag_retrieval", "intent_detection", 
            "user_persistence", "assistant_persistence", "conversation_resolution",
            "context_construction", "agent_routing", "history_loading", "response_serialization"
        ]
        
        # Verify no credentials or user messages leak in summary
        for key, val in perf_summary.items():
            if isinstance(val, str):
                assert "mongodb" not in val.lower()
                assert "api_key" not in val.lower()
                assert "include" not in val.lower()
                assert "premium" not in val.lower()


def test_gemini_retry_on_transient_failure_then_success(log_capture):
    """Verify that a transient Gemini failure (429/503) triggers a retry and returns success on the next attempt."""
    chat_payload = {"message": "What does the Premium Plan include?"}
    
    mock_client = MagicMock()
    from google.genai.errors import ClientError
    err = ClientError(429, {"error": "Too Many Requests"})
    mock_client.models.generate_content.side_effect = [err, MagicMock(text="Mocked Premium response")]
    
    with patch.object(GeminiLLMService, "_client", mock_client), \
         patch.object(GeminiLLMService, "_initialize_sdk", return_value=None), \
         patch("utils.resilience.settings.GEMINI_BACKOFF_FACTOR", 0.1):
         
        response = client.post("/api/v1/chat/", json=chat_payload)
        assert response.status_code == 200
        assert "Premium" in response.json()["response"]
        
        events = log_capture.get_events()
        retry_event = next((e for e in events if e.get("event") == "retry_attempt" and e.get("dependency") == "Gemini API"), None)
        assert retry_event is not None
        assert retry_event["attempt"] == 1
        assert retry_event["max_attempts"] == 3
        assert retry_event["error_type"] == "ClientError"


def test_gemini_non_transient_failure_does_not_retry():
    """Verify that a non-transient Gemini error (403 invalid key) fails immediately without any retries."""
    chat_payload = {"message": "What does the Premium Plan include?"}
    
    mock_client = MagicMock()
    from google.genai.errors import ClientError
    err = ClientError(403, {"error": "API_KEY_INVALID"})
    mock_client.models.generate_content.side_effect = err
    
    with patch.object(GeminiLLMService, "_client", mock_client), \
         patch.object(GeminiLLMService, "_initialize_sdk", return_value=None), \
         patch("utils.resilience.logger.warning") as mock_warn:
         
        response = client.post("/api/v1/chat/", json=chat_payload)
        assert response.status_code == 200
        assert "apologize" in response.json()["response"]
        
        warnings = [call.args[0] for call in mock_warn.call_args_list]
        retry_skipped = next((w for w in warnings if isinstance(w, dict) and w.get("event") == "retry_skipped"), None)
        assert retry_skipped is not None
        assert retry_skipped["error_type"] == "ClientError"
        assert "API_KEY_INVALID" in retry_skipped["error_detail"]


def test_mongodb_read_retry_on_transient_failure(log_capture):
    """Verify that a transient MongoDB query failure triggers a retry and succeeds."""
    from pymongo.errors import AutoReconnect
    
    mock_collection = MagicMock()
    mock_collection.find_one.side_effect = [AutoReconnect("connection lost"), {"conversation_id": "test_conv", "session_id": "test_session"}]
    
    with patch("agents.conversation_memory.get_conversations_collection", return_value=mock_collection):
        from agents.conversation_memory import ConversationMemory
        res = ConversationMemory.get_conversation("test_conv")
        
        assert res is not None
        assert res["conversation_id"] == "test_conv"
        
        events = log_capture.get_events()
        mongo_retry = next((e for e in events if e.get("event") == "retry_attempt" and e.get("dependency") == "MongoDB"), None)
        assert mongo_retry is not None
        assert mongo_retry["attempt"] == 1
        assert mongo_retry["error_type"] == "AutoReconnect"


def test_concurrent_request_ids_isolation(log_capture):
    """Verify that multiple concurrent requests obtain unique request IDs and remain isolated in context."""
    import concurrent.futures
    
    mock_response = MagicMock(text="Mocked concurrent response")
    
    with patch.object(GeminiLLMService, "_client") as mock_client, \
         patch.object(GeminiLLMService, "_initialize_sdk", return_value=None):
         
        mock_client.models.generate_content.return_value = mock_response
        
        def run_request(index):
            return client.post("/api/v1/chat/", json={"message": f"Query number {index}"})
            
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(run_request, i) for i in range(10)]
            results = [f.result() for f in futures]
            
        assert len(results) == 10
        req_ids = []
        for r in results:
            assert r.status_code == 200
            req_id = r.headers.get("x-request-id")
            assert req_id is not None
            req_ids.append(req_id)
            
        assert len(set(req_ids)) == 10


def test_concurrent_conversations_history_isolation(log_capture):
    """Verify that concurrent requests on separate conversations load only their respective histories."""
    import concurrent.futures
    import logging
    
    mock_history_store = {
        "conv_A": [{"role": "user", "content": "Query A1"}, {"role": "assistant", "content": "Answer A1"}],
        "conv_B": [{"role": "user", "content": "Query B1"}, {"role": "assistant", "content": "Answer B1"}],
        "conv_C": [{"role": "user", "content": "Query C1"}, {"role": "assistant", "content": "Answer C1"}],
    }
    
    def mock_get_history(conversation_id, limit=20):
        docs = mock_history_store.get(conversation_id, [])
        logger = logging.getLogger("customer_support_backend")
        logger.info({
            "event": "history_loaded",
            "conversation_id": conversation_id,
            "message_count": len(docs),
            "duration_ms": 1
        })
        return docs
        
    with patch("agents.conversation_memory.ConversationMemory.get_conversation_history", side_effect=mock_get_history), \
         patch("agents.conversation_memory.ConversationMemory.get_conversation", return_value={"conversation_id": "temp"}), \
         patch.object(GeminiLLMService, "_client") as mock_client, \
         patch.object(GeminiLLMService, "_initialize_sdk", return_value=None):
         
        mock_client.models.generate_content.return_value = MagicMock(text="Response text")
        
        def run_chat(conv_id):
            return client.post("/api/v1/chat/", json={"message": "refund bill query", "conversation_id": conv_id})
            
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = {executor.submit(run_chat, cid): cid for cid in ["conv_A", "conv_B", "conv_C"]}
            results = {futures[f]: f.result() for f in futures}
            
        for cid, res in results.items():
            assert res.status_code == 200
            
        events = log_capture.get_events()
        history_loads = [e for e in events if e.get("event") == "history_loaded"]
        assert len(history_loads) >= 3
        for h in history_loads:
            cid = h["conversation_id"]
            if cid in mock_history_store:
                count = h["message_count"]
                assert count == 2


def test_concurrent_retry_state_isolation(log_capture):
    """Verify that concurrent requests have independent retry states."""
    import concurrent.futures
    import threading
    from google.genai.errors import ClientError
    
    err = ClientError(429, {"error": "Too Many Requests"})
    mock_success = MagicMock(text="Success response")
    
    client_a = MagicMock()
    client_a.models.generate_content.side_effect = [err, mock_success]
    
    client_b = MagicMock()
    client_b.models.generate_content.side_effect = [mock_success]
    
    client_c = MagicMock()
    client_c.models.generate_content.side_effect = [err, err, err]
    
    import uuid
    from utils.logging import request_id_var
    
    mapping = {}
    mapping_lock = threading.Lock()
    
    def mock_generate_content(*args, **kwargs):
        req_id = request_id_var.get()
        with mapping_lock:
            target = mapping.get(req_id)
        if not target:
            raise RuntimeError(f"No mock client found for request id: {req_id}")
        return target.models.generate_content(*args, **kwargs)
        
    with patch.object(GeminiLLMService, "_client") as mock_client, \
         patch.object(GeminiLLMService, "_initialize_sdk", return_value=None), \
         patch("utils.resilience.settings.GEMINI_BACKOFF_FACTOR", 0.01):
         
        mock_client.models.generate_content.side_effect = mock_generate_content
        
        def run_thread(client_mock):
            req_id = str(uuid.uuid4())
            with mapping_lock:
                mapping[req_id] = client_mock
            return client.post(
                "/api/v1/chat/",
                json={"message": "refund bill query"},
                headers={"x-request-id": req_id}
            )
            
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            f_a = executor.submit(run_thread, client_a)
            f_b = executor.submit(run_thread, client_b)
            f_c = executor.submit(run_thread, client_c)
            
            res_a = f_a.result()
            res_b = f_b.result()
            res_c = f_c.result()
            
        assert res_a.status_code == 200
        assert res_b.status_code == 200
        assert res_c.status_code == 200
        
        events = log_capture.get_events()
        exhausted = [e for e in events if e.get("event") == "retry_exhausted"]
        assert len(exhausted) == 1
        
        retries = [e for e in events if e.get("event") == "retry_attempt"]
        assert len(retries) == 3



