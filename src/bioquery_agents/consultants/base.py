"""
Base class for domain expert consultants.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from .schemas import ConsultationRequest, ConsultationResponse

logger = logging.getLogger(__name__)


@dataclass
class DomainConsultant:
    """
    Base class for domain expert consultants.

    Each consultant has a focused system prompt and uses Claude Haiku
    for fast, cheap consultations with prompt caching.

    Example:
        ```python
        consultant = DomainConsultant(
            name="Statistics Expert",
            expertise="Statistical test selection",
            system_prompt="You are a biostatistics expert...",
        )

        request = ConsultationRequest(
            question="What test should I use for comparing two groups?",
            context={"n_samples": 50, "groups": 2},
        )

        response = await consultant.consult(request)
        print(response.answer)
        ```
    """

    name: str
    expertise: str
    system_prompt: str
    model: Optional[str] = None
    max_tokens: int = 1024
    _client: Any = field(default=None, repr=False)

    def __post_init__(self) -> None:
        """Initialize the Anthropic client lazily."""
        if self.model is None:
            self.model = "claude-haiku-4-20250514"


    @property
    def client(self) -> Any:
        """Get or create the Anthropic client."""
        if self._client is None:
            try:
                import anthropic

                self._client = anthropic.AsyncAnthropic()
            except ImportError as err:
                raise ImportError(
                    "anthropic package required for consultants. "
                    "Install with: pip install anthropic"
                ) from err
        return self._client

    async def consult(self, request: ConsultationRequest) -> ConsultationResponse:
        """
        Perform consultation with prompt caching and structured output.

        Args:
            request: ConsultationRequest with question and context

        Returns:
            ConsultationResponse with expert guidance
        """
        logger.debug(f"Consulting {self.name}: {request.question[:100]}...")

        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=[
                    {
                        "type": "text",
                        "text": self.system_prompt,
                        "cache_control": {"type": "ephemeral"},  # Cache system prompt
                    }
                ],
                messages=[{"role": "user", "content": self._format_question(request)}],
            )

            return self._parse_response(response.content[0].text)

        except Exception as e:
            logger.error(f"Consultation failed for {self.name}: {e}")
            return ConsultationResponse(
                consultant=self.name,
                answer=f"Consultation failed: {e!s}",
                confidence=0.0,
                reasoning="Error during consultation",
                caveats=["Consultation failed - proceed with caution"],
                recommend_other=[],
            )

    def _format_question(self, request: ConsultationRequest) -> str:
        """Format the consultation question with context."""
        context_str = json.dumps(request.context, indent=2, default=str)

        urgency_instruction = {
            "quick": "Provide a brief, direct answer (1-2 sentences).",
            "normal": "Provide a clear answer with key reasoning.",
            "thorough": "Provide a comprehensive answer with full reasoning.",
        }.get(request.urgency, "")

        return f"""## Analysis Context
```json
{context_str}
```

## Question
{request.question}

{urgency_instruction}

Respond as JSON with: answer, confidence (0-1), reasoning, caveats (list), recommend_other_consultants (list)."""

    def _parse_response(self, text: str) -> ConsultationResponse:
        """Parse the consultation response."""
        try:
            # Try to extract JSON from response
            if "```json" in text:
                json_str = text.split("```json")[1].split("```")[0]
            elif "{" in text:
                # Find JSON object
                start = text.index("{")
                end = text.rindex("}") + 1
                json_str = text[start:end]
            else:
                raise ValueError("No JSON found in response")

            data = json.loads(json_str)

            return ConsultationResponse(
                consultant=self.name,
                answer=data.get("answer", text),
                confidence=float(data.get("confidence", 0.5)),
                reasoning=data.get("reasoning", ""),
                caveats=data.get("caveats", []),
                recommend_other=data.get("recommend_other_consultants", []),
            )
        except (json.JSONDecodeError, ValueError, IndexError) as e:
            logger.warning(f"Failed to parse JSON response from {self.name}: {e}")
            # Fallback to raw text
            return ConsultationResponse(
                consultant=self.name,
                answer=text,
                confidence=0.5,
                reasoning="Response not in expected format",
                caveats=["Response parsing failed"],
                recommend_other=[],
            )
