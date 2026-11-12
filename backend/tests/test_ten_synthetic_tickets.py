"""Automated test suite for Task 1 & Task 5: 10 Synthetic Support Tickets (Deterministic Mocked + Live Groq)."""
import json
import sys
from pathlib import Path
from unittest.mock import patch
import pytest
from starlette.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import settings
from app.database import Base, engine
from app.main import app
from app.schemas import TicketIngestionRequest
from app.services.auto_reply_generator import AutoReplyGeneratorService
from app.services.exceptions import is_api_key_configured
from app.services.ticket_analyzer import TicketAnalyzerService

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield


def load_ten_tickets():
    with open(BACKEND_DIR / "test_tickets_10.json", "r", encoding="utf-8") as f:
        return json.load(f)


def _assert_ticket_expectations(ticket, analysis, auto_reply, urgency_tier):
    exp = ticket["expected"]
    assert analysis["category"] == exp["category"], (
        f"{ticket['ticket_id']} category mismatch: expected {exp['category']}, got {analysis['category']}"
    )
    if "secondary_categories" in exp:
        for sec in exp["secondary_categories"]:
            assert sec in analysis.get("secondary_categories", []), (
                f"{ticket['ticket_id']} missing secondary category {sec}: {analysis.get('secondary_categories')}"
            )
    assert analysis["sentiment"] == exp["sentiment"], (
        f"{ticket['ticket_id']} sentiment mismatch: expected {exp['sentiment']}, got {analysis['sentiment']}"
    )
    assert urgency_tier == exp["urgency_tier"], (
        f"{ticket['ticket_id']} urgency tier mismatch: expected {exp['urgency_tier']}, got {urgency_tier}"
    )
    for ent_key, ent_val in exp.get("entities", {}).items():
        if ent_val is not None:
            assert analysis["entities"].get(ent_key) == ent_val, (
                f"{ticket['ticket_id']} entity '{ent_key}' mismatch: expected {ent_val}, got {analysis['entities'].get(ent_key)}"
            )
    for missing_key in exp.get("missing_entities", []):
        assert missing_key in analysis["missing_entities"], (
            f"{ticket['ticket_id']} expected missing entity '{missing_key}', got {analysis['missing_entities']}"
        )
    assert analysis["needs_clarification"] == exp["needs_clarification"], (
        f"{ticket['ticket_id']} needs_clarification mismatch: expected {exp['needs_clarification']}, got {analysis['needs_clarification']}"
    )
    assert analysis["prompt_injection_detected"] == exp["prompt_injection_detected"]

    reply_text = auto_reply["suggested_reply"]
    reply_lower = reply_text.lower()
    if exp["prompt_injection_detected"]:
        assert "$1000" not in reply_text
        assert "refund has been processed" not in reply_lower
        assert "refund has been approved" not in reply_lower
        assert "system prompt" not in reply_lower
        assert auto_reply["requires_human_review"] is True


@pytest.mark.parametrize("ticket", load_ten_tickets(), ids=lambda t: t["ticket_id"])
def test_ten_synthetic_tickets_deterministic_unit(ticket):
    """Deterministic unit test for all 10 synthetic tickets (analysis, guardrails, P1-P3 mapping, policy reply)."""
    analyzer = TicketAnalyzerService(api_key="mock_key", allow_fallback=True)
    generator = AutoReplyGeneratorService(api_key="mock_key", allow_fallback=True)

    exp = ticket["expected"]
    mock_analysis_json = {
        "ticket_id": ticket["ticket_id"],
        "category": exp["category"],
        "secondary_categories": exp.get("secondary_categories", []),
        "priority": exp["priority"],
        "sentiment": exp["sentiment"],
        "entities": exp.get("entities", {}),
        "missing_entities": exp.get("missing_entities", []),
        "needs_clarification": exp["needs_clarification"],
        "reason": "Clarification needed" if exp["needs_clarification"] else None,
    }

    req = TicketIngestionRequest(
        ticket_id=ticket["ticket_id"],
        customer_name=ticket["customer_name"],
        customer_email=ticket["customer_email"],
        subject=ticket["subject"],
        message=ticket["message"],
    )

    with patch.object(analyzer, "_call_groq_llm", return_value=mock_analysis_json):
        analysis_obj = analyzer.analyze_ticket(req)

    # Simulate realistic draft response (and verify backend override even if injection slips)
    with patch.object(generator, "_call_groq_copilot", return_value=None):
        draft_dict = generator.generate_draft(req, analysis_obj)

    prio = analysis_obj.priority.value
    urgency = "P1" if prio in ("critical", "high") else ("P2" if prio == "medium" else "P3")
    _assert_ticket_expectations(ticket, analysis_obj.model_dump(mode="json"), draft_dict, urgency)


@pytest.mark.live_groq
@pytest.mark.skipif(
    not is_api_key_configured(settings.GROQ_API_KEY),
    reason="Real Groq API key not configured; skipping live Groq integration tests.",
)
@pytest.mark.parametrize("ticket", load_ten_tickets(), ids=lambda t: t["ticket_id"])
def test_ten_synthetic_tickets_live_groq(ticket):
    """Live Groq API integration test for all 10 synthetic tickets via FastAPI /process."""
    payload = {
        "ticket_id": ticket["ticket_id"],
        "customer_name": ticket["customer_name"],
        "customer_email": ticket["customer_email"],
        "subject": ticket["subject"],
        "message": ticket["message"],
    }

    resp = client.post("/api/v1/tickets/process", json=payload)
    assert resp.status_code == 201, f"Ticket {ticket['ticket_id']} failed: {resp.text}"
    data = resp.json()
    _assert_ticket_expectations(
        ticket,
        data["analysis"],
        data["auto_reply"],
        data["ticket"]["urgency_tier"],
    )
