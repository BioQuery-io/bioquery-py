"""Tests for BioQuery models."""

import pytest

from bioquery.models import QueryCard


class TestQueryCard:
    """Test cases for QueryCard model."""

    def test_query_card_basic(self) -> None:
        """Test basic QueryCard creation."""
        card = QueryCard(
            card_id="bq-2025-01-01-abc123",
            question="Is DDR1 higher in KIRP vs KIRC?",
            interpretation="Compare DDR1 expression between KIRP and KIRC",
            answer="DDR1 is significantly higher in KIRP.",
            statistics={"p_value": 0.001, "effect_size": 0.45},
        )
        assert card.card_id == "bq-2025-01-01-abc123"
        assert card.p_value == 0.001
        assert card.effect_size == 0.45

    def test_query_card_repr(self) -> None:
        """Test QueryCard string representation."""
        card = QueryCard(
            card_id="test-123",
            question="A very long question that should be truncated in the repr",
            interpretation="Test",
            answer="Test answer",
        )
        repr_str = repr(card)
        assert "test-123" in repr_str
        assert "..." in repr_str

    def test_query_card_to_dict(self) -> None:
        """Test QueryCard to dict conversion."""
        card = QueryCard(
            card_id="test-123",
            question="Test question",
            interpretation="Test interpretation",
            answer="Test answer",
        )
        d = card.to_dict()
        assert d["card_id"] == "test-123"
        assert "question" in d

    def test_query_card_no_figure_error(self) -> None:
        """Test error when accessing figure that doesn't exist."""
        card = QueryCard(
            card_id="test-123",
            question="Test",
            interpretation="Test",
            answer="Test",
            figure=None,
        )
        with pytest.raises(ValueError, match="No figure available"):
            card.show_figure()

    def test_query_card_no_data_error(self) -> None:
        """Test error when accessing data that doesn't exist."""
        card = QueryCard(
            card_id="test-123",
            question="Test",
            interpretation="Test",
            answer="Test",
            data=[],
        )
        with pytest.raises(ValueError, match="No data available"):
            card.to_dataframe()
