"""
Checkpointing for state persistence.

Enables resumable execution and human-in-the-loop patterns.
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


class Checkpointer(ABC):
    """
    Abstract base class for state persistence.

    Checkpointers enable:
    - Resumable execution after failures
    - Human-in-the-loop interrupts
    - Long-running workflow state management

    Implementations should handle serialization of state dicts.
    """

    @abstractmethod
    async def save(self, thread_id: str, state: dict[str, Any]) -> None:
        """
        Save state checkpoint.

        Args:
            thread_id: Unique identifier for this execution thread
            state: State dictionary to persist
        """
        pass

    @abstractmethod
    async def load(self, thread_id: str) -> dict[str, Any] | None:
        """
        Load state checkpoint.

        Args:
            thread_id: Unique identifier for this execution thread

        Returns:
            Saved state dict, or None if not found
        """
        pass

    @abstractmethod
    async def delete(self, thread_id: str) -> None:
        """
        Delete checkpoint.

        Args:
            thread_id: Unique identifier for this execution thread
        """
        pass

    async def exists(self, thread_id: str) -> bool:
        """Check if checkpoint exists."""
        return await self.load(thread_id) is not None


class MemoryCheckpointer(Checkpointer):
    """
    In-memory checkpointer for development and testing.

    Not suitable for production use as state is lost on restart.
    """

    def __init__(self, ttl_seconds: int = 3600):
        """
        Initialize memory checkpointer.

        Args:
            ttl_seconds: Time-to-live for checkpoints (default: 1 hour)
        """
        self._store: dict[str, dict[str, Any]] = {}
        self._timestamps: dict[str, datetime] = {}
        self._ttl = timedelta(seconds=ttl_seconds)

    async def save(self, thread_id: str, state: dict[str, Any]) -> None:
        """Save state to memory."""
        # Deep copy to prevent mutation issues
        self._store[thread_id] = json.loads(json.dumps(self._serialize(state)))
        self._timestamps[thread_id] = datetime.now(UTC)
        logger.debug(f"Saved checkpoint for thread {thread_id}")

    async def load(self, thread_id: str) -> dict[str, Any] | None:
        """Load state from memory."""
        if thread_id not in self._store:
            return None

        # Check TTL
        if datetime.now(UTC) - self._timestamps[thread_id] > self._ttl:
            logger.debug(f"Checkpoint for thread {thread_id} expired")
            await self.delete(thread_id)
            return None

        logger.debug(f"Loaded checkpoint for thread {thread_id}")
        return self._store[thread_id]

    async def delete(self, thread_id: str) -> None:
        """Delete checkpoint from memory."""
        self._store.pop(thread_id, None)
        self._timestamps.pop(thread_id, None)
        logger.debug(f"Deleted checkpoint for thread {thread_id}")

    def _serialize(self, state: dict[str, Any]) -> dict[str, Any]:
        """Serialize state, filtering non-serializable values."""
        result = {}
        for key, value in state.items():
            try:
                # Test if value is JSON-serializable
                json.dumps(value)
                result[key] = value
            except (TypeError, ValueError):
                # Skip non-serializable values but log them
                logger.debug(f"Skipping non-serializable key: {key}")
        return result

    def clear(self) -> None:
        """Clear all checkpoints (for testing)."""
        self._store.clear()
        self._timestamps.clear()

    @property
    def size(self) -> int:
        """Number of stored checkpoints."""
        return len(self._store)
