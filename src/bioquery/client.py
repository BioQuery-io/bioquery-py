"""BioQuery API client."""

from __future__ import annotations

import os
from typing import Any, Callable

import httpx

from bioquery.exceptions import (
    AuthenticationError,
    BioQueryError,
    QueryError,
    RateLimitError,
)
from bioquery.models import QueryCard

DEFAULT_API_URL = "https://api.bioquery.io"
DEFAULT_TIMEOUT = 120.0


class Client:
    """Synchronous BioQuery API client."""

    def __init__(
        self,
        api_key: str | None = None,
        api_url: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialize the BioQuery client.

        Args:
            api_key: BioQuery API key. Falls back to BIOQUERY_API_KEY env var.
            api_url: API base URL. Falls back to BIOQUERY_API_URL env var or default.
            timeout: Request timeout in seconds.
        """
        self.api_key = api_key or os.getenv("BIOQUERY_API_KEY")
        self.api_url = (
            api_url or os.getenv("BIOQUERY_API_URL") or DEFAULT_API_URL
        ).rstrip("/")
        self.timeout = timeout

        self._client = httpx.Client(
            base_url=self.api_url,
            timeout=timeout,
            headers=self._get_headers(),
        )

    def _get_headers(self) -> dict[str, str]:
        """Get request headers."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _handle_response(self, response: httpx.Response) -> dict[str, Any]:
        """Handle API response and raise appropriate exceptions."""
        if response.status_code == 401:
            raise AuthenticationError("Invalid API key")
        elif response.status_code == 429:
            raise RateLimitError("Rate limit exceeded")
        elif response.status_code >= 400:
            try:
                error_data = response.json()
                message = error_data.get("detail", response.text)
            except Exception:
                message = response.text
            raise QueryError(f"API error ({response.status_code}): {message}")

        return response.json()

    def query(self, question: str) -> QueryCard:
        """Submit a natural language query.

        Args:
            question: Natural language question about cancer genomics.

        Returns:
            QueryCard with results, visualization, and statistics.

        Raises:
            AuthenticationError: If API key is invalid.
            QueryError: If query processing fails.
            RateLimitError: If rate limit is exceeded.
        """
        response = self._client.post("/query", json={"question": question})
        data = self._handle_response(response)
        return QueryCard(**data)

    def get_card(self, card_id: str) -> QueryCard:
        """Retrieve an existing Query Card by ID.

        Args:
            card_id: The unique card identifier.

        Returns:
            QueryCard with results.

        Raises:
            QueryError: If card is not found.
        """
        response = self._client.get(f"/cards/{card_id}")
        data = self._handle_response(response)
        return QueryCard(**data)

    def stream_query(
        self,
        question: str,
        on_progress: Callable[[dict[str, Any]], None] | None = None,
    ) -> QueryCard:
        """Submit a query and stream progress updates.

        Args:
            question: Natural language question.
            on_progress: Callback function for progress updates.

        Returns:
            QueryCard with final results.
        """
        with self._client.stream(
            "POST",
            "/query/stream",
            json={"question": question},
        ) as response:
            if response.status_code >= 400:
                raise QueryError(f"Stream error: {response.status_code}")

            final_card = None
            for line in response.iter_lines():
                if line.startswith("data: "):
                    import json

                    data = json.loads(line[6:])
                    if data.get("type") == "progress" and on_progress:
                        on_progress(data)
                    elif data.get("type") == "complete":
                        final_card = QueryCard(**data.get("card", {}))

            if final_card is None:
                raise QueryError("Stream ended without complete response")

            return final_card

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self) -> "Client":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()


class AsyncClient:
    """Asynchronous BioQuery API client."""

    def __init__(
        self,
        api_key: str | None = None,
        api_url: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialize the async BioQuery client."""
        self.api_key = api_key or os.getenv("BIOQUERY_API_KEY")
        self.api_url = (
            api_url or os.getenv("BIOQUERY_API_URL") or DEFAULT_API_URL
        ).rstrip("/")
        self.timeout = timeout

        self._client = httpx.AsyncClient(
            base_url=self.api_url,
            timeout=timeout,
            headers=self._get_headers(),
        )

    def _get_headers(self) -> dict[str, str]:
        """Get request headers."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def _handle_response(self, response: httpx.Response) -> dict[str, Any]:
        """Handle API response and raise appropriate exceptions."""
        if response.status_code == 401:
            raise AuthenticationError("Invalid API key")
        elif response.status_code == 429:
            raise RateLimitError("Rate limit exceeded")
        elif response.status_code >= 400:
            try:
                error_data = response.json()
                message = error_data.get("detail", response.text)
            except Exception:
                message = response.text
            raise QueryError(f"API error ({response.status_code}): {message}")

        return response.json()

    async def query(self, question: str) -> QueryCard:
        """Submit a natural language query."""
        response = await self._client.post("/query", json={"question": question})
        data = await self._handle_response(response)
        return QueryCard(**data)

    async def get_card(self, card_id: str) -> QueryCard:
        """Retrieve an existing Query Card by ID."""
        response = await self._client.get(f"/cards/{card_id}")
        data = await self._handle_response(response)
        return QueryCard(**data)

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    async def __aenter__(self) -> "AsyncClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()
