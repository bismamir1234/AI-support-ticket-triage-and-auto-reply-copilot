"""Comprehensive automated tests for Phase 6: Ticket Management and Data Export.

Tests cover:
- TASK 1: Draft Editing, Saving, and Regenerating
- TASK 2: Mock Approval & Send (with clear mock notice)
- TASK 3: Ticket Resolution & Statistics Refresh
- TASK 4: CSV Export with accurate headers and latest saved final response
- TASK 5: JSON Export with complete ticket analysis and response details
- Database persistence in SQLite
"""
import csv
import io
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

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    """Ensure clean test database tables before running Phase 6 tests."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


# =====================================================================
# TASK 1: DRAFT EDITING, SAVING & PERSISTENCE
# =====================================================================

def test_draft_editing_and_sqlite_persistence():
    """Verify that agents can edit AI-generated responses and save them to SQLite."""
    ticket_payload = {
        "ticket_id": "P6-EDIT-001",
        "customer_name": "Eleanor Vance",
        "customer_email": "eleanor.vance@example.com",
        "subject": "Missing order tracking info",
        "message": "Where is my shipment for order ORD-99214? I need tracking details immediately.",
    }

    # 1. Ingest ticket
    ingest_res = client.post("/api/v1/tickets/process", json=ticket_payload)
    assert ingest_res.status_code == 201
    initial_ticket = ingest_res.json()["ticket"]
    assert initial_ticket["ticket_id"] == "P6-EDIT-001"
    assert initial_ticket["generated_response"] is not None
    assert initial_ticket["edited_response"] is None
    assert initial_ticket["final_response"] == initial_ticket["generated_response"]

    # 2. Agent edits the draft
    edited_text = (
        "Dear Eleanor,\n\n"
        "Thank you for contacting us regarding Order ORD-99214. "
        "I have personally contacted our shipping carrier and your tracking number is TRK-882194. "
        "Estimated delivery is tomorrow by 3 PM.\n\n"
        "Best regards,\nSenior Support Specialist"
    )

    patch_res = client.patch(
        "/api/v1/tickets/P6-EDIT-001",
        json={"edited_response": edited_text},
    )
    assert patch_res.status_code == 200
    patched_ticket = patch_res.json()
    assert patched_ticket["edited_response"] == edited_text
    assert patched_ticket["final_response"] == edited_text

    # 3. Direct SQLite verification
    db = SessionLocal()
    try:
        db_record = db.query(Ticket).filter(Ticket.ticket_id == "P6-EDIT-001").first()
        assert db_record is not None
        assert db_record.edited_response == edited_text
        assert db_record.final_response == edited_text
    finally:
        db.close()


def test_draft_regeneration():
    """Verify that regenerating drafts updates generated_response and resets edited_response."""
    ticket_id = "P6-EDIT-001"
    regen_res = client.post(f"/api/v1/tickets/{ticket_id}/regenerate")
    assert regen_res.status_code == 200
    data = regen_res.json()

    assert data["ticket_id"] == ticket_id
    assert data["generated_response"] is not None
    assert data["edited_response"] is None
    assert data["approval_status"] == "pending"

    # SQLite check
    db = SessionLocal()
    try:
        db_record = db.query(Ticket).filter(Ticket.ticket_id == ticket_id).first()
        assert db_record.generated_response is not None
        assert db_record.edited_response is None
        assert db_record.approval_status == "pending"
    finally:
        db.close()


# =====================================================================
# TASK 2: MOCK APPROVAL & SEND
# =====================================================================

def test_mock_approval_and_send():
    """Verify Approve & Send:
    - Saves approved response
    - Records approval_status = 'approved'
    - Returns mock sending details clearly stating no real email was sent
    - Preserves in SQLite
    """
    ticket_payload = {
        "ticket_id": "P6-APPROVE-002",
        "customer_name": "Daniel Craig",
        "customer_email": "daniel.c@example.com",
        "subject": "Wrong item delivered",
        "message": "I ordered headphones but received a phone case. Order ORD-44321.",
    }
    client.post("/api/v1/tickets/process", json=ticket_payload)

    approved_text = (
        "Hello Daniel,\n\n"
        "We apologize for the fulfillment mistake on Order ORD-44321. "
        "A replacement pair of headphones has been expedited to your address at no charge.\n\n"
        "Sincerely,\nSupport Lead"
    )

    approve_res = client.post(
        "/api/v1/tickets/P6-APPROVE-002/approve",
        json={"edited_response": approved_text},
    )
    assert approve_res.status_code == 200
    approval_data = approve_res.json()

    # 1. Verify ticket state
    ticket = approval_data["ticket"]
    assert ticket["ticket_id"] == "P6-APPROVE-002"
    assert ticket["approval_status"] == "approved"
    assert ticket["edited_response"] == approved_text
    assert ticket["final_response"] == approved_text

    # 2. Verify mock send details
    mock_send = approval_data["mock_send"]
    assert mock_send["is_mock"] is True
    assert mock_send["recipient"] == "daniel.c@example.com"
    assert "No real email was sent" in mock_send["message"]
    assert "demonstration project" in mock_send["message"].lower()
    assert mock_send["sent_content"] == approved_text

    # 3. Direct SQLite verification
    db = SessionLocal()
    try:
        db_record = db.query(Ticket).filter(Ticket.ticket_id == "P6-APPROVE-002").first()
        assert db_record.approval_status == "approved"
        assert db_record.edited_response == approved_text
    finally:
        db.close()


# =====================================================================
# TASK 3: TICKET RESOLUTION
# =====================================================================

def test_ticket_resolution_and_stats():
    """Verify Mark Resolved:
    - Updates ticket_status = 'resolved' in SQLite
    - Refreshes dashboard statistics
    """
    # Check baseline stats
    stats_before = client.get("/api/v1/tickets/stats").json()
    resolved_before = stats_before["resolved_tickets"]

    # Resolve ticket
    res = client.post("/api/v1/tickets/P6-APPROVE-002/resolve")
    assert res.status_code == 200
    res_data = res.json()
    assert res_data["ticket"]["ticket_status"] == "resolved"
    assert "successfully marked as resolved" in res_data["message"]

    # Verify SQLite update
    db = SessionLocal()
    try:
        db_record = db.query(Ticket).filter(Ticket.ticket_id == "P6-APPROVE-002").first()
        assert db_record.ticket_status == "resolved"
    finally:
        db.close()

    # Check updated dashboard statistics
    stats_after = client.get("/api/v1/tickets/stats").json()
    assert stats_after["resolved_tickets"] == resolved_before + 1


# =====================================================================
# TASK 4: CSV EXPORT
# =====================================================================

def test_csv_export_format_and_content():
    """Verify CSV export:
    - Has exact required headers:
      Ticket ID, Customer, Category, Priority, Sentiment, Missing entities, Status, Final response
    - Contains latest saved information (including edited_response as Final response)
    - Returns proper Content-Type and Content-Disposition
    """
    # First, ensure a ticket with edited response exists
    ticket_payload = {
        "ticket_id": "P6-CSV-003",
        "customer_name": "Sophia Loren",
        "customer_email": "sophia.l@example.com",
        "subject": "Billing inquiry",
        "message": "Can you explain the extra charge on my monthly bill?",
    }
    client.post("/api/v1/tickets/process", json=ticket_payload)

    # Edit the response
    latest_final_response = "Dear Sophia, the charge has been credited back to your account in full. Thank you."
    client.patch("/api/v1/tickets/P6-CSV-003", json={"edited_response": latest_final_response})

    # Download CSV export
    res = client.get("/api/v1/tickets/export/csv")
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    assert "attachment" in res.headers["content-disposition"]
    assert 'filename="tickets_export.csv"' in res.headers["content-disposition"]

    # Parse CSV content
    csv_text = res.text
    reader = csv.reader(io.StringIO(csv_text))
    rows = list(reader)

    # Check headers
    expected_headers = [
        "Ticket ID",
        "Customer",
        "Category",
        "Priority",
        "Sentiment",
        "Missing entities",
        "Status",
        "Final response",
    ]
    assert len(rows) > 0
    assert rows[0] == expected_headers

    # Locate Sophia's ticket row
    ticket_row = None
    for r in rows[1:]:
        if r[0] == "P6-CSV-003":
            ticket_row = r
            break

    assert ticket_row is not None, "Exported CSV must contain ticket P6-CSV-003"
    assert "Sophia Loren" in ticket_row[1]
    assert "sophia.l@example.com" in ticket_row[1]
    # Check that Final response contains the latest saved edited text!
    assert ticket_row[7] == latest_final_response


# =====================================================================
# TASK 5: JSON EXPORT
# =====================================================================

def test_json_export_complete_analysis_and_response_details():
    """Verify JSON export:
    - Contains complete ticket analysis and response details
    - Content contains latest saved data
    - Returns valid JSON with Content-Disposition header
    """
    res = client.get("/api/v1/tickets/export/json")
    assert res.status_code == 200
    assert "application/json" in res.headers["content-type"]
    assert "attachment" in res.headers["content-disposition"]
    assert 'filename="tickets_export.json"' in res.headers["content-disposition"]

    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 3

    # Check that every ticket in JSON export has complete analysis and response details
    for item in data:
        # Core fields
        assert "ticket_id" in item
        assert "customer_name" in item
        assert "customer_email" in item
        assert "subject" in item
        assert "original_message" in item
        assert "category" in item
        assert "priority" in item
        assert "sentiment" in item
        assert "extracted_entities" in item
        assert "missing_entities" in item
        assert "ticket_status" in item
        assert "approval_status" in item
        assert "final_response" in item
        # Comprehensive analysis & response details
        assert "analysis_details" in item
        assert "response_details" in item
        assert "category" in item["analysis_details"]
        assert "sentiment" in item["analysis_details"]
        assert "generated_draft" in item["response_details"]
        assert "final_response" in item["response_details"]

    # Verify our specific ticket P6-CSV-003 in JSON
    target_ticket = next((t for t in data if t["ticket_id"] == "P6-CSV-003"), None)
    assert target_ticket is not None
    assert target_ticket["edited_response"] == "Dear Sophia, the charge has been credited back to your account in full. Thank you."
    assert target_ticket["final_response"] == "Dear Sophia, the charge has been credited back to your account in full. Thank you."


def test_batch_log_csv_export():
    """Verify batch ticket log CSV export contains the 10 required fields:
    Ticket ID, Customer inquiry, Classification, Priority, Sentiment, Category,
    AI-generated response, Agent-edited response, Approval status, Timestamp.
    """
    res = client.get("/api/v1/tickets/export/batch-csv")
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    assert 'filename="batch_tickets_log.csv"' in res.headers["content-disposition"]

    rows = list(csv.reader(io.StringIO(res.text)))
    expected_batch_headers = [
        "Ticket ID",
        "Customer inquiry",
        "Classification",
        "Priority",
        "Sentiment",
        "Category",
        "AI-generated response",
        "Agent-edited response",
        "Approval status",
        "Timestamp",
    ]
    assert len(rows) > 0
    assert rows[0] == expected_batch_headers

    # Also test query parameter ?format=batch_log on /export/csv
    res_param = client.get("/api/v1/tickets/export/csv?format=batch_log")
    assert res_param.status_code == 200
    rows_param = list(csv.reader(io.StringIO(res_param.text)))
    assert rows_param[0] == expected_batch_headers


def test_reject_response_workflow():
    """Verify human agent rejection workflow:
    - Post rejection via /api/v1/tickets/{id}/reject
    - Updates approval_status to 'rejected' in SQLite
    - Reflected in subsequent GET requests and stats
    """
    ticket_payload = {
        "ticket_id": "P6-REJ-001",
        "customer_name": "Oliver Queen",
        "customer_email": "oliver@example.com",
        "subject": "System downtime inquiry",
        "message": "When will the portal be online again? Please confirm.",
    }
    create_res = client.post("/api/v1/tickets/process", json=ticket_payload)
    assert create_res.status_code == 201

    # Call reject endpoint
    rej_res = client.post("/api/v1/tickets/P6-REJ-001/reject")
    assert rej_res.status_code == 200
    rej_data = rej_res.json()
    assert rej_data["approval_status"] == "rejected"

    # Fetch directly to verify persistence
    get_res = client.get("/api/v1/tickets/P6-REJ-001")
    assert get_res.status_code == 200
    assert get_res.json()["approval_status"] == "rejected"

