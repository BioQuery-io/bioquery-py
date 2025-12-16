"""
Tool definition for consult_expert, to be used by the main query orchestrator.
"""

from __future__ import annotations

from typing import Any

# Tool definition for Anthropic tool_use
CONSULT_EXPERT_TOOL: dict[str, Any] = {
    "name": "consult_expert",
    "description": """Consult a domain expert for specialized guidance during analysis.

Use this tool when you need expert advice on:
- **statistics**: Test selection, multiple testing correction, effect size interpretation, survival analysis methodology
- **clinical**: Cancer staging, treatment context, clinical vs statistical significance, confounders
- **immunology**: Tumor microenvironment, checkpoint biology, immunotherapy signatures (TIDE, infiltration)
- **genomics**: Gene function, pathway biology, variant interpretation, cancer hallmarks

You can consult multiple experts in parallel by providing multiple names in the experts array.

Examples:
- For survival analysis: ["statistics", "clinical"]
- For immunotherapy response: ["immunology", "clinical"]
- For differential expression: ["statistics", "genomics"]
- For mutation interpretation: ["genomics", "clinical"]""",
    "input_schema": {
        "type": "object",
        "properties": {
            "experts": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ["statistics", "clinical", "immunology", "genomics"],
                },
                "description": "Which experts to consult (can specify multiple for parallel consultation)",
                "minItems": 1,
                "maxItems": 4,
            },
            "question": {
                "type": "string",
                "description": "The specific question to ask the expert(s). Be clear and provide relevant context.",
                "minLength": 10,
            },
            "urgency": {
                "type": "string",
                "enum": ["quick", "normal", "thorough"],
                "default": "normal",
                "description": "How detailed should the response be? 'quick' for 1-2 sentences, 'thorough' for comprehensive.",
            },
        },
        "required": ["experts", "question"],
    },
}


async def execute_consult_expert(
    experts: list[str],
    question: str,
    context: dict[str, Any],
    urgency: str = "normal",
) -> dict[str, Any]:
    """
    Execute the consult_expert tool.

    This is called by the tool executor when the orchestrator invokes consult_expert.

    Args:
        experts: List of expert names to consult
        question: The question to ask
        context: Current analysis context (passed from orchestrator state)
        urgency: quick | normal | thorough

    Returns:
        Dict with consultation results
    """
    from .orchestrator import get_orchestrator

    orchestrator = get_orchestrator()

    if len(experts) == 1:
        response = await orchestrator.consult(
            consultant_name=experts[0],
            question=question,
            context=context,
            urgency=urgency,
        )
        if response:
            return {
                "success": True,
                "consultations": {experts[0]: _response_to_dict(response)},
                "synthesis": response.answer,
            }
        return {"success": False, "error": f"Unknown consultant: {experts[0]}"}

    # Multiple experts - parallel consultation
    responses = await orchestrator.consult_parallel(
        consultant_names=experts,
        question=question,
        context=context,
        urgency=urgency,
    )

    if not responses:
        return {"success": False, "error": "No valid consultants found"}

    synthesis = orchestrator.synthesize_responses(responses)

    return {
        "success": True,
        "consultations": {name: _response_to_dict(resp) for name, resp in responses.items()},
        "synthesis": synthesis,
    }


def _response_to_dict(response: Any) -> dict[str, Any]:
    """Convert ConsultationResponse to dict."""
    return {
        "consultant": response.consultant,
        "answer": response.answer,
        "confidence": response.confidence,
        "reasoning": response.reasoning,
        "caveats": response.caveats,
        "recommend_other": response.recommend_other,
    }
