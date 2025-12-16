"""Tests for Checkpointer."""

import pytest

from bioquery_agents import MemoryCheckpointer


class TestMemoryCheckpointer:
    """Tests for MemoryCheckpointer class."""

    @pytest.mark.asyncio
    async def test_save_and_load(self):
        """Test basic save and load."""
        checkpointer = MemoryCheckpointer()

        state = {"key": "value", "number": 42}
        await checkpointer.save("thread-1", state)

        loaded = await checkpointer.load("thread-1")
        assert loaded == state

    @pytest.mark.asyncio
    async def test_load_nonexistent(self):
        """Test loading nonexistent checkpoint returns None."""
        checkpointer = MemoryCheckpointer()

        loaded = await checkpointer.load("nonexistent")
        assert loaded is None

    @pytest.mark.asyncio
    async def test_delete(self):
        """Test deleting checkpoint."""
        checkpointer = MemoryCheckpointer()

        await checkpointer.save("thread-1", {"key": "value"})
        await checkpointer.delete("thread-1")

        loaded = await checkpointer.load("thread-1")
        assert loaded is None

    @pytest.mark.asyncio
    async def test_exists(self):
        """Test exists method."""
        checkpointer = MemoryCheckpointer()

        assert await checkpointer.exists("thread-1") is False

        await checkpointer.save("thread-1", {"key": "value"})
        assert await checkpointer.exists("thread-1") is True

    @pytest.mark.asyncio
    async def test_ttl_expiration(self):
        """Test TTL expiration."""
        import asyncio

        checkpointer = MemoryCheckpointer(ttl_seconds=1)  # 1 second TTL

        await checkpointer.save("thread-1", {"key": "value"})

        # Should exist immediately
        loaded = await checkpointer.load("thread-1")
        assert loaded is not None

        # Wait for expiration
        await asyncio.sleep(1.1)

        # Should be expired
        loaded = await checkpointer.load("thread-1")
        assert loaded is None

    @pytest.mark.asyncio
    async def test_overwrite(self):
        """Test overwriting existing checkpoint."""
        checkpointer = MemoryCheckpointer()

        await checkpointer.save("thread-1", {"version": 1})
        await checkpointer.save("thread-1", {"version": 2})

        loaded = await checkpointer.load("thread-1")
        assert loaded["version"] == 2

    @pytest.mark.asyncio
    async def test_isolation(self):
        """Test that state mutations don't affect stored state."""
        checkpointer = MemoryCheckpointer()

        state = {"key": "original"}
        await checkpointer.save("thread-1", state)

        # Mutate original
        state["key"] = "mutated"

        # Load should have original value
        loaded = await checkpointer.load("thread-1")
        assert loaded["key"] == "original"

    def test_clear(self):
        """Test clearing all checkpoints."""
        checkpointer = MemoryCheckpointer()

        # Can't use async in sync test, but can test clear directly
        checkpointer._store["thread-1"] = {"key": "value"}
        checkpointer._store["thread-2"] = {"key": "value"}

        checkpointer.clear()

        assert checkpointer.size == 0

    @pytest.mark.asyncio
    async def test_skip_non_serializable(self):
        """Test that non-serializable values are skipped."""
        checkpointer = MemoryCheckpointer()

        state = {
            "serializable": "value",
            "non_serializable": lambda x: x,  # Functions are not serializable
        }

        await checkpointer.save("thread-1", state)
        loaded = await checkpointer.load("thread-1")

        assert "serializable" in loaded
        assert "non_serializable" not in loaded
