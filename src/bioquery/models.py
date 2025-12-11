"""BioQuery SDK data models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd
import plotly.graph_objects as go
from pydantic import BaseModel, Field


class QueryCard(BaseModel):
    """Represents a BioQuery Query Card result."""

    card_id: str = Field(..., description="Unique card identifier")
    question: str = Field(..., description="Original natural language question")
    interpretation: str = Field(..., description="How BioQuery understood the query")
    answer: str = Field(..., description="Natural language answer")
    figure: dict[str, Any] | None = Field(None, description="Plotly figure JSON")
    statistics: dict[str, Any] = Field(
        default_factory=dict, description="Statistical results"
    )
    sql_query: str | None = Field(None, description="Executed BigQuery SQL")
    methods_text: str | None = Field(None, description="Grant-ready methods text")
    data: list[dict[str, Any]] = Field(
        default_factory=list, description="Underlying data"
    )
    created_at: datetime | None = Field(None, description="Creation timestamp")
    analysis_type: str | None = Field(None, description="Type of analysis performed")

    model_config = {"extra": "allow"}

    def show_figure(self) -> None:
        """Display the interactive Plotly figure in a notebook."""
        if self.figure is None:
            raise ValueError("No figure available for this card")
        fig = go.Figure(self.figure)
        fig.show()

    def get_figure(self) -> go.Figure:
        """Get the Plotly figure object for customization."""
        if self.figure is None:
            raise ValueError("No figure available for this card")
        return go.Figure(self.figure)

    def save_figure(
        self,
        path: str,
        format: str | None = None,
        width: int = 1200,
        height: int = 800,
        scale: float = 2.0,
    ) -> None:
        """Save the figure to a file.

        Args:
            path: Output file path
            format: Export format (png, svg, pdf, html). Auto-detected from path if not specified.
            width: Image width in pixels
            height: Image height in pixels
            scale: Image scale factor
        """
        if self.figure is None:
            raise ValueError("No figure available for this card")

        fig = go.Figure(self.figure)

        if format is None:
            format = path.split(".")[-1].lower()

        if format == "html":
            fig.write_html(path)
        else:
            fig.write_image(path, width=width, height=height, scale=scale)

    def to_dataframe(self) -> pd.DataFrame:
        """Convert the underlying data to a pandas DataFrame."""
        if not self.data:
            raise ValueError("No data available for this card")
        return pd.DataFrame(self.data)

    def to_json(self) -> str:
        """Export the full card as JSON."""
        return self.model_dump_json(indent=2)

    def to_dict(self) -> dict[str, Any]:
        """Export the full card as a dictionary."""
        return self.model_dump()

    @property
    def p_value(self) -> float | None:
        """Get the p-value from statistics if available."""
        return self.statistics.get("p_value")

    @property
    def effect_size(self) -> float | None:
        """Get the effect size from statistics if available."""
        return self.statistics.get("effect_size")

    def __repr__(self) -> str:
        return (
            f"QueryCard(card_id='{self.card_id}', question='{self.question[:50]}...')"
        )
