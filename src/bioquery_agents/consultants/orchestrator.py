"""
Consultant orchestrator for managing domain expert invocations.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
from dataclasses import dataclass, field
from typing import Any

from .base import DomainConsultant
from .definitions import CONSULTANTS
from .schemas import ConsultationRequest, ConsultationResponse

logger = logging.getLogger(__name__)


@dataclass
class ConsultantOrchestrator:
    """
    Manages consultant invocations from the main query orchestrator.

    Features:
    - Parallel consultation for multiple experts
    - Result caching to avoid duplicate queries
    - Automatic consultant selection based on analysis type

    Example:
        ```python
        orchestrator = ConsultantOrchestrator()

        # Single consultation
        response = await orchestrator.consult(
            consultant_name="statistics",
            question="What test should I use?",
            context={"n_groups": 3, "n_samples": 50},
        )

        # Parallel consultation
        responses = await orchestrator.consult_parallel(
            consultant_names=["statistics", "clinical"],
            question="Reviewing survival analysis",
            context={"analysis_type": "survival"},
        )
        ```
    """

    consultants: dict[str, DomainConsultant] = field(default_factory=lambda: CONSULTANTS.copy())
    cache: dict[str, ConsultationResponse] = field(default_factory=dict)
    cache_enabled: bool = True

    async def consult(
        self,
        consultant_name: str,
        question: str,
        context: dict[str, Any],
        urgency: str = "normal",
    ) -> ConsultationResponse | None:
        """
        Consult a single expert.

        Args:
            consultant_name: Name of consultant (statistics, clinical, immunology, genomics)
            question: The question to ask
            context: Analysis context
            urgency: quick | normal | thorough

        Returns:
            ConsultationResponse or None if consultant not found
        """
        consultant = self.consultants.get(consultant_name)
        if not consultant:
            logger.warning(f"Unknown consultant: {consultant_name}")
            return None

        request = ConsultationRequest(
            question=question,
            context=context,
            urgency=urgency,  # type: ignore[arg-type]
        )

        # Check cache
        if self.cache_enabled:
            cache_key = self._cache_key(consultant_name, request)
            if cache_key in self.cache:
                logger.debug(f"Cache hit for {consultant_name}")
                return self.cache[cache_key]

        # Perform consultation
        response = await consultant.consult(request)

        # Cache result
        if self.cache_enabled:
            self.cache[cache_key] = response

        return response

    async def consult_parallel(
        self,
        consultant_names: list[str],
        question: str,
        context: dict[str, Any],
        urgency: str = "normal",
    ) -> dict[str, ConsultationResponse]:
        """
        Consult multiple experts in parallel.

        Args:
            consultant_names: List of consultant names
            question: The question to ask (all get same question)
            context: Analysis context
            urgency: quick | normal | thorough

        Returns:
            Dict mapping consultant name to response
        """
        # Filter to valid consultants
        valid_names = [name for name in consultant_names if name in self.consultants]

        if not valid_names:
            return {}

        tasks = [self.consult(name, question, context, urgency) for name in valid_names]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        return {
            name: result
            for name, result in zip(valid_names, results, strict=True)
            if isinstance(result, ConsultationResponse)
        }

    def should_consult(
        self,
        analysis_type: str,
        context: dict[str, Any],
    ) -> list[str]:
        """
        Determine which consultants to invoke based on analysis type and context.

        This provides automatic consultation routing based on heuristics.

        Args:
            analysis_type: The analysis being performed
            context: Query context (may include genes, cancer types, etc.)

        Returns:
            List of recommended consultant names
        """
        recommendations: list[str] = []
        context_str = str(context).lower()

        # Statistical consultation triggers
        stats_analyses = {
            "differential_expression",
            "survival_analysis",
            "gene_correlation",
            "signature_comparison",
            "pan_cancer_expression",
        }
        if analysis_type in stats_analyses:
            recommendations.append("statistics")

        # Multi-group comparison triggers stats
        groups = context.get("groups", [])
        if isinstance(groups, list) and len(groups) > 2 and "statistics" not in recommendations:
            recommendations.append("statistics")

        # Clinical consultation triggers
        clinical_analyses = {"survival_analysis"}
        clinical_keywords = {"stage", "treatment", "therapy", "prognosis", "grade"}
        if (
            analysis_type in clinical_analyses or any(kw in context_str for kw in clinical_keywords)
        ) and "clinical" not in recommendations:
            recommendations.append("clinical")

        # Immunology consultation triggers
        immune_keywords = {
            "immune",
            "checkpoint",
            "pd-1",
            "pd-l1",
            "ctla",
            "infiltration",
            "tide",
            "tme",
            "microenvironment",
            "cd8",
            "treg",
            "myeloid",
            "ici",
            "immunotherapy",
        }
        if any(kw in context_str for kw in immune_keywords) and "immunology" not in recommendations:
            recommendations.append("immunology")

        # iAtlas ICI data always gets immunology + clinical
        if "iatlas" in context_str or "ici" in context_str:
            if "immunology" not in recommendations:
                recommendations.append("immunology")
            if "clinical" not in recommendations:
                recommendations.append("clinical")

        # Genomics consultation triggers
        genomics_analyses = {"scientific_context", "mutation_frequency"}
        genomics_keywords = {"pathway", "function", "driver", "oncogene", "suppressor"}
        if (
            analysis_type in genomics_analyses or any(kw in context_str for kw in genomics_keywords)
        ) and "genomics" not in recommendations:
            recommendations.append("genomics")

        return recommendations

    def synthesize_responses(
        self,
        responses: dict[str, ConsultationResponse],
    ) -> str:
        """
        Synthesize multiple consultant responses into a unified summary.

        Args:
            responses: Dict of consultant name to response

        Returns:
            Synthesized summary string
        """
        if not responses:
            return ""

        if len(responses) == 1:
            resp = list(responses.values())[0]
            return f"**{resp.consultant}**: {resp.answer}"

        # Multiple responses - format each
        parts = []
        caveats_all: list[str] = []

        for name, resp in responses.items():
            confidence_pct = f"{resp.confidence:.0%}"
            parts.append(f"**{name}** (confidence: {confidence_pct}): {resp.answer}")
            caveats_all.extend(resp.caveats)

        synthesis = "\n\n".join(parts)

        if caveats_all:
            unique_caveats = list(dict.fromkeys(caveats_all))[:3]  # Top 3 unique
            synthesis += "\n\n**Caveats**: " + "; ".join(unique_caveats)

        return synthesis

    def _cache_key(self, consultant_name: str, request: ConsultationRequest) -> str:
        """Generate cache key for a consultation."""
        content = f"{consultant_name}:{request.question}:{hash(str(request.context))}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def clear_cache(self) -> None:
        """Clear the consultation cache."""
        self.cache.clear()


# Default global instance
_orchestrator: ConsultantOrchestrator | None = None


def get_orchestrator() -> ConsultantOrchestrator:
    """Get or create the global consultant orchestrator."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = ConsultantOrchestrator()
    return _orchestrator


def reset_orchestrator() -> None:
    """Reset the global orchestrator (useful for testing)."""
    global _orchestrator
    _orchestrator = None
