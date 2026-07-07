import os
import sys
import unittest.mock
import pytest
from fastapi.testclient import TestClient

# Ensure backend root is in the import path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from services.llm_service import GeminiLLMService

client = TestClient(app)

# Helper to mock Gemini responses to prevent external 429 rate limit errors during test execution
def mock_generate_response(user_query: str, system_instruction: str = None, history: list = None, **kwargs) -> str:
    query_lower = user_query.lower()
    if "premium plan" in query_lower:
        return "The Premium Plan includes unlimited camera support, 60-day storage history, advanced AI detection rules, and cellular backup. It is priced at $19.99 per month or $199.99 when billed annually."
    elif "cost annually" in query_lower:
        return "The Premium Plan costs $199.99 when billed annually."
    elif "shipping" in query_lower:
        return "Standard Ground Shipping takes 3 to 5 business days for delivery."
    elif "refund" in query_lower:
        return "TechMart Electronics offers a complete refund on purchases returned within 45 days from the original purchase date."
    elif "login" in query_lower:
        return "I am sorry to hear you are having trouble logging in. Please reset your password."
    elif "terrible" in query_lower or "manager" in query_lower:
        return "For critical complaints or grievances, you may request a formal review by the Support Manager by writing directly to manager-support@techmart.com."
    return "Hello! I am your AI assistant. How can I help you today?"


@pytest.fixture(autouse=True)
def patch_gemini():
    """Automatically patch Gemini LLM service calls for all test cases."""
    with unittest.mock.patch.object(GeminiLLMService, "generate_response", side_effect=mock_generate_response):
        yield


def test_health():
    """Test API service status and health check validation."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "ok"


def test_kb_search():
    """Test retrieval of matching documents from the vector store."""
    response = client.get("/api/v1/kb/search?query=premium")
    assert response.status_code == 200
    results = response.json()
    assert isinstance(results, list)
    if len(results) > 0:
        # The kb/search route returns List[KBSearchResult] where each result is:
        # { "article": { "title": ..., "content": ... }, "score": ... }
        assert "article" in results[0]
        assert "content" in results[0]["article"]
        assert "title" in results[0]["article"]
        assert "category" in results[0]["article"]


def test_ticket_crud_workflow():
    """Verify full CRUD ticket pipeline including creation, retrieval, updates, and deletion."""
    # 1. Create Ticket
    ticket_payload = {
        "customer_name": "Sarah Connor",
        "customer_email": "sarah@cyberdyne.com",
        "subject": "System login alerts",
        "description": "Critical alerts are firing on my home security hub.",
        "priority": "high",
        "category": "technical"
    }
    response = client.post("/api/v1/tickets/", json=ticket_payload)
    assert response.status_code == 201
    ticket = response.json()
    ticket_id = ticket.get("ticket_id")
    assert ticket_id is not None
    assert ticket.get("status") == "open"

    # 2. GET Ticket by ID
    response = client.get(f"/api/v1/tickets/{ticket_id}")
    assert response.status_code == 200
    assert response.json().get("subject") == "System login alerts"

    # 3. GET List Tickets
    response = client.get("/api/v1/tickets/")
    assert response.status_code == 200
    tickets = response.json()
    assert any(t.get("ticket_id") == ticket_id for t in tickets)

    # 4. PUT Update Ticket Status
    response = client.put(f"/api/v1/tickets/{ticket_id}", json={"status": "in_progress"})
    assert response.status_code == 200
    assert response.json().get("status") == "in_progress"

    # 5. DELETE Ticket
    response = client.delete(f"/api/v1/tickets/{ticket_id}")
    assert response.status_code == 204

    # 6. GET Ticket (Verify 404 deleted status)
    response = client.get(f"/api/v1/tickets/{ticket_id}")
    assert response.status_code == 404


def test_chat_persistence_and_isolation():
    """Verify chat multi-turn query continuity, conversation context preservation, and isolation."""
    # 1. Start Conversation 1
    response = client.post("/api/v1/chat/", json={"message": "What does the Premium Plan include?"})
    assert response.status_code == 200
    res_data1 = response.json()
    conv_id = res_data1.get("conversation_id")
    assert conv_id is not None
    assert "Premium Plan" in res_data1.get("response")

    # 2. Multi-turn Follow-up
    response = client.post("/api/v1/chat/", json={
        "message": "How much does it cost annually?",
        "conversation_id": conv_id
    })
    assert response.status_code == 200
    res_data2 = response.json()
    assert res_data2.get("conversation_id") == conv_id
    assert "199.99" in res_data2.get("response")

    # 3. History Retrieval Check
    response = client.get(f"/api/v1/chat/conversations/{conv_id}/history")
    assert response.status_code == 200
    history = response.json()
    assert len(history) >= 2
    assert history[0].get("role") == "user"
    assert history[1].get("role") == "assistant"

    # 4. Conversation Isolation
    response = client.post("/api/v1/chat/", json={"message": "How much does standard shipping take?"})
    assert response.status_code == 200
    res_data3 = response.json()
    new_conv_id = res_data3.get("conversation_id")
    assert new_conv_id != conv_id
