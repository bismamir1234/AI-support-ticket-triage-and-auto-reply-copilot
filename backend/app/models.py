from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, String, Text, DateTime, JSON
from app.database import Base


class Ticket(Base):
    __tablename__ = "tickets"

    # Primary Identifier
    ticket_id = Column(String(100), primary_key=True, index=True)

    # Customer Information
    customer_name = Column(String(255), nullable=False)
    customer_email = Column(String(255), nullable=False, index=True)

    # Ticket Content
    subject = Column(String(500), nullable=False)
    original_message = Column(Text, nullable=False)

    # Classification & Analysis
    category = Column(String(100), nullable=False, index=True)
    secondary_categories = Column(JSON, nullable=True, default=list)
    priority = Column(String(50), nullable=False, default="medium")
    sentiment = Column(String(50), nullable=False, default="Neutral")

    # Entities & Clarification
    extracted_entities = Column(JSON, nullable=True, default=dict)
    missing_entities = Column(JSON, nullable=True, default=list)
    needs_clarification = Column(Boolean, nullable=False, default=False)
    analysis_reason = Column(Text, nullable=True)

    # Security Guardrails
    prompt_injection_detected = Column(Boolean, nullable=False, default=False)
    security_flags = Column(JSON, nullable=True, default=list)

    # Responses & Human-In-The-Loop Approval
    generated_response = Column(Text, nullable=True)
    edited_response = Column(Text, nullable=True)
    approval_status = Column(String(50), nullable=False, default="pending")  # pending, approved, rejected
    ticket_status = Column(String(50), nullable=False, default="open")       # open, in_progress, resolved, closed

    # Metadata & Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Compatibility properties for backward interoperability
    @property
    def id(self):
        return self.ticket_id

    @property
    def body(self):
        return self.original_message

    @property
    def status(self):
        return self.ticket_status

    @property
    def ai_suggested_reply(self):
        return self.generated_response

    @property
    def final_response(self):
        return self.edited_response if self.edited_response else (self.generated_response or "")

    @property
    def urgency_tier(self) -> str:
        prio = (self.priority or "medium").lower()
        if prio in ("critical", "high"):
            return "P1"
        if prio == "medium":
            return "P2"
        return "P3"
