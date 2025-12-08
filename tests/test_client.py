"""Tests for BioQuery client."""

import pytest

from bioquery import Client


class TestClient:
    """Test cases for the BioQuery client."""

    def test_client_init_with_api_key(self) -> None:
        """Test client initialization with explicit API key."""
        client = Client(api_key="test-key")
        assert client.api_key == "test-key"
        assert client.api_url == "https://api.bioquery.io"
        client.close()

    def test_client_init_with_custom_url(self) -> None:
        """Test client initialization with custom API URL."""
        client = Client(api_key="test-key", api_url="http://localhost:8000")
        assert client.api_url == "http://localhost:8000"
        client.close()

    def test_client_context_manager(self) -> None:
        """Test client as context manager."""
        with Client(api_key="test-key") as client:
            assert client.api_key == "test-key"


# Integration tests would go here (marked with @pytest.mark.integration)
