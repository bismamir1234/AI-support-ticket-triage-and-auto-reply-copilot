"""Pytest automated test suite for Phase 3: Five-Ticket Classification & Entity Extraction."""
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import pytest
from starlette.testclient import TestClient

from app.main import app
from app.schemas import (
    TicketAnalysisResponse,
    TicketCategory,
    TicketPriority,
    TicketSentiment,
)
from app.services.ticket_analyzer import TicketAnalyzerService, analyzer_service

client = TestClient(app)


@pytest.fixture(scope="module")
def test_tickets_data():
    json_path = BACKEND_DIR / "test_tickets.json"
    with open(json_path, "r", encoding="utf-8") as f:
        return {item["ticket_id"]: item for item in json.load(f)}


# =====================================================================
# INTEGRATION TESTS WITH ACTUAL GROQ / FULL PIPELINE
# =====================================================================

def test_ticket_1_order_issue(test_tickets_data):
    """TICKET 1 — ORDER ISSUE:
    'My order ORD-2045 has not arrived. Please check its status.'
    Expected: Category: order_issue, Sentiment: Frustrated, Entity: ORD-2045
    """
    ticket = test_tickets_data["TICKET-1"]
    response = client.post("/api/v1/tickets/analyze", json={
        "ticket_id": ticket["ticket_id"],
        "customer_name": ticket["customer_name"],
        "customer_email": ticket["customer_email"],
        "subject": ticket["subject"],
        "message": ticket["message"],
    })
    assert response.status_code == 200
    data = response.json()
    validated = TicketAnalysisResponse.model_validate(data)

    assert validated.category == TicketCategory.ORDER_ISSUE, (
        f"Expected order_issue, got {validated.category}"
    )
    assert validated.sentiment == TicketSentiment.FRUSTRATED, (
        f"Expected Frustrated sentiment, got {validated.sentiment}"
    )
    assert validated.entities.order_id == "ORD-2045", (
        f"Expected entity ORD-2045, got {validated.entities.order_id}"
    )
    assert validated.needs_clarification is False


def test_ticket_2_refund_request(test_tickets_data):
    """TICKET 2 — REFUND REQUEST:
    'I want a refund for my purchase, but I do not have my order number.'
    Expected: Category: refund, Missing entity: order_id, Needs clarification: true
    """
    ticket = test_tickets_data["TICKET-2"]
    response = client.post("/api/v1/tickets/analyze", json={
        "ticket_id": ticket["ticket_id"],
        "customer_name": ticket["customer_name"],
        "customer_email": ticket["customer_email"],
        "subject": ticket["subject"],
        "message": ticket["message"],
    })
    assert response.status_code == 200
    data = response.json()
    validated = TicketAnalysisResponse.model_validate(data)

    assert validated.category == TicketCategory.REFUND, (
        f"Expected refund, got {validated.category}"
    )
    assert "order_id" in validated.missing_entities, (
        f"Expected order_id in missing_entities, got {validated.missing_entities}"
    )
    assert validated.needs_clarification is True, (
        f"Expected needs_clarification=True, got {validated.needs_clarification}"
    )
    assert validated.reason is not None


def test_ticket_3_technical_issue(test_tickets_data):
    """TICKET 3 — TECHNICAL ISSUE:
    'Your website shows error code ERR-404 whenever I try to log in.'
    Expected: Category: technical_issue, Entity: ERR-404
    """
    ticket = test_tickets_data["TICKET-3"]
    response = client.post("/api/v1/tickets/analyze", json={
        "ticket_id": ticket["ticket_id"],
        "customer_name": ticket["customer_name"],
        "customer_email": ticket["customer_email"],
        "subject": ticket["subject"],
        "message": ticket["message"],
    })
    assert response.status_code == 200
    data = response.json()
    validated = TicketAnalysisResponse.model_validate(data)

    assert validated.category == TicketCategory.TECHNICAL_ISSUE, (
        f"Expected technical_issue, got {validated.category}"
    )
    assert validated.entities.error_code == "ERR-404", (
        f"Expected error_code ERR-404, got {validated.entities.error_code}"
    )
    assert validated.needs_clarification is False


def test_ticket_4_positive_feedback(test_tickets_data):
    """TICKET 4 — POSITIVE FEEDBACK:
    'Thank you for helping me with my account. Your support is excellent.'
    Expected: Category: general_inquiry, Sentiment: Positive
    """
    ticket = test_tickets_data["TICKET-4"]
    response = client.post("/api/v1/tickets/analyze", json={
        "ticket_id": ticket["ticket_id"],
        "customer_name": ticket["customer_name"],
        "customer_email": ticket["customer_email"],
        "subject": ticket["subject"],
        "message": ticket["message"],
    })
    assert response.status_code == 200
    data = response.json()
    validated = TicketAnalysisResponse.model_validate(data)

    assert validated.category == TicketCategory.GENERAL_INQUIRY, (
        f"Expected general_inquiry, got {validated.category}"
    )
    assert validated.sentiment == TicketSentiment.POSITIVE, (
        f"Expected Positive sentiment, got {validated.sentiment}"
    )
    assert validated.priority == TicketPriority.LOW


def test_ticket_5_highly_urgent_issue(test_tickets_data):
    """TICKET 5 — HIGHLY URGENT ISSUE:
    'My account is locked and I urgently need access to complete an important task.'
    Expected: Category: technical_issue, Sentiment: Highly Urgent
    """
    ticket = test_tickets_data["TICKET-5"]
    response = client.post("/api/v1/tickets/analyze", json={
        "ticket_id": ticket["ticket_id"],
        "customer_name": ticket["customer_name"],
        "customer_email": ticket["customer_email"],
        "subject": ticket["subject"],
        "message": ticket["message"],
    })
    assert response.status_code == 200
    data = response.json()
    validated = TicketAnalysisResponse.model_validate(data)

    assert validated.category == TicketCategory.TECHNICAL_ISSUE, (
        f"Expected technical_issue, got {validated.category}"
    )
    assert validated.sentiment == TicketSentiment.HIGHLY_URGENT, (
        f"Expected Highly Urgent sentiment, got {validated.sentiment}"
    )
    assert validated.priority in [TicketPriority.HIGH, TicketPriority.CRITICAL]


# =====================================================================
# UNIT TESTS WITH MOCKED GROQ API RESPONSES
# =====================================================================

def test_mocked_groq_response():
    """Unit test using a mocked Groq API client to test isolated service parsing."""
    mock_service = TicketAnalyzerService(api_key="mock_key")
    
    mock_llm_json = {
        "ticket_id": "MOCK-001",
        "category": "refund",
        "priority": "high",
        "sentiment": "Neutral",
        "entities": {
            "order_id": None,
            "account_email": "mock@example.com",
            "error_code": None,
            "date": None,
        },
        "missing_entities": ["order_id"],
        "needs_clarification": True,
        "reason": "Order number is missing.",
    }

    with patch.object(mock_service, "_call_groq_llm", return_value=mock_llm_json):
        from app.schemas import TicketIngestionRequest
        req = TicketIngestionRequest(
            ticket_id="MOCK-001",
            customer_name="Mock Customer",
            customer_email="mock@example.com",
            subject="Refund query",
            message="Please refund my money without order ID",
        )
        result = mock_service.analyze_ticket(req)
        assert result.category == TicketCategory.REFUND
        assert result.sentiment == TicketSentiment.NEUTRAL
        assert result.needs_clarification is True
        assert "order_id" in result.missing_entities
