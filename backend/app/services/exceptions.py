"""Custom sanitized exceptions for AI and Groq API integrations."""
import json
import re
from typing import Optional
import groq
from pydantic import ValidationError


def sanitize_error_message(message: str) -> str:
    """Scrub potential API keys, bearer tokens, and secrets from error text."""
    if not message:
        return "An unexpected error occurred."

    sanitized = str(message)
    # Redact Groq API keys (gsk_...)
    sanitized = re.sub(r"gsk_[A-Za-z0-9_-]{8,}", "[REDACTED_API_KEY]", sanitized)
    # Redact OpenAI/generic sk_ keys
    sanitized = re.sub(r"sk-[A-Za-z0-9_-]{8,}", "[REDACTED_API_KEY]", sanitized)
    # Redact Bearer tokens
    sanitized = re.sub(r"Bearer\s+[A-Za-z0-9._-]+", "Bearer [REDACTED]", sanitized, flags=re.IGNORECASE)
    # Redact key=value pairs
    sanitized = re.sub(
        r"(api[_-]?key|authorization|secret|token|password)\s*[:=]\s*['\"]?[^\s'\"]+['\"]?",
        r"\1=[REDACTED]",
        sanitized,
        flags=re.IGNORECASE,
    )
    return sanitized


class AIServiceError(Exception):
    """Base exception for sanitized AI service failures."""

    def __init__(
        self,
        user_message: str,
        error_code: str = "AI_SERVICE_ERROR",
        status_code: int = 502,
        internal_detail: Optional[str] = None,
    ):
        self.user_message = sanitize_error_message(user_message)
        self.error_code = error_code
        self.status_code = status_code
        self.internal_detail = sanitize_error_message(internal_detail or user_message)
        super().__init__(self.user_message)


class MissingAPIKeyError(AIServiceError):
    """Raised when GROQ_API_KEY is missing or unconfigured."""

    def __init__(self, detail: Optional[str] = None):
        super().__init__(
            user_message=(
                "AI service is not configured: the Groq API key is missing. "
                "Please set a valid GROQ_API_KEY in backend/.env."
            ),
            error_code="MISSING_API_KEY",
            status_code=503,
            internal_detail=detail,
        )


class AIAuthenticationError(AIServiceError):
    """Raised when the Groq API key is invalid or rejected by authentication."""

    def __init__(self, detail: Optional[str] = None):
        super().__init__(
            user_message=(
                "AI authentication failed: the configured Groq API key is invalid, "
                "revoked, or lacks permission. Please verify your API key."
            ),
            error_code="AUTHENTICATION_FAILED",
            status_code=401,
            internal_detail=detail,
        )


class AIRateLimitError(AIServiceError):
    """Raised when Groq API rate limits or quotas are exceeded."""

    def __init__(self, detail: Optional[str] = None):
        super().__init__(
            user_message=(
                "AI service rate limit exceeded. Please wait a brief moment and try again."
            ),
            error_code="RATE_LIMIT_EXCEEDED",
            status_code=429,
            internal_detail=detail,
        )


class AINetworkError(AIServiceError):
    """Raised when network connectivity or timeout prevents reaching Groq."""

    def __init__(self, detail: Optional[str] = None):
        super().__init__(
            user_message=(
                "Network connection to the AI service failed or timed out. "
                "Please check your internet connection and retry."
            ),
            error_code="NETWORK_CONNECTION_ERROR",
            status_code=503,
            internal_detail=detail,
        )


class AIModelResponseError(AIServiceError):
    """Raised when the Groq model or upstream API returns an error response."""

    def __init__(self, detail: Optional[str] = None):
        super().__init__(
            user_message=(
                "The AI model returned an error response while processing this ticket. "
                "Please try again shortly."
            ),
            error_code="MODEL_API_ERROR",
            status_code=502,
            internal_detail=detail,
        )


class AIInvalidJSONError(AIServiceError):
    """Raised when the AI model outputs invalid or unparseable JSON."""

    def __init__(self, detail: Optional[str] = None):
        super().__init__(
            user_message=(
                "The AI model returned an invalid JSON response format that could not be processed. "
                "Please retry generating the analysis."
            ),
            error_code="INVALID_MODEL_JSON",
            status_code=502,
            internal_detail=detail,
        )


def classify_groq_exception(exc: Exception) -> AIServiceError:
    """Convert raw Groq SDK, network, or JSON exceptions into safe AIServiceError instances."""
    if isinstance(exc, AIServiceError):
        return exc

    raw_str = str(exc)
    lower = raw_str.lower()

    if isinstance(exc, groq.AuthenticationError) or "401" in lower or "invalid api key" in lower or "authentication" in lower:
        return AIAuthenticationError(detail=raw_str)

    if isinstance(exc, groq.RateLimitError) or "429" in lower or "rate limit" in lower or "quota" in lower:
        return AIRateLimitError(detail=raw_str)

    if isinstance(exc, (groq.APIConnectionError, groq.APITimeoutError, ConnectionError, TimeoutError, OSError)):
        return AINetworkError(detail=raw_str)

    if isinstance(exc, (json.JSONDecodeError, ValidationError)):
        return AIInvalidJSONError(detail=raw_str)

    if isinstance(exc, (groq.APIStatusError, groq.APIError)):
        status_code = getattr(exc, "status_code", None)
        if status_code == 401 or status_code == 403:
            return AIAuthenticationError(detail=raw_str)
        if status_code == 429:
            return AIRateLimitError(detail=raw_str)
        if status_code and status_code >= 500:
            return AIModelResponseError(detail=raw_str)
        return AIModelResponseError(detail=raw_str)

    if "connection" in lower or "network" in lower or "dns" in lower or "timed out" in lower:
        return AINetworkError(detail=raw_str)

    return AIModelResponseError(detail=raw_str)


def is_api_key_configured(api_key: Optional[str]) -> bool:
    """Check whether an API key is present and non-placeholder."""
    if not api_key:
        return False
    cleaned = api_key.strip()
    if not cleaned:
        return False
    placeholders = {
        "your-groq-api-key-here",
        "your_groq_api_key",
        "changeme",
        "replace_me",
        "none",
        "null",
    }
    if cleaned.lower() in placeholders:
        return False
    return True

