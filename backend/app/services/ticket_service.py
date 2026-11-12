import csv
import io
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from sqlalchemy.orm import Session
from app.models import Ticket
from app.schemas import (
    AutoReplyDraftResponse,
    MockSendDetails,
    TicketAnalysisResponse,
    TicketApprovalResponse,
    TicketDBResponse,
    TicketDBUpdate,
    TicketIngestionRequest,
    TicketProcessResult,
    TicketResolutionResponse,
)
from app.services.auto_reply_generator import auto_reply_service
from app.services.ticket_analyzer import analyzer_service


class TicketDatabaseService:
    """Manages SQLite ticket persistence, triage execution, and human approval workflow."""

    def process_and_save_ticket(
        self, db: Session, req: TicketIngestionRequest
    ) -> TicketProcessResult:
        """Run AI analysis, policy-grounded auto-reply generation, and persist to SQLite."""
        # 1. AI Analysis & Entity Extraction
        analysis = analyzer_service.analyze_ticket(req)

        # 2. Policy Matching & Auto-Reply Generation
        draft = auto_reply_service.generate_draft(req, analysis)
        auto_reply_response = AutoReplyDraftResponse(
            ticket_id=draft["ticket_id"],
            matched_policy_id=draft["matched_policy_id"],
            policy_name=draft["policy_name"],
            suggested_reply=draft["suggested_reply"],
            action_items=draft.get("action_items", []),
            confidence_score=draft.get("confidence_score", 0.95),
            requires_human_review=draft.get("requires_human_review", False),
            clarification_requested=draft.get("clarification_requested", False),
            grounding_rules_checked=draft.get("grounding_rules_checked", {}),
        )

        # 3. Upsert into SQLite Database
        existing_ticket = db.query(Ticket).filter(Ticket.ticket_id == req.ticket_id).first()
        now = datetime.now(timezone.utc)

        if existing_ticket:
            existing_ticket.customer_name = req.customer_name
            existing_ticket.customer_email = req.customer_email
            existing_ticket.subject = req.subject
            existing_ticket.original_message = req.message
            existing_ticket.category = analysis.category.value
            existing_ticket.secondary_categories = analysis.secondary_categories
            existing_ticket.priority = analysis.priority.value
            existing_ticket.sentiment = analysis.sentiment.value
            existing_ticket.extracted_entities = analysis.entities.model_dump()
            existing_ticket.missing_entities = analysis.missing_entities
            existing_ticket.needs_clarification = analysis.needs_clarification
            existing_ticket.analysis_reason = analysis.reason
            existing_ticket.prompt_injection_detected = analysis.prompt_injection_detected
            existing_ticket.security_flags = analysis.security_flags
            existing_ticket.generated_response = auto_reply_response.suggested_reply
            existing_ticket.updated_at = now
            ticket_model = existing_ticket
        else:
            ticket_model = Ticket(
                ticket_id=req.ticket_id,
                customer_name=req.customer_name,
                customer_email=req.customer_email,
                subject=req.subject,
                original_message=req.message,
                category=analysis.category.value,
                secondary_categories=analysis.secondary_categories,
                priority=analysis.priority.value,
                sentiment=analysis.sentiment.value,
                extracted_entities=analysis.entities.model_dump(),
                missing_entities=analysis.missing_entities,
                needs_clarification=analysis.needs_clarification,
                analysis_reason=analysis.reason,
                prompt_injection_detected=analysis.prompt_injection_detected,
                security_flags=analysis.security_flags,
                generated_response=auto_reply_response.suggested_reply,
                edited_response=None,
                approval_status="pending",
                ticket_status="open",
                created_at=now,
                updated_at=now,
            )
            db.add(ticket_model)

        db.commit()
        db.refresh(ticket_model)

        db_response = TicketDBResponse.model_validate(ticket_model)

        return TicketProcessResult(
            ticket=db_response,
            analysis=analysis,
            auto_reply=auto_reply_response,
        )

    def list_tickets(
        self,
        db: Session,
        category: Optional[str] = None,
        priority: Optional[str] = None,
        ticket_status: Optional[str] = None,
        approval_status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[TicketDBResponse]:
        query = db.query(Ticket)
        if category:
            query = query.filter(Ticket.category == category)
        if priority:
            query = query.filter(Ticket.priority == priority)
        if ticket_status:
            query = query.filter(Ticket.ticket_status == ticket_status)
        if approval_status:
            query = query.filter(Ticket.approval_status == approval_status)

        records = query.order_by(Ticket.created_at.desc()).offset(offset).limit(limit).all()
        return [TicketDBResponse.model_validate(r) for r in records]

    def get_ticket(self, db: Session, ticket_id: str) -> Optional[TicketDBResponse]:
        record = db.query(Ticket).filter(Ticket.ticket_id == ticket_id).first()
        if not record:
            return None
        return TicketDBResponse.model_validate(record)

    def update_ticket(
        self, db: Session, ticket_id: str, updates: TicketDBUpdate
    ) -> Optional[TicketDBResponse]:
        record = db.query(Ticket).filter(Ticket.ticket_id == ticket_id).first()
        if not record:
            return None

        if updates.edited_response is not None:
            record.edited_response = updates.edited_response
        if updates.approval_status is not None:
            record.approval_status = updates.approval_status
        if updates.ticket_status is not None:
            record.ticket_status = updates.ticket_status
        if updates.priority is not None:
            record.priority = updates.priority

        record.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(record)
        return TicketDBResponse.model_validate(record)

    def get_dashboard_stats(self, db: Session) -> dict[str, Any]:
        """Compute actual real-time statistics from SQLite database."""
        all_tickets = db.query(Ticket).all()
        total = len(all_tickets)
        open_count = sum(1 for t in all_tickets if t.ticket_status == "open")
        pending_count = sum(1 for t in all_tickets if t.ticket_status == "pending" or t.approval_status == "pending")
        resolved_count = sum(1 for t in all_tickets if t.ticket_status in ["resolved", "closed"])
        high_priority_count = sum(1 for t in all_tickets if t.priority in ["high", "critical"])
        critical_count = sum(1 for t in all_tickets if t.priority == "critical")

        categories = {}
        for t in all_tickets:
            categories[t.category] = categories.get(t.category, 0) + 1

        sentiments = {}
        for t in all_tickets:
            sentiments[t.sentiment] = sentiments.get(t.sentiment, 0) + 1

        return {
            "total_tickets": total,
            "open_tickets": open_count,
            "pending_tickets": pending_count,
            "resolved_tickets": resolved_count,
            "high_priority_tickets": high_priority_count,
            "critical_tickets": critical_count,
            "category_breakdown": categories,
            "sentiment_breakdown": sentiments,
        }

    def regenerate_reply(self, db: Session, ticket_id: str) -> Optional[TicketDBResponse]:
        """Regenerate the policy-grounded draft response for an existing ticket."""
        ticket = db.query(Ticket).filter(Ticket.ticket_id == ticket_id).first()
        if not ticket:
            return None

        ingestion_req = TicketIngestionRequest(
            ticket_id=ticket.ticket_id,
            customer_name=ticket.customer_name,
            customer_email=ticket.customer_email,
            subject=ticket.subject,
            message=ticket.original_message,
        )
        analysis = analyzer_service.analyze_ticket(ingestion_req)
        draft = auto_reply_service.generate_draft(ingestion_req, analysis)

        ticket.generated_response = draft["suggested_reply"]
        ticket.edited_response = None  # Reset edited response so newly regenerated draft is active
        ticket.approval_status = "pending"  # Needs review again
        ticket.category = analysis.category.value
        ticket.secondary_categories = analysis.secondary_categories
        ticket.priority = analysis.priority.value
        ticket.sentiment = analysis.sentiment.value
        ticket.extracted_entities = analysis.entities.model_dump()
        ticket.missing_entities = analysis.missing_entities
        ticket.needs_clarification = analysis.needs_clarification
        ticket.analysis_reason = analysis.reason
        ticket.prompt_injection_detected = analysis.prompt_injection_detected
        ticket.security_flags = analysis.security_flags
        ticket.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(ticket)
        return TicketDBResponse.model_validate(ticket)

    def approve_ticket(
        self, db: Session, ticket_id: str, edited_response: Optional[str] = None
    ) -> Optional[TicketApprovalResponse]:
        """Approve and mock send auto-reply to customer."""
        record = db.query(Ticket).filter(Ticket.ticket_id == ticket_id).first()
        if not record:
            return None

        now = datetime.now(timezone.utc)
        if edited_response is not None:
            record.edited_response = edited_response

        record.approval_status = "approved"
        if record.ticket_status == "open":
            record.ticket_status = "in_progress"

        record.updated_at = now
        db.commit()
        db.refresh(record)

        final_reply = record.final_response
        mock_send = MockSendDetails(
            is_mock=True,
            recipient=record.customer_email,
            message=(
                f"MOCK SENDING NOTICE: No real email was sent. This is a demonstration project. "
                f"Approved response recorded for {record.customer_name} <{record.customer_email}>."
            ),
            sent_content=final_reply,
            sent_at=now,
        )

        return TicketApprovalResponse(
            ticket=TicketDBResponse.model_validate(record),
            mock_send=mock_send,
        )

    def resolve_ticket(self, db: Session, ticket_id: str) -> Optional[TicketResolutionResponse]:
        """Mark a ticket as resolved and update status in SQLite."""
        record = db.query(Ticket).filter(Ticket.ticket_id == ticket_id).first()
        if not record:
            return None

        now = datetime.now(timezone.utc)
        record.ticket_status = "resolved"
        record.updated_at = now
        db.commit()
        db.refresh(record)

        return TicketResolutionResponse(
            ticket=TicketDBResponse.model_validate(record),
            message=f"Ticket {ticket_id} successfully marked as resolved.",
        )

    def export_tickets_csv(
        self,
        db: Session,
        category: Optional[str] = None,
        priority: Optional[str] = None,
        ticket_status: Optional[str] = None,
        approval_status: Optional[str] = None,
    ) -> str:
        """Export tickets to CSV format containing exact required fields:
        - Ticket ID
        - Customer
        - Category
        - Priority
        - Sentiment
        - Missing entities
        - Status
        - Final response
        """
        query = db.query(Ticket)
        if category:
            query = query.filter(Ticket.category == category)
        if priority:
            query = query.filter(Ticket.priority == priority)
        if ticket_status:
            query = query.filter(Ticket.ticket_status == ticket_status)
        if approval_status:
            query = query.filter(Ticket.approval_status == approval_status)

        tickets = query.order_by(Ticket.created_at.desc()).all()

        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

        # Header row
        writer.writerow([
            "Ticket ID",
            "Customer",
            "Category",
            "Priority",
            "Sentiment",
            "Missing entities",
            "Status",
            "Final response",
        ])

        for t in tickets:
            missing_str = ", ".join(t.missing_entities) if t.missing_entities else "None"
            customer_str = f"{t.customer_name} <{t.customer_email}>"
            writer.writerow([
                t.ticket_id,
                customer_str,
                t.category,
                t.priority,
                t.sentiment,
                missing_str,
                t.ticket_status,
                t.final_response,
            ])

        return output.getvalue()

    def export_tickets_json(
        self,
        db: Session,
        category: Optional[str] = None,
        priority: Optional[str] = None,
        ticket_status: Optional[str] = None,
        approval_status: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Export tickets in complete JSON structure containing full analysis and response details."""
        query = db.query(Ticket)
        if category:
            query = query.filter(Ticket.category == category)
        if priority:
            query = query.filter(Ticket.priority == priority)
        if ticket_status:
            query = query.filter(Ticket.ticket_status == ticket_status)
        if approval_status:
            query = query.filter(Ticket.approval_status == approval_status)

        tickets = query.order_by(Ticket.created_at.desc()).all()

        export_list = []
        for t in tickets:
            export_list.append({
                "ticket_id": t.ticket_id,
                "customer": {
                    "name": t.customer_name,
                    "email": t.customer_email,
                },
                "customer_name": t.customer_name,
                "customer_email": t.customer_email,
                "subject": t.subject,
                "original_message": t.original_message,
                "category": t.category,
                "secondary_categories": t.secondary_categories or [],
                "priority": t.priority,
                "urgency_tier": t.urgency_tier,
                "sentiment": t.sentiment,
                "extracted_entities": t.extracted_entities or {},
                "missing_entities": t.missing_entities or [],
                "needs_clarification": bool(t.needs_clarification or (t.missing_entities and len(t.missing_entities) > 0)),
                "analysis_reason": t.analysis_reason,
                "prompt_injection_detected": bool(t.prompt_injection_detected),
                "security_flags": t.security_flags or [],
                "generated_response": t.generated_response,
                "edited_response": t.edited_response,
                "final_response": t.final_response,
                "approval_status": t.approval_status,
                "ticket_status": t.ticket_status,
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "updated_at": t.updated_at.isoformat() if t.updated_at else None,
                "analysis_details": {
                    "category": t.category,
                    "secondary_categories": t.secondary_categories or [],
                    "priority": t.priority,
                    "urgency_tier": t.urgency_tier,
                    "sentiment": t.sentiment,
                    "extracted_entities": t.extracted_entities or {},
                    "missing_entities": t.missing_entities or [],
                    "needs_clarification": bool(t.needs_clarification or (t.missing_entities and len(t.missing_entities) > 0)),
                    "reason": t.analysis_reason,
                    "prompt_injection_detected": bool(t.prompt_injection_detected),
                    "security_flags": t.security_flags or [],
                },
                "response_details": {
                    "generated_draft": t.generated_response,
                    "edited_draft": t.edited_response,
                    "final_response": t.final_response,
                    "approval_status": t.approval_status,
                    "ticket_status": t.ticket_status,
                },
            })

        return export_list

    def seed_sample_tickets(self, db: Session, samples_file: Path) -> list[TicketDBResponse]:
        """Seed initial realistic tickets into database if not present."""
        if not samples_file.exists():
            return []
        import json
        with open(samples_file, "r", encoding="utf-8") as f:
            samples = json.load(f)

        results = []
        for s in samples:
            req = TicketIngestionRequest(
                ticket_id=s["id"],
                customer_name=s["customer_name"],
                customer_email=s["customer_email"],
                subject=s["subject"],
                message=s["body"],
            )
            res = self.process_and_save_ticket(db, req)
            results.append(res.ticket)
        return results


ticket_db_service = TicketDatabaseService()
