from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class HealthResponse(BaseModel):
    status: str = "ok"
    app_name: str
    environment: str
    version: str


class PolicySchema(BaseModel):
    id: str
    name: str
    category: str
    description: str
    default_priority: str
    sla_hours: int
    eligibility_and_rules: list[str]
    required_customer_info: list[str]
    resolution_actions: list[str]
    auto_reply_guidelines: str


# ==========================================================
# Phase 2: Classification, Sentiment, Entity Models
# ==========================================================

class TicketCategory(str, Enum):
    ORDER_ISSUE = "order_issue"
    REFUND = "refund"
    TECHNICAL_ISSUE = "technical_issue"
    GENERAL_INQUIRY = "general_inquiry"


class TicketPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TicketSentiment(str, Enum):
    POSITIVE = "Positive"
    NEUTRAL = "Neutral"
    FRUSTRATED = "Frustrated"
    HIGHLY_URGENT = "Highly Urgent"


class ExtractedEntities(BaseModel):
    order_id: Optional[str] = None
    account_email: Optional[str] = None
    error_code: Optional[str] = None
    date: Optional[str] = None


class TicketIngestionRequest(BaseModel):
    ticket_id: str = Field(..., description="Unique ticket identifier (e.g. T001, TCK-1001)")
    customer_name: str = Field(..., description="Name of the customer")
    customer_email: str = Field(..., description="Customer contact email")
    subject: str = Field(..., description="Ticket subject line")
    message: str = Field(..., description="Raw customer message content")

    @model_validator(mode="before")
    @classmethod
    def populate_message_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Allow body, raw_message, or raw_customer_message aliases
            if "message" not in data or not data["message"]:
                for alias in ["body", "raw_message", "raw_customer_message", "content", "original_message"]:
                    if alias in data and data[alias]:
                        data["message"] = data[alias]
                        break
        return data


class TicketAnalysisResponse(BaseModel):
    ticket_id: str
    category: TicketCategory
    priority: TicketPriority
    sentiment: TicketSentiment
    entities: ExtractedEntities
    missing_entities: list[str] = Field(default_factory=list)
    needs_clarification: bool = False
    reason: Optional[str] = None

    @field_validator("category", mode="before")
    @classmethod
    def normalize_category(cls, v: Any) -> TicketCategory:
        if isinstance(v, TicketCategory):
            return v
        s = str(v).lower().strip().replace(" ", "_").replace("-", "_")
        if "order" in s or "delivery" in s or "shipping" in s:
            return TicketCategory.ORDER_ISSUE
        if "refund" in s or "return" in s or "charge" in s or "money_back" in s:
            return TicketCategory.REFUND
        if "tech" in s or "bug" in s or "error" in s or "crash" in s or "code" in s:
            return TicketCategory.TECHNICAL_ISSUE
        if "general" in s or "inquiry" in s or "question" in s or "info" in s:
            return TicketCategory.GENERAL_INQUIRY
        return TicketCategory.GENERAL_INQUIRY

    @field_validator("priority", mode="before")
    @classmethod
    def normalize_priority(cls, v: Any) -> TicketPriority:
        if isinstance(v, TicketPriority):
            return v
        s = str(v).lower().strip()
        if "crit" in s:
            return TicketPriority.CRITICAL
        if "high" in s:
            return TicketPriority.HIGH
        if "med" in s:
            return TicketPriority.MEDIUM
        if "low" in s:
            return TicketPriority.LOW
        return TicketPriority.MEDIUM

    @field_validator("sentiment", mode="before")
    @classmethod
    def normalize_sentiment(cls, v: Any) -> TicketSentiment:
        if isinstance(v, TicketSentiment):
            return v
        s = str(v).lower().strip()
        if "urgent" in s or "panic" in s or "emergency" in s:
            return TicketSentiment.HIGHLY_URGENT
        if "frustrat" in s or "angry" in s or "upset" in s or "mad" in s or "annoy" in s:
            return TicketSentiment.FRUSTRATED
        if "pos" in s or "happy" in s or "great" in s or "thank" in s:
            return TicketSentiment.POSITIVE
        return TicketSentiment.NEUTRAL

    @field_validator("entities", mode="before")
    @classmethod
    def normalize_entities(cls, v: Any) -> ExtractedEntities:
        if isinstance(v, ExtractedEntities):
            return v
        if isinstance(v, dict):
            return ExtractedEntities(
                order_id=v.get("order_id") or None,
                account_email=v.get("account_email") or None,
                error_code=v.get("error_code") or None,
                date=v.get("date") or None,
            )
        return ExtractedEntities()


# ==========================================================
# Phase 4: Policy Matching & Auto-Reply Schemas
# ==========================================================

class AutoReplyDraftResponse(BaseModel):
    ticket_id: str
    matched_policy_id: str
    policy_name: str
    suggested_reply: str
    action_items: list[str] = Field(default_factory=list)
    confidence_score: float = 0.95
    requires_human_review: bool = False
    clarification_requested: bool = False
    grounding_rules_checked: dict[str, bool] = Field(
        default_factory=lambda: {
            "no_invented_order_numbers": True,
            "no_guessed_account_status": True,
            "missing_order_requested": True,
            "no_unapproved_refund_promises": True,
            "no_invented_policies": True,
            "insufficient_info_clarified": True,
            "no_unverified_action_claims": True,
        }
    )


class TicketDBResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ticket_id: str
    customer_name: str
    customer_email: str
    subject: str
    original_message: str
    category: str
    priority: str
    sentiment: str
    extracted_entities: dict[str, Any] = Field(default_factory=dict)
    missing_entities: list[str] = Field(default_factory=list)
    generated_response: Optional[str] = None
    edited_response: Optional[str] = None
    final_response: Optional[str] = None
    approval_status: str = "pending"
    ticket_status: str = "open"
    created_at: datetime
    updated_at: datetime


class TicketDBUpdate(BaseModel):
    edited_response: Optional[str] = None
    approval_status: Optional[str] = None  # pending, approved, rejected
    ticket_status: Optional[str] = None    # open, in_progress, resolved, closed
    priority: Optional[str] = None


class TicketApproveRequest(BaseModel):
    edited_response: Optional[str] = None


class MockSendDetails(BaseModel):
    is_mock: bool = True
    recipient: str
    message: str
    sent_content: str
    sent_at: datetime


class TicketApprovalResponse(BaseModel):
    ticket: TicketDBResponse
    mock_send: MockSendDetails


class TicketResolutionResponse(BaseModel):
    ticket: TicketDBResponse
    message: str


class TicketProcessResult(BaseModel):
    ticket: TicketDBResponse
    analysis: TicketAnalysisResponse
    auto_reply: AutoReplyDraftResponse
