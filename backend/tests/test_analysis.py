"""Automated test suite for Phase 2: AI Ticket Classification & Entity Extraction."""
import json
from starlette.testclient import TestClient
from app.main import app
from app.schemas import (
    TicketAnalysisResponse,
    TicketCategory,
    TicketPriority,
    TicketSentiment,
)

client = TestClient(app)

TEST_TICKETS = [
    {
        "description": "Test Ticket 1: Order Inquiry without Order ID (Clarification Needed)",
        "payload": {
            "ticket_id": "TEST-TCK-001",
            "customer_name": "Jessica Taylor",
            "customer_email": "jtaylor@example.com",
            "subject": "Still waiting on my package",
            "message": "Hi, I ordered some winter coats last week and the tracking has not updated at all. Where is my stuff? I am really frustrated with the delay.",
        },
        "expected_category": TicketCategory.ORDER_ISSUE,
        "expected_needs_clarification": True,
        "expected_missing_entities": ["order_id"],
    },
    {
        "description": "Test Ticket 2: Refund Request with Order ID and Date",
        "payload": {
            "ticket_id": "TEST-TCK-002",
            "customer_name": "Robert Miller",
            "customer_email": "rmiller@example.com",
            "subject": "Requesting return for Order ORD-44910",
            "message": "Hello support team, I received Order ORD-44910 on November 8th. The item is still sealed in the original packaging. Please process my refund.",
        },
        "expected_category": TicketCategory.REFUND,
        "expected_order_id": "ORD-44910",
        "expected_needs_clarification": False,
    },
    {
        "description": "Test Ticket 3: Critical Technical Outage with Error Code",
        "payload": {
            "ticket_id": "TEST-TCK-003",
            "customer_name": "Amanda Cross",
            "customer_email": "across@corp.com",
            "subject": "CRITICAL: Checkout payment failing with Error Code 500",
            "message": "Urgent! None of our team members can complete checkout. The screen throws Error Code: 500 Internal Server Error when submitting payment details. Please fix this immediately!",
        },
        "expected_category": TicketCategory.TECHNICAL_ISSUE,
        "expected_priority": TicketPriority.CRITICAL,
        "expected_error_code": "500",
    },
    {
        "description": "Test Ticket 4: Positive General Inquiry",
        "payload": {
            "ticket_id": "TEST-TCK-004",
            "customer_name": "Leo Martinez",
            "customer_email": "leo@example.com",
            "subject": "Question about weekend store hours",
            "message": "Good morning! I love your products. Could you please let me know what time your downtown store opens on Sundays? Thank you so much for your help!",
        },
        "expected_category": TicketCategory.GENERAL_INQUIRY,
        "expected_priority": TicketPriority.LOW,
        "expected_sentiment": TicketSentiment.POSITIVE,
    },
]


def run_all_tests():
    print("=" * 70)
    print("PHASE 2: RUNNING AI TICKET ANALYSIS VERIFICATION SUITE")
    print("=" * 70)

    for idx, test in enumerate(TEST_TICKETS, start=1):
        print(f"\n[{idx}] {test['description']}")
        print(f"Payload ticket_id: {test['payload']['ticket_id']}")

        response = client.post("/api/v1/tickets/analyze", json=test["payload"])
        assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}: {response.text}"

        data = response.json()
        validated = TicketAnalysisResponse.model_validate(data)

        # Validate Expected Category
        assert validated.category == test["expected_category"], (
            f"Category mismatch: expected {test['expected_category']}, got {validated.category}"
        )

        # Validate Missing Entities if specified
        if "expected_missing_entities" in test:
            for entity in test["expected_missing_entities"]:
                assert entity in validated.missing_entities, (
                    f"Expected '{entity}' in missing_entities: {validated.missing_entities}"
                )
            assert validated.needs_clarification == test["expected_needs_clarification"], (
                f"Clarification mismatch: expected {test['expected_needs_clarification']}, got {validated.needs_clarification}"
            )

        # Validate Order ID if specified
        if "expected_order_id" in test:
            assert validated.entities.order_id == test["expected_order_id"], (
                f"Order ID mismatch: expected {test['expected_order_id']}, got {validated.entities.order_id}"
            )

        # Validate Error Code if specified
        if "expected_error_code" in test:
            assert validated.entities.error_code == test["expected_error_code"], (
                f"Error code mismatch: expected {test['expected_error_code']}, got {validated.entities.error_code}"
            )

        # Validate Priority if specified
        if "expected_priority" in test:
            assert validated.priority == test["expected_priority"], (
                f"Priority mismatch: expected {test['expected_priority']}, got {validated.priority}"
            )

        # Validate Sentiment if specified
        if "expected_sentiment" in test:
            assert validated.sentiment == test["expected_sentiment"], (
                f"Sentiment mismatch: expected {test['expected_sentiment']}, got {validated.sentiment}"
            )

        print("-> Status: PASSED")
        print("-> Output JSON:")
        print(json.dumps(data, indent=2))

    print("\n" + "=" * 70)
    print("ALL TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    run_all_tests()
