"""Evaluation and Comparison Report Generator for Phase 3 Five-Ticket Classification."""
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure backend root is on sys.path
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.schemas import TicketIngestionRequest
from app.services.ticket_analyzer import analyzer_service

LOG_FILE = BACKEND_DIR / "test_logs.log"
REPORT_FILE = BACKEND_DIR / "comparison_report.json"
TEST_DATA_FILE = BACKEND_DIR / "test_tickets.json"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("Phase3Evaluator")


def run_evaluation():
    logger.info("Starting Phase 3: Five-Ticket Classification Testing...")
    logger.info(f"Model configured: {analyzer_service.model}")
    logger.info(f"Test data source: {TEST_DATA_FILE}")

    with open(TEST_DATA_FILE, "r", encoding="utf-8") as f:
        test_tickets = json.load(f)

    results = []
    category_matches = 0
    sentiment_matches = 0
    priority_matches = 0
    entity_matches = 0
    clarification_matches = 0
    incorrect_classifications = []

    for t in test_tickets:
        ticket_id = t["ticket_id"]
        customer_name = t["customer_name"]
        customer_email = t["customer_email"]
        subject = t["subject"]
        message = t["message"]
        expected = t["expected"]

        logger.info(f"--- Testing {ticket_id}: '{message}' ---")

        req = TicketIngestionRequest(
            ticket_id=ticket_id,
            customer_name=customer_name,
            customer_email=customer_email,
            subject=subject,
            message=message,
        )

        # Actual execution against Groq
        actual = analyzer_service.analyze_ticket(req)

        # Check Category
        cat_match = actual.category.value == expected["category"]
        if cat_match:
            category_matches += 1
        else:
            incorrect_classifications.append({
                "ticket_id": ticket_id,
                "dimension": "category",
                "expected": expected["category"],
                "actual": actual.category.value,
            })

        # Check Sentiment
        sent_match = actual.sentiment.value.lower() == expected["sentiment"].lower()
        if sent_match:
            sentiment_matches += 1
        else:
            incorrect_classifications.append({
                "ticket_id": ticket_id,
                "dimension": "sentiment",
                "expected": expected["sentiment"],
                "actual": actual.sentiment.value,
            })

        # Check Priority
        prio_match = actual.priority.value.lower() == expected["priority"].lower()
        if prio_match:
            priority_matches += 1

        # Check Entity Extraction
        ent_match = True
        if expected["entities"].get("order_id"):
            if actual.entities.order_id != expected["entities"]["order_id"]:
                ent_match = False
        if expected["entities"].get("error_code"):
            if actual.entities.error_code != expected["entities"]["error_code"]:
                ent_match = False
        if ent_match:
            entity_matches += 1

        # Check Missing Entities / Clarification
        clarif_match = (
            actual.needs_clarification == expected["needs_clarification"]
            and set(actual.missing_entities) == set(expected["missing_entities"])
        )
        if clarif_match:
            clarification_matches += 1

        overall_pass = cat_match and sent_match and ent_match and clarif_match
        status_label = "PASS" if overall_pass else "FAIL"

        logger.info(
            f"Result for {ticket_id}: [{status_label}] | "
            f"Category: Exp='{expected['category']}', Act='{actual.category.value}' | "
            f"Sentiment: Exp='{expected['sentiment']}', Act='{actual.sentiment.value}' | "
            f"Priority: Exp='{expected['priority']}', Act='{actual.priority.value}' | "
            f"Entities: {actual.entities.model_dump()} | "
            f"Needs Clarification: {actual.needs_clarification}"
        )

        results.append({
            "ticket_id": ticket_id,
            "subject": subject,
            "message": message,
            "expected": expected,
            "actual": {
                "category": actual.category.value,
                "priority": actual.priority.value,
                "sentiment": actual.sentiment.value,
                "entities": actual.entities.model_dump(),
                "missing_entities": actual.missing_entities,
                "needs_clarification": actual.needs_clarification,
                "reason": actual.reason,
            },
            "eval_checks": {
                "category_match": cat_match,
                "sentiment_match": sent_match,
                "priority_match": prio_match,
                "entity_match": ent_match,
                "clarification_match": clarif_match,
                "overall_pass": overall_pass,
            },
            "status": status_label,
        })

    total_tickets = len(test_tickets)
    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model_used": analyzer_service.model,
        "total_tickets": total_tickets,
        "category_accuracy": f"{category_matches}/{total_tickets} ({category_matches / total_tickets * 100:.1f}%)",
        "sentiment_accuracy": f"{sentiment_matches}/{total_tickets} ({sentiment_matches / total_tickets * 100:.1f}%)",
        "entity_accuracy": f"{entity_matches}/{total_tickets} ({entity_matches / total_tickets * 100:.1f}%)",
        "clarification_accuracy": f"{clarification_matches}/{total_tickets} ({clarification_matches / total_tickets * 100:.1f}%)",
        "priority_accuracy": f"{priority_matches}/{total_tickets} ({priority_matches / total_tickets * 100:.1f}%)",
        "incorrect_classifications_count": len(incorrect_classifications),
        "incorrect_classifications": incorrect_classifications,
    }

    report = {
        "summary": summary,
        "test_results": results,
    }

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    logger.info(f"Comparison report saved to {REPORT_FILE}")

    # Copy to root as well
    root_report = BACKEND_DIR.parent / "comparison_report.json"
    with open(root_report, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    root_log = BACKEND_DIR.parent / "test_logs.log"
    with open(root_log, "w", encoding="utf-8") as f:
        with open(LOG_FILE, "r", encoding="utf-8") as src:
            f.write(src.read())

    print("\n" + "=" * 80)
    print("PHASE 3 TEST SUMMARY & COMPARISON REPORT")
    print("=" * 80)
    print(f"Total Tickets Tested: {total_tickets}")
    print(f"Category Accuracy:    {summary['category_accuracy']}")
    print(f"Sentiment Accuracy:   {summary['sentiment_accuracy']}")
    print(f"Entity Accuracy:      {summary['entity_accuracy']}")
    print(f"Clarification Acc:    {summary['clarification_accuracy']}")
    print(f"Priority Accuracy:    {summary['priority_accuracy']}")
    print(f"Incorrect Count:      {summary['incorrect_classifications_count']}")
    print("=" * 80)

    return report


if __name__ == "__main__":
    run_evaluation()

