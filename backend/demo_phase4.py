"""Demonstration script for Phase 4: Policy Matching, AI Auto-Reply Generation, and SQLite Persistence."""
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.database import Base, SessionLocal, engine
from app.models import Ticket
from app.schemas import TicketIngestionRequest
from app.services.ticket_service import ticket_db_service

SCENARIOS = [
    {
        "name": "SCENARIO 1: ORDER ISSUE",
        "ticket": TicketIngestionRequest(
            ticket_id="DEMO-ORD-101",
            customer_name="Marcus Vance",
            customer_email="marcus.v@example.com",
            subject="Delayed Package ORD-88231",
            message="Hello, my package for order ORD-88231 has been delayed for 4 days at the regional hub with no tracking updates. When will it arrive?",
        ),
    },
    {
        "name": "SCENARIO 2: REFUND REQUEST (MISSING ORDER ID)",
        "ticket": TicketIngestionRequest(
            ticket_id="DEMO-REF-102",
            customer_name="Elena Rostova",
            customer_email="elena.r@example.com",
            subject="Refund request for shoes",
            message="Hi team, I would like to request a refund for a pair of running shoes I purchased two weeks ago. They are brand new and unworn, but I lost my order number.",
        ),
    },
    {
        "name": "SCENARIO 3: TECHNICAL ISSUE",
        "ticket": TicketIngestionRequest(
            ticket_id="DEMO-TECH-103",
            customer_name="David Chen",
            customer_email="dchen.dev@example.com",
            subject="Checkout payment crash",
            message="Every time I click 'Place Order' on the checkout page, the site crashes with error code ERR-502 Bad Gateway. The entire payment flow is blocked!",
        ),
    },
]


def run_demo():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    print("=" * 80)
    print("PHASE 4: POLICY MATCHING, AI EMAIL GENERATION & SQLITE PERSISTENCE DEMO")
    print("=" * 80)

    try:
        for item in SCENARIOS:
            print(f"\n>>> {item['name']}")
            print(f"Ticket ID: {item['ticket'].ticket_id}")
            print(f"Customer:  {item['ticket'].customer_name} ({item['ticket'].customer_email})")
            print(f"Subject:   {item['ticket'].subject}")
            print(f"Message:   {item['ticket'].message}")

            result = ticket_db_service.process_and_save_ticket(db, item["ticket"])

            print("\n--- AI Analysis & Policy Matching ---")
            print(f"Category:         {result.analysis.category.value}")
            print(f"Priority:         {result.analysis.priority.value}")
            print(f"Sentiment:        {result.analysis.sentiment.value}")
            print(f"Matched Policy:   {result.auto_reply.policy_name} ({result.auto_reply.matched_policy_id})")
            print(f"Extracted Entities: {result.analysis.entities.model_dump()}")
            print(f"Missing Entities:   {result.analysis.missing_entities}")
            print(f"Needs Clarification: {result.analysis.needs_clarification}")

            print("\n--- Grounding Rules Verification ---")
            for rule, status in result.auto_reply.grounding_rules_checked.items():
                print(f"  [{'PASS' if status else 'FAIL'}] {rule}")

            print("\n--- Generated AI Auto-Reply Draft ---")
            print(result.auto_reply.suggested_reply)

            print("\n--- Recommended Agent Action Items ---")
            for act in result.auto_reply.action_items:
                print(f"  • {act}")

            print("\n--- SQLite Database Row Confirmation ---")
            row = db.query(Ticket).filter(Ticket.ticket_id == item["ticket"].ticket_id).first()
            print(f"  Stored in DB: ticket_id={row.ticket_id}, category={row.category}, status={row.ticket_status}, approval={row.approval_status}")
            print("-" * 80)
    finally:
        db.close()


if __name__ == "__main__":
    run_demo()

