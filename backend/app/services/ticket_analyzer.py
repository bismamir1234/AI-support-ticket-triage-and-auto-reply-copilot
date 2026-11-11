import json
import logging
import os
import re
from typing import Any, Optional
from groq import Groq
from app.config import settings
from app.schemas import (
    ExtractedEntities,
    TicketAnalysisResponse,
    TicketCategory,
    TicketIngestionRequest,
    TicketPriority,
    TicketSentiment,
)

logger = logging.getLogger(__name__)


def extract_order_id_from_text(text: str) -> Optional[str]:
    """Extract realistic order IDs containing numbers from text."""
    patterns = [
        r"\b(ORD-[0-9A-Za-z-]+)\b",
        r"#\s*([0-9]{4,10})\b",
        r"\border\s*(?:id|number|no\.?|#)?\s*[:#-]?\s*([0-9A-Za-z-]*\d+[0-9A-Za-z-]*)\b",
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            val = m.group(1).strip()
            if any(ch.isdigit() for ch in val) and len(val) >= 3:
                return val
    return None


class TicketAnalyzerService:
    """AI Support Ticket Triage and Analysis Engine using Groq with deterministic fallbacks."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.GROQ_API_KEY
        self.model = model or settings.GROQ_MODEL
        self._client: Optional[Groq] = None

    @property
    def client(self) -> Optional[Groq]:
        if self._client is None and self.api_key:
            try:
                self._client = Groq(api_key=self.api_key)
            except Exception as e:
                logger.error(f"Failed to initialize Groq client: {e}")
                self._client = None
        return self._client

    def analyze_ticket(self, ticket: TicketIngestionRequest) -> TicketAnalysisResponse:
        """Run the complete ticket analysis pipeline with LLM and validation layers."""
        # 1. Try Groq AI analysis
        ai_result = None
        if self.client:
            try:
                ai_result = self._call_groq_llm(ticket)
            except Exception as e:
                logger.warning(f"Groq API call failed or encountered error: {e}. Falling back to rule engine.")
                ai_result = None

        # 2. If AI call failed, use robust rule-based fallback
        if not ai_result:
            ai_result = self._rule_based_fallback(ticket)

        # 3. Post-process and apply strict business policy enforcement
        final_response = self._enforce_business_policies(ticket, ai_result)
        return final_response

    def _call_groq_llm(self, ticket: TicketIngestionRequest) -> Optional[dict[str, Any]]:
        """Call Groq API with JSON schema enforcement."""
        prompt = f"""You are an expert customer support ticket classification and entity extraction system.
Analyze the following customer support ticket and output STRICT JSON only.

TICKET TO ANALYZE:
- Ticket ID: {ticket.ticket_id}
- Customer Name: {ticket.customer_name}
- Customer Email: {ticket.customer_email}
- Subject: {ticket.subject}
- Customer Message: {ticket.message}

TAXONOMY & GUIDELINES:
1. CATEGORY (must be strictly one of):
   - "order_issue": shipping delays, missing parcels, tracking inquiries, delivery status, damaged packages.
   - "refund": return requests, refund processing, billing disputes, money back, cancellations.
   - "technical_issue": website errors, 500/404 errors, checkout crashes, login failures, payment processing failures, bugs.
   - "general_inquiry": product details, business hours, company information, general questions, feedback.

2. PRIORITY (must be strictly one of):
   - "critical": complete checkout failure, payment outage, site-wide downtime, urgent security issue.
   - "high": time-sensitive refunds, significant payment errors, customer completely blocked, urgent escalation.
   - "medium": standard shipping delay, non-blocking bug with workaround, order update request.
   - "low": general questions, store hours, general product information.

3. SENTIMENT (must be strictly one of):
   - "Positive": customer expresses gratitude, praise, thanks, or satisfaction (e.g. "thank you", "great support", "excellent").
   - "Neutral": calm, matter-of-fact inquiry without emotional stress or panic.
   - "Frustrated": customer expresses irritation, dissatisfaction, or complaints about delays (e.g. "has not arrived", "still waiting", "broken").
   - "Highly Urgent": customer explicitly expresses time-critical pressure, panic, immediate need, or deadlines (e.g. "urgently need access", "emergency", "ASAP", "immediately"). Whenever the customer explicitly says "urgently" or "immediate need", choose "Highly Urgent".
   NOTE: Keep sentiment separate from priority!

4. ENTITY EXTRACTION:
   - order_id: explicit order ID (e.g. ORD-88231, 90412, or null if not found).
   - account_email: explicit email mentioned in the body (or null if not mentioned).
   - error_code: specific error code or HTTP status (e.g. "500", "404", "ERR_CONNECTION_REFUSED", or null).
   - date: specific date mentioned (e.g. "November 4th", "November 2nd", or null).

5. MISSING ENTITIES & CLARIFICATION:
   - Mandatory rules:
     * If category is "order_issue" and order_id is null: "order_id" MUST be in missing_entities, needs_clarification MUST be true, reason MUST explain order number is required.
     * If category is "refund" and order_id is null: "order_id" MUST be in missing_entities, needs_clarification MUST be true, reason MUST explain order number is required.
     * If category is "technical_issue" and customer describes an error but omitted error code or reproduction steps: error_code can be optional unless required for that specific investigation.
     * If all mandatory entities are present: missing_entities MUST be [], needs_clarification MUST be false, reason MUST be null.

REQUIRED JSON FORMAT:
{{
  "ticket_id": "{ticket.ticket_id}",
  "category": "order_issue",
  "priority": "high",
  "sentiment": "Frustrated",
  "entities": {{
    "order_id": null,
    "account_email": null,
    "error_code": null,
    "date": null
  }},
  "missing_entities": ["order_id"],
  "needs_clarification": true,
  "reason": "Order number is missing."
}}
"""

        last_error = None
        for attempt in range(2):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a senior automated support triage engine. Output valid JSON only."},
                        {"role": "user", "content": prompt},
                    ],
                    response_format={"type": "json_object"},
                    max_tokens=800,
                    temperature=0.0,
                )

                content = response.choices[0].message.content or ""
                # Clean any accidental markdown code fence
                cleaned = re.sub(r"^```(?:json)?\s*", "", content.strip(), flags=re.MULTILINE)
                cleaned = re.sub(r"```$", "", cleaned.strip(), flags=re.MULTILINE)
                
                parsed = json.loads(cleaned)
                return parsed
            except Exception as e:
                last_error = e
                logger.warning(f"Groq completion attempt {attempt + 1} failed: {e}")

        raise last_error

    def _rule_based_fallback(self, ticket: TicketIngestionRequest) -> dict[str, Any]:
        """Deterministic rule-based classification and entity extraction fallback."""
        text = f"{ticket.subject} {ticket.message}".lower()
        full_text = f"{ticket.subject} {ticket.message}"

        # 1. Entity Extraction via Regex
        order_id = extract_order_id_from_text(full_text)

        email_match = re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", full_text)
        account_email = email_match.group(0) if email_match else None

        error_match = re.search(r"(?:code:\s*|error\s+code:\s*|error\s+|status\s+)(\d{3}|ERR_[A-Z_]+)\b", full_text, re.IGNORECASE)
        error_code = error_match.group(1) if error_match else None

        date_match = re.search(
            r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2}(?:st|nd|rd|th)?\b|\b\d{4}-\d{2}-\d{2}\b",
            full_text,
            re.IGNORECASE,
        )
        date_str = date_match.group(0) if date_match else None

        # 2. Category Detection
        if any(w in text for w in ["refund", "return", "money back", "charge back", "credit card return"]):
            category = "refund"
        elif any(w in text for w in ["order", "package", "delivery", "shipping", "fedex", "ups", "tracking", "stuck in transit"]):
            category = "order_issue"
        elif any(w in text for w in ["error", "bug", "crash", "code: 500", "500", "failed request", "endpoint", "checkout page", "cannot login"]):
            category = "technical_issue"
        else:
            category = "general_inquiry"

        # 3. Sentiment Detection
        if any(w in text for w in ["urgent", "immediately", "asap", "emergency", "critical", "blocking"]):
            sentiment = "Highly Urgent"
        elif any(w in text for w in ["frustrated", "angry", "terrible", "stuck", "ridiculous", "unacceptable", "disappointed"]):
            sentiment = "Frustrated"
        elif any(w in text for w in ["thank", "thanks", "great", "appreciate", "kindly"]):
            sentiment = "Positive"
        else:
            sentiment = "Neutral"

        # 4. Priority Detection
        if category == "technical_issue" and any(w in text for w in ["500", "checkout", "place order", "payment", "down", "outage"]):
            priority = "critical"
        elif category == "refund" or "immediately" in text or "urgent" in text:
            priority = "high"
        elif category == "order_issue":
            priority = "medium"
        else:
            priority = "low"

        # 5. Missing Entities & Clarification
        missing_entities = []
        needs_clarification = False
        reason = None

        if category in ["order_issue", "refund"] and not order_id:
            missing_entities.append("order_id")
            needs_clarification = True
            reason = "Order number is missing."

        return {
            "ticket_id": ticket.ticket_id,
            "category": category,
            "priority": priority,
            "sentiment": sentiment,
            "entities": {
                "order_id": order_id,
                "account_email": account_email,
                "error_code": error_code,
                "date": date_str,
            },
            "missing_entities": missing_entities,
            "needs_clarification": needs_clarification,
            "reason": reason,
        }

    def _enforce_business_policies(
        self, ticket: TicketIngestionRequest, raw_data: dict[str, Any]
    ) -> TicketAnalysisResponse:
        """Validate with Pydantic and apply business policy guardrails."""
        # Normalize and instantiate Pydantic model
        validated = TicketAnalysisResponse.model_validate(raw_data)

        # Re-check entity extraction from raw text if LLM missed obvious patterns
        full_text = f"{ticket.subject} {ticket.message}"
        if not validated.entities.order_id:
            extracted_ord = extract_order_id_from_text(full_text)
            if extracted_ord:
                validated.entities.order_id = extracted_ord

        if not validated.entities.error_code:
            error_match = re.search(r"(?:code:\s*|error\s+code:\s*|error\s+|status\s+)(\d{3}|ERR_[A-Z_]+)\b", full_text, re.IGNORECASE)
            if error_match:
                validated.entities.error_code = error_match.group(1).strip()

        if not validated.entities.date:
            date_match = re.search(
                r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2}(?:st|nd|rd|th)?\b|\b\d{4}-\d{2}-\d{2}\b",
                full_text,
                re.IGNORECASE,
            )
            if date_match:
                validated.entities.date = date_match.group(0).strip()

        # Sentiment guardrail for explicit urgency cues
        lower_text = full_text.lower()
        if any(term in lower_text for term in ["urgently", "urgent need", "immediately need", "emergency"]) and validated.sentiment != TicketSentiment.POSITIVE:
            validated.sentiment = TicketSentiment.HIGHLY_URGENT

        # Enforce Missing Entities Rules:
        # If order_issue or refund and order_id is missing -> mandatory clarification
        if validated.category in [TicketCategory.ORDER_ISSUE, TicketCategory.REFUND]:
            if not validated.entities.order_id:
                if "order_id" not in validated.missing_entities:
                    validated.missing_entities.append("order_id")
                validated.needs_clarification = True
                if not validated.reason:
                    validated.reason = "Order number is missing."
            else:
                # If order_id is present, remove from missing_entities
                if "order_id" in validated.missing_entities:
                    validated.missing_entities.remove("order_id")
                if not validated.missing_entities:
                    validated.needs_clarification = False
                    validated.reason = None

        elif validated.category == TicketCategory.TECHNICAL_ISSUE:
            # For technical issues, error_code can be optional unless required for a particular investigation
            # If present, make sure it's not listed as missing
            if validated.entities.error_code and "error_code" in validated.missing_entities:
                validated.missing_entities.remove("error_code")
            if not validated.missing_entities:
                validated.needs_clarification = False
                validated.reason = None

        elif validated.category == TicketCategory.GENERAL_INQUIRY:
            if not validated.missing_entities:
                validated.needs_clarification = False
                validated.reason = None

        return validated


analyzer_service = TicketAnalyzerService()
