"""
Agentic Consultants for domain expertise.

Lightweight domain expert agents that provide guidance without taking over execution.

Example:
    ```python
    from bioquery_agents.consultants import get_orchestrator

    orchestrator = get_orchestrator()

    # Single consultation
    response = await orchestrator.consult(
        consultant_name="statistics",
        question="What test should I use for comparing two groups?",
        context={"n_samples": 50, "groups": 2},
    )
    print(response.answer)

    # Parallel consultation
    responses = await orchestrator.consult_parallel(
        consultant_names=["statistics", "clinical"],
        question="Reviewing survival analysis results",
        context={"analysis_type": "survival"},
    )
    synthesis = orchestrator.synthesize_responses(responses)
    ```
"""

from .base import DomainConsultant
from .definitions import (
    BIOSTATISTICS_CONSULTANT,
    CLINICAL_ONCOLOGY_CONSULTANT,
    CONSULTANTS,
    GENOMICS_CONSULTANT,
    IMMUNOLOGY_CONSULTANT,
    get_consultant,
    list_consultants,
)
from .orchestrator import (
    ConsultantOrchestrator,
    get_orchestrator,
    reset_orchestrator,
)
from .schemas import (
    CONSULTATION_RESPONSE_SCHEMA,
    ConsultationRequest,
    ConsultationResponse,
)
from .tool import CONSULT_EXPERT_TOOL, execute_consult_expert

__all__ = [
    # Base
    "DomainConsultant",
    # Definitions
    "BIOSTATISTICS_CONSULTANT",
    "CLINICAL_ONCOLOGY_CONSULTANT",
    "IMMUNOLOGY_CONSULTANT",
    "GENOMICS_CONSULTANT",
    "CONSULTANTS",
    "get_consultant",
    "list_consultants",
    # Orchestrator
    "ConsultantOrchestrator",
    "get_orchestrator",
    "reset_orchestrator",
    # Schemas
    "ConsultationRequest",
    "ConsultationResponse",
    "CONSULTATION_RESPONSE_SCHEMA",
    # Tool
    "CONSULT_EXPERT_TOOL",
    "execute_consult_expert",
]
