"""Tests for RetryPolicy."""

import pytest

from bioquery_agents import RetryPolicy


class TestRetryPolicy:
    """Tests for RetryPolicy class."""

    @pytest.mark.asyncio
    async def test_success_first_attempt(self):
        """Test successful execution on first attempt."""

        async def success_func(state: dict) -> dict:
            state["success"] = True
            return state

        policy = RetryPolicy(max_attempts=3)
        result = await policy.execute(success_func, {})

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_retry_until_success(self):
        """Test retry until function succeeds."""
        attempt_count = 0

        async def flaky_func(state: dict) -> dict:
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 2:
                raise ValueError("Temporary failure")
            state["success"] = True
            return state

        policy = RetryPolicy(
            max_attempts=3,
            initial_interval=0.01,
            retry_on=(ValueError,),
        )
        result = await policy.execute(flaky_func, {})

        assert result["success"] is True
        assert attempt_count == 2

    @pytest.mark.asyncio
    async def test_exhaust_retries(self):
        """Test exhausting all retries."""

        async def always_fail(state: dict) -> dict:
            raise ValueError("Always fails")

        policy = RetryPolicy(
            max_attempts=2,
            initial_interval=0.01,
            retry_on=(ValueError,),
        )

        with pytest.raises(ValueError, match="Always fails"):
            await policy.execute(always_fail, {})

    @pytest.mark.asyncio
    async def test_no_retry_on_unmatched_exception(self):
        """Test that unmatched exceptions are not retried."""
        attempt_count = 0

        async def type_error_func(state: dict) -> dict:
            nonlocal attempt_count
            attempt_count += 1
            raise TypeError("Type error")

        policy = RetryPolicy(
            max_attempts=3,
            initial_interval=0.01,
            retry_on=(ValueError,),  # Only retry ValueError
        )

        with pytest.raises(TypeError):
            await policy.execute(type_error_func, {})

        assert attempt_count == 1  # No retries

    def test_with_max_attempts(self):
        """Test creating copy with different max_attempts."""
        original = RetryPolicy(max_attempts=3)
        modified = original.with_max_attempts(5)

        assert modified.max_attempts == 5
        assert original.max_attempts == 3  # Original unchanged

    def test_with_retry_on(self):
        """Test creating copy with different retry_on."""
        original = RetryPolicy(retry_on=(ValueError,))
        modified = original.with_retry_on(TypeError, KeyError)

        assert modified.retry_on == (TypeError, KeyError)
        assert original.retry_on == (ValueError,)  # Original unchanged
