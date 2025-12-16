"""
Data models for consultant requests and responses.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class ConsultationRequest:
    """Request to a domain consultant."""

    question: str
    context: dict[str, Any] = field(default_factory=dict)
    urgency: Literal["quick", "normal", "thorough"] = "normal"


@dataclass
class ConsultationResponse:
    """Response from a domain consultant."""

    consultant: str
    answer: str
    confidence: float  # 0.0 to 1.0
    reasoning: str
    caveats: list[str] = field(default_factory=list)
    recommend_other: list[str] = field(default_factory=list)


# JSON schema for structured output (used with Anthropic API)
CONSULTATION_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {
            "type": "string",
            "description": "Expert guidance addressing the question",
        },
        "confidence": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
            "description": "Confidence in the answer (0.0 to 1.0)",
        },
        "reasoning": {
            "type": "string",
            "description": "Brief explanation of the reasoning",
        },
        "caveats": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Important limitations or assumptions",
        },
        "recommend_other_consultants": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Other consultants that might provide useful input",
        },
    },
    "required": ["answer", "confidence", "reasoning", "caveats"],
}
