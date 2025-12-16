"""
Retry policy implementation with exponential backoff.

Inspired by LangGraph's RetryPolicy.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class RetryPolicy:
    """
    Retry policy with exponential backoff.

    Automatically retries failed operations with configurable
    backoff, attempt limits, and exception filtering.

    Example:
        ```python
        policy = RetryPolicy(
            max_attempts=3,
            initial_interval=1.0,
            backoff_multiplier=2.0,
            retry_on=(TimeoutError, APIError),
        )

        result = await policy.execute(my_async_func, state)
        ```
    """

    max_attempts: int = 3
    initial_interval: float = 1.0
    backoff_multiplier: float = 2.0
    max_interval: float = 30.0
    retry_on: tuple[type[Exception], ...] = field(default=(Exception,))

    async def execute(
        self,
        func: Callable[[dict[str, Any]], Any],
        state: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Execute function with retry logic.

        Args:
            func: Async function to execute
            state: State to pass to function

        Returns:
            Updated state from function

        Raises:
            Exception: If all retries exhausted
        """
        last_exception: Exception | None = None
        interval = self.initial_interval

        for attempt in range(self.max_attempts):
            try:
                result: dict[str, Any] = await func(state)
                return result
            except self.retry_on as e:
                last_exception = e
                if attempt < self.max_attempts - 1:
                    logger.warning(
                        f"Attempt {attempt + 1}/{self.max_attempts} failed: {e}. "
                        f"Retrying in {interval:.1f}s..."
                    )
                    await asyncio.sleep(interval)
                    interval = min(interval * self.backoff_multiplier, self.max_interval)
                else:
                    logger.error(f"All {self.max_attempts} attempts failed. Last error: {e}")

        if last_exception:
            raise last_exception
        raise RuntimeError("Retry loop completed without result or exception")

    def with_max_attempts(self, max_attempts: int) -> RetryPolicy:
        """Return a copy with different max_attempts."""
        return RetryPolicy(
            max_attempts=max_attempts,
            initial_interval=self.initial_interval,
            backoff_multiplier=self.backoff_multiplier,
            max_interval=self.max_interval,
            retry_on=self.retry_on,
        )

    def with_retry_on(self, *exceptions: type[Exception]) -> RetryPolicy:
        """Return a copy with different retry_on exceptions."""
        return RetryPolicy(
            max_attempts=self.max_attempts,
            initial_interval=self.initial_interval,
            backoff_multiplier=self.backoff_multiplier,
            max_interval=self.max_interval,
            retry_on=exceptions,
        )
