"""
Tests for the consultants module.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from bioquery_agents.consultants import (
    BIOSTATISTICS_CONSULTANT,
    CLINICAL_ONCOLOGY_CONSULTANT,
    CONSULT_EXPERT_TOOL,
    CONSULTANTS,
    GENOMICS_CONSULTANT,
    IMMUNOLOGY_CONSULTANT,
    ConsultantOrchestrator,
    ConsultationRequest,
    ConsultationResponse,
    DomainConsultant,
    get_consultant,
    get_orchestrator,
    list_consultants,
    reset_orchestrator,
)


class TestConsultationSchemas:
    """Tests for consultation data models."""

    def test_consultation_request_defaults(self):
        """Test ConsultationRequest with defaults."""
        request = ConsultationRequest(question="Test question?")
        assert request.question == "Test question?"
        assert request.context == {}
        assert request.urgency == "normal"

    def test_consultation_request_with_context(self):
        """Test ConsultationRequest with context."""
        request = ConsultationRequest(
            question="What test?",
            context={"genes": ["TP53"], "n_samples": 100},
            urgency="quick",
        )
        assert request.context["genes"] == ["TP53"]
        assert request.urgency == "quick"

    def test_consultation_response_defaults(self):
        """Test ConsultationResponse with defaults."""
        response = ConsultationResponse(
            consultant="Test",
            answer="Answer",
            confidence=0.8,
            reasoning="Because",
        )
        assert response.caveats == []
        assert response.recommend_other == []


class TestDomainConsultant:
    """Tests for DomainConsultant base class."""

    def test_consultant_custom_model(self):
        """Test consultant with custom model."""
        consultant = DomainConsultant(
            name="Custom",
            expertise="Custom",
            system_prompt="Custom prompt",
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
        )
        assert consultant.model == "claude-sonnet-4-20250514"
        assert consultant.max_tokens == 2048


    def test_format_question(self):
        """Test question formatting."""
        consultant = DomainConsultant(
            name="Test",
            expertise="Test",
            system_prompt="Test",
        )
        request = ConsultationRequest(
            question="What test should I use?",
            context={"n_groups": 2},
            urgency="quick",
        )
        formatted = consultant._format_question(request)
        assert "What test should I use?" in formatted
        assert '"n_groups": 2' in formatted
        assert "brief, direct answer" in formatted

    def test_parse_response_json(self):
        """Test parsing JSON response."""
        consultant = DomainConsultant(
            name="Test",
            expertise="Test",
            system_prompt="Test",
        )
        text = '{"answer": "Use t-test", "confidence": 0.9, "reasoning": "Two groups", "caveats": ["Check normality"]}'
        response = consultant._parse_response(text)
        assert response.answer == "Use t-test"
        assert response.confidence == 0.9
        assert "Check normality" in response.caveats

    def test_parse_response_json_code_block(self):
        """Test parsing JSON in code block."""
        consultant = DomainConsultant(
            name="Test",
            expertise="Test",
            system_prompt="Test",
        )
        text = '```json\n{"answer": "Test answer", "confidence": 0.8, "reasoning": "Test", "caveats": []}\n```'
        response = consultant._parse_response(text)
        assert response.answer == "Test answer"

    def test_parse_response_fallback(self):
        """Test fallback when JSON parsing fails."""
        consultant = DomainConsultant(
            name="Test",
            expertise="Test",
            system_prompt="Test",
        )
        text = "Just plain text without JSON"
        response = consultant._parse_response(text)
        assert response.answer == text
        assert response.confidence == 0.5
        assert "Response parsing failed" in response.caveats


class TestConsultantDefinitions:
    """Tests for consultant definitions."""

    def test_biostatistics_consultant(self):
        """Test biostatistics consultant is properly defined."""
        assert BIOSTATISTICS_CONSULTANT.name == "Biostatistics Consultant"
        assert "statistical" in BIOSTATISTICS_CONSULTANT.expertise.lower()
        assert len(BIOSTATISTICS_CONSULTANT.system_prompt) > 500

    def test_clinical_consultant(self):
        """Test clinical oncology consultant."""
        assert CLINICAL_ONCOLOGY_CONSULTANT.name == "Clinical Oncology Consultant"
        assert "staging" in CLINICAL_ONCOLOGY_CONSULTANT.expertise.lower()

    def test_immunology_consultant(self):
        """Test immunology consultant."""
        assert IMMUNOLOGY_CONSULTANT.name == "Tumor Immunology Consultant"
        assert "checkpoint" in IMMUNOLOGY_CONSULTANT.expertise.lower()

    def test_genomics_consultant(self):
        """Test genomics consultant."""
        assert GENOMICS_CONSULTANT.name == "Cancer Genomics Consultant"
        assert "pathway" in GENOMICS_CONSULTANT.expertise.lower()

    def test_all_consultants_in_registry(self):
        """Test all consultants are in registry."""
        assert "statistics" in CONSULTANTS
        assert "clinical" in CONSULTANTS
        assert "immunology" in CONSULTANTS
        assert "genomics" in CONSULTANTS
        assert len(CONSULTANTS) == 4

    def test_get_consultant(self):
        """Test get_consultant function."""
        stats = get_consultant("statistics")
        assert stats is not None
        assert stats.name == "Biostatistics Consultant"

        unknown = get_consultant("unknown")
        assert unknown is None

    def test_list_consultants(self):
        """Test list_consultants function."""
        names = list_consultants()
        assert set(names) == {"statistics", "clinical", "immunology", "genomics"}


class TestConsultantOrchestrator:
    """Tests for ConsultantOrchestrator."""

    def setup_method(self):
        """Reset orchestrator before each test."""
        reset_orchestrator()

    def test_orchestrator_creation(self):
        """Test orchestrator instantiation."""
        orchestrator = ConsultantOrchestrator()
        assert len(orchestrator.consultants) == 4
        assert orchestrator.cache_enabled is True

    def test_should_consult_survival(self):
        """Test automatic consultant selection for survival analysis."""
        orchestrator = ConsultantOrchestrator()
        recommended = orchestrator.should_consult(
            analysis_type="survival_analysis",
            context={"genes": ["TP53"], "cancer_types": ["BRCA"]},
        )
        assert "statistics" in recommended
        assert "clinical" in recommended

    def test_should_consult_differential(self):
        """Test automatic consultant selection for differential expression."""
        orchestrator = ConsultantOrchestrator()
        recommended = orchestrator.should_consult(
            analysis_type="differential_expression",
            context={"genes": ["EGFR"]},
        )
        assert "statistics" in recommended

    def test_should_consult_immunotherapy(self):
        """Test automatic consultant selection for immunotherapy."""
        orchestrator = ConsultantOrchestrator()
        recommended = orchestrator.should_consult(
            analysis_type="signature_score",
            context={"signature": "immune_infiltration", "checkpoint": True},
        )
        assert "immunology" in recommended

    def test_should_consult_iatlas(self):
        """Test automatic consultant selection for iAtlas data."""
        orchestrator = ConsultantOrchestrator()
        recommended = orchestrator.should_consult(
            analysis_type="any",
            context={"data_source": "iatlas_ici"},
        )
        assert "immunology" in recommended
        assert "clinical" in recommended

    def test_should_consult_pathway(self):
        """Test automatic consultant selection for pathway analysis."""
        orchestrator = ConsultantOrchestrator()
        recommended = orchestrator.should_consult(
            analysis_type="scientific_context",
            context={"question": "What pathway is TP53 in?"},
        )
        assert "genomics" in recommended

    def test_should_consult_empty(self):
        """Test no consultants for simple queries."""
        orchestrator = ConsultantOrchestrator()
        recommended = orchestrator.should_consult(
            analysis_type="platform_info",
            context={},
        )
        assert recommended == []

    def test_cache_key_generation(self):
        """Test cache key generation is consistent."""
        orchestrator = ConsultantOrchestrator()
        request = ConsultationRequest(question="Test?", context={"a": 1})
        key1 = orchestrator._cache_key("statistics", request)
        key2 = orchestrator._cache_key("statistics", request)
        assert key1 == key2
        assert len(key1) == 16  # SHA256 truncated

    def test_cache_key_different_consultants(self):
        """Test different consultants get different cache keys."""
        orchestrator = ConsultantOrchestrator()
        request = ConsultationRequest(question="Test?", context={})
        key_stats = orchestrator._cache_key("statistics", request)
        key_clinical = orchestrator._cache_key("clinical", request)
        assert key_stats != key_clinical

    def test_synthesize_single_response(self):
        """Test synthesizing a single response."""
        orchestrator = ConsultantOrchestrator()
        responses = {
            "statistics": ConsultationResponse(
                consultant="Biostatistics Consultant",
                answer="Use FDR correction",
                confidence=0.9,
                reasoning="Multiple comparisons",
            )
        }
        synthesis = orchestrator.synthesize_responses(responses)
        assert "Biostatistics Consultant" in synthesis
        assert "Use FDR correction" in synthesis

    def test_synthesize_multiple_responses(self):
        """Test synthesizing multiple responses."""
        orchestrator = ConsultantOrchestrator()
        responses = {
            "statistics": ConsultationResponse(
                consultant="Statistics",
                answer="Use log-rank test",
                confidence=0.9,
                reasoning="Survival data",
                caveats=["Check proportional hazards"],
            ),
            "clinical": ConsultationResponse(
                consultant="Clinical",
                answer="Consider stage as covariate",
                confidence=0.8,
                reasoning="Clinical context",
                caveats=["Treatment effects"],
            ),
        }
        synthesis = orchestrator.synthesize_responses(responses)
        assert "statistics" in synthesis
        assert "clinical" in synthesis
        assert "90%" in synthesis
        assert "80%" in synthesis
        assert "Caveats" in synthesis

    def test_synthesize_empty(self):
        """Test synthesizing empty responses."""
        orchestrator = ConsultantOrchestrator()
        synthesis = orchestrator.synthesize_responses({})
        assert synthesis == ""

    def test_clear_cache(self):
        """Test cache clearing."""
        orchestrator = ConsultantOrchestrator()
        orchestrator.cache["test_key"] = ConsultationResponse(
            consultant="Test",
            answer="Test",
            confidence=0.5,
            reasoning="Test",
        )
        assert len(orchestrator.cache) == 1
        orchestrator.clear_cache()
        assert len(orchestrator.cache) == 0

    def test_global_orchestrator(self):
        """Test global orchestrator singleton."""
        reset_orchestrator()
        orch1 = get_orchestrator()
        orch2 = get_orchestrator()
        assert orch1 is orch2


class TestConsultExpertTool:
    """Tests for consult_expert tool definition."""

    def test_tool_definition_structure(self):
        """Test tool definition has required fields."""
        assert CONSULT_EXPERT_TOOL["name"] == "consult_expert"
        assert "description" in CONSULT_EXPERT_TOOL
        assert "input_schema" in CONSULT_EXPERT_TOOL

    def test_tool_schema_properties(self):
        """Test tool input schema properties."""
        schema = CONSULT_EXPERT_TOOL["input_schema"]
        assert schema["type"] == "object"
        assert "experts" in schema["properties"]
        assert "question" in schema["properties"]
        assert "urgency" in schema["properties"]

    def test_tool_schema_experts_enum(self):
        """Test experts enum values."""
        experts_schema = CONSULT_EXPERT_TOOL["input_schema"]["properties"]["experts"]
        assert experts_schema["type"] == "array"
        enum_values = experts_schema["items"]["enum"]
        assert set(enum_values) == {"statistics", "clinical", "immunology", "genomics"}

    def test_tool_required_fields(self):
        """Test required fields."""
        required = CONSULT_EXPERT_TOOL["input_schema"]["required"]
        assert "experts" in required
        assert "question" in required


class TestConsultantIntegration:
    """Integration tests for consultant workflow."""

    def setup_method(self):
        """Reset orchestrator before each test."""
        reset_orchestrator()

    @pytest.mark.asyncio
    async def test_consult_with_mock(self):
        """Test consultation with mocked API."""
        orchestrator = ConsultantOrchestrator()

        # Create a mock consultant
        mock_consultant = MagicMock(spec=DomainConsultant)
        mock_consultant.consult = AsyncMock(
            return_value=ConsultationResponse(
                consultant="Mock Consultant",
                answer="Mock answer",
                confidence=0.9,
                reasoning="Mock reasoning",
                caveats=[],
            )
        )
        orchestrator.consultants["mock"] = mock_consultant

        response = await orchestrator.consult(
            consultant_name="mock",
            question="Test question?",
            context={"test": True},
        )

        assert response is not None
        assert response.answer == "Mock answer"
        mock_consultant.consult.assert_called_once()

    @pytest.mark.asyncio
    async def test_consult_unknown_consultant(self):
        """Test consulting unknown consultant."""
        orchestrator = ConsultantOrchestrator()
        response = await orchestrator.consult(
            consultant_name="unknown",
            question="Test?",
            context={},
        )
        assert response is None

    @pytest.mark.asyncio
    async def test_consult_parallel_with_mock(self):
        """Test parallel consultation with mocked API."""
        orchestrator = ConsultantOrchestrator()

        # Create mock consultants
        for name in ["mock1", "mock2"]:
            mock_consultant = MagicMock(spec=DomainConsultant)
            mock_consultant.consult = AsyncMock(
                return_value=ConsultationResponse(
                    consultant=f"{name} Consultant",
                    answer=f"Answer from {name}",
                    confidence=0.8,
                    reasoning="Test",
                )
            )
            orchestrator.consultants[name] = mock_consultant

        responses = await orchestrator.consult_parallel(
            consultant_names=["mock1", "mock2"],
            question="Test question?",
            context={},
        )

        assert len(responses) == 2
        assert "mock1" in responses
        assert "mock2" in responses

    @pytest.mark.asyncio
    async def test_caching_works(self):
        """Test that caching prevents duplicate API calls."""
        orchestrator = ConsultantOrchestrator()

        mock_consultant = MagicMock(spec=DomainConsultant)
        mock_consultant.consult = AsyncMock(
            return_value=ConsultationResponse(
                consultant="Mock",
                answer="Cached answer",
                confidence=0.9,
                reasoning="Test",
            )
        )
        orchestrator.consultants["mock"] = mock_consultant

        # First call
        await orchestrator.consult("mock", "Same question?", {})
        # Second call - should hit cache
        await orchestrator.consult("mock", "Same question?", {})

        # Should only have called the API once
        assert mock_consultant.consult.call_count == 1
