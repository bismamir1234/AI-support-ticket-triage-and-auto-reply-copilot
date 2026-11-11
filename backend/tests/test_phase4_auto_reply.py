"""Automated test suite for Phase 4: Database, Policy Matching, and AI Auto-Reply Generation."""
import json
import sys
from pathlib import Path
import pytest
from starlette.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import Ticket
from app.schemas import (
    TicketCategory,
    TicketIngestionRequest,
)
from app.services.auto_reply_generator import auto_reply_service, policy_manager

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    """Ensure clean test database tables before running tests."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


# =====================================================================
# TASK 2: POLICY MATCHING TESTS
# =====================================================================

def test_policy_matching_all_categories():
    """Verify policy.json is correctly loaded and mapped to each category."""
    order_policy = policy_manager.get_policy_for_category("order_issue")
    assert order_policy is not None
    assert order_policy["id"] == "POL-ORDER"
    assert order_policy["name"] == "Order and Delivery"

    refund_policy = policy_manager.get_policy_for_category("refund")
    assert refund_policy is not None
    assert refund_policy["id"] == "POL-REFUND"
    assert refund_policy["name"] == "Refund"

    tech_policy = policy_manager.get_policy_for_category("technical_issue")
    assert tech_policy is not None
    assert tech_policy["id"] == "POL-TECH"
    assert tech_policy["name"] == "Technical Support"

    general_policy = policy_manager.get_policy_for_category("general_inquiry")
    assert general_policy is not None
    assert general_policy["id"] == "POL-GENERAL"
    assert general_policy["name"] == "General Inquiry"


# =====================================================================
# TASK 3 & 4 & 5: RESPONSE GENERATION, GROUNDING & SQLITE PERSISTENCE
# =====================================================================

def test_order_issue_auto_reply_and_persistence():
    """SCENARIO 1: Order Issue with Order ID ORD-55102
    - Matches 'Order and Delivery' policy
    - Grounds response in delivery timelines
    - References ORD-55102 without inventing numbers
    - Persists in SQLite database
    """
    payload = {
        "ticket_id": "P4-ORDER-001",
        "customer_name": "Marcus Kane",
        "customer_email": "marcus.kane@example.com",
        "subject": "Delayed shipment status",
        "message": "My order ORD-55102 was placed 5 days ago and has not arrived. Can you check where it is?",
    }

    response = client.post("/api/v1/tickets/process", json=payload)
    assert response.status_code == 201, f"Failed: {response.text}"
    data = response.json()

    # 1. Verify Analysis
    assert data["analysis"]["category"] == "order_issue"
    assert data["analysis"]["entities"]["order_id"] == "ORD-55102"
    assert data["analysis"]["needs_clarification"] is False

    # 2. Verify Policy Matching & Auto-Reply
    auto_reply = data["auto_reply"]
    assert auto_reply["matched_policy_id"] == "POL-ORDER"
    assert auto_reply["policy_name"] == "Order and Delivery"

    reply_text = auto_reply["suggested_reply"]
    assert "Marcus" in reply_text
    assert "ORD-55102" in reply_text
    # Grounding check: standard delivery 3-5 days
    assert any(term in reply_text.lower() for term in ["3-5", "delivery", "shipping", "carrier"])
    # Must not claim unverified delivery
    assert "has been delivered" not in reply_text.lower()

    # 3. Verify SQLite Persistence
    ticket_db = data["ticket"]
    assert ticket_db["ticket_id"] == "P4-ORDER-001"
    assert ticket_db["category"] == "order_issue"
    assert ticket_db["approval_status"] == "pending"
    assert ticket_db["ticket_status"] == "open"
    assert ticket_db["generated_response"] == reply_text

    # Direct DB verification
    db = SessionLocal()
    try:
        row = db.query(Ticket).filter(Ticket.ticket_id == "P4-ORDER-001").first()
        assert row is not None
        assert row.customer_email == "marcus.kane@example.com"
        assert row.extracted_entities["order_id"] == "ORD-55102"
    finally:
        db.close()


def test_refund_request_missing_order_id_grounding_and_persistence():
    """SCENARIO 2: Refund Request with Missing Order ID
    - Matches 'Refund' policy
    - Detects missing order ID and sets needs_clarification=True
    - Politely requests the order number (Rule 3)
    - NEVER promises an unapproved refund (Rule 4)
    - Persists in SQLite
    """
    payload = {
        "ticket_id": "P4-REFUND-002",
        "customer_name": "Linda Gomez",
        "customer_email": "linda.g@example.com",
        "subject": "Want a refund",
        "message": "I purchased a dress two weeks ago but it does not fit. I want to return it for a refund, but I lost my order number.",
    }

    response = client.post("/api/v1/tickets/process", json=payload)
    assert response.status_code == 201, f"Failed: {response.text}"
    data = response.json()

    # 1. Verify Analysis
    assert data["analysis"]["category"] == "refund"
    assert "order_id" in data["analysis"]["missing_entities"]
    assert data["analysis"]["needs_clarification"] is True

    # 2. Verify Policy Matching & Auto-Reply
    auto_reply = data["auto_reply"]
    assert auto_reply["matched_policy_id"] == "POL-REFUND"
    assert auto_reply["policy_name"] == "Refund"

    reply_text = auto_reply["suggested_reply"]
    reply_lower = reply_text.lower()
    # Rule 3: Must politely request the missing order number
    assert "order" in reply_lower and ("number" in reply_lower or "id" in reply_lower or "details" in reply_lower)
    # Rule 1: Never invent an order number
    assert "ORD-" not in reply_text
    # Rule 4: Never state refund is already processed
    assert "refund has been issued" not in reply_lower
    assert "refund has been processed" not in reply_lower
    # Grounding in Refund policy (30 days, 5-7 business days)
    assert any(term in reply_lower for term in ["30 days", "30-day", "5-7", "return"])

    # 3. Verify SQLite Persistence
    ticket_db = data["ticket"]
    assert ticket_db["ticket_id"] == "P4-REFUND-002"
    assert ticket_db["category"] == "refund"
    assert ticket_db["approval_status"] == "pending"


def test_technical_issue_error_code_grounding_and_persistence():
    """SCENARIO 3: Technical Issue with Error Code ERR-502
    - Matches 'Technical Support' policy
    - Extracts error code ERR-502
    - Includes standard troubleshooting (cache/incognito)
    - Sets priority to critical/high due to checkout outage
    - Persists in SQLite
    """
    payload = {
        "ticket_id": "P4-TECH-003",
        "customer_name": "Kevin Zhang",
        "customer_email": "kzhang@techcorp.io",
        "subject": "Checkout page error 502",
        "message": "When I try to complete my purchase on the checkout page, the site crashes with error code ERR-502 Bad Gateway. We cannot place company orders!",
    }

    response = client.post("/api/v1/tickets/process", json=payload)
    assert response.status_code == 201, f"Failed: {response.text}"
    data = response.json()

    # 1. Verify Analysis
    assert data["analysis"]["category"] == "technical_issue"
    assert data["analysis"]["entities"]["error_code"] == "ERR-502"
    assert data["analysis"]["priority"] in ["high", "critical"]

    # 2. Verify Policy Matching & Auto-Reply
    auto_reply = data["auto_reply"]
    assert auto_reply["matched_policy_id"] == "POL-TECH"
    assert auto_reply["policy_name"] == "Technical Support"

    reply_text = auto_reply["suggested_reply"]
    reply_lower = reply_text.lower()
    # References error code
    assert "ERR-502" in reply_text or "502" in reply_text
    # Grounded in technical support policy guidelines (cache/troubleshooting)
    assert any(term in reply_lower for term in ["cache", "cookies", "browser", "engineering", "investigat"])

    # 3. Verify SQLite Persistence
    ticket_db = data["ticket"]
    assert ticket_db["ticket_id"] == "P4-TECH-003"
    assert ticket_db["category"] == "technical_issue"


# =====================================================================
# HUMAN-IN-THE-LOOP APPROVAL & EDIT WORKFLOW TEST
# =====================================================================

def test_human_in_the_loop_approval_workflow():
    """Verify that a support agent can edit draft responses and approve them."""
    ticket_id = "P4-ORDER-001"
    new_response = "Hello Marcus, I have personally expedited Order ORD-55102 with FedEx. It will arrive tomorrow morning. Best regards, Senior Support Lead"

    update_payload = {
        "edited_response": new_response,
        "approval_status": "approved",
        "ticket_status": "in_progress",
    }

    patch_resp = client.patch(f"/api/v1/tickets/{ticket_id}", json=update_payload)
    assert patch_resp.status_code == 200
    updated_data = patch_resp.json()

    assert updated_data["edited_response"] == new_response
    assert updated_data["approval_status"] == "approved"
    assert updated_data["ticket_status"] == "in_progress"

    # Verify query by approval_status
    list_resp = client.get("/api/v1/tickets?approval_status=approved")
    assert list_resp.status_code == 200
    items = list_resp.json()
    assert any(item["ticket_id"] == ticket_id for item in items)

