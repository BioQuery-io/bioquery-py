"""Tests for StateGraph."""

import pytest

from bioquery_agents import NodeStatus, StateGraph
from bioquery_agents.checkpoint import MemoryCheckpointer
from bioquery_agents.retry import RetryPolicy


async def increment_node(state: dict) -> dict:
    """Test node that increments a counter."""
    state["counter"] = state.get("counter", 0) + 1
    return state


async def double_node(state: dict) -> dict:
    """Test node that doubles the counter."""
    state["counter"] = state.get("counter", 0) * 2
    return state


async def failing_node(state: dict) -> dict:
    """Test node that always fails."""
    raise ValueError("Intentional failure")


async def conditional_node(state: dict) -> dict:
    """Test node for conditional routing."""
    state["processed"] = True
    return state


def route_by_counter(state: dict) -> str:
    """Route based on counter value."""
    if state.get("counter", 0) > 5:
        return "END"
    return "increment"


class TestStateGraph:
    """Tests for StateGraph class."""

    @pytest.mark.asyncio
    async def test_simple_linear_graph(self):
        """Test basic linear execution."""
        graph = StateGraph()
        graph.add_node("increment", increment_node)
        graph.add_node("double", double_node)
        graph.add_edge("increment", "double")
        graph.add_edge("double", "END")
        graph.set_entry_point("increment")

        result = await graph.run({"counter": 1})

        assert result["counter"] == 4  # (1 + 1) * 2
        assert result["_node_status"] == NodeStatus.SUCCESS.value

    @pytest.mark.asyncio
    async def test_conditional_routing(self):
        """Test conditional edge routing."""
        graph = StateGraph()
        graph.add_node("increment", increment_node)
        graph.add_conditional_edge("increment", route_by_counter)
        graph.set_entry_point("increment")

        result = await graph.run({"counter": 0})

        # Should loop until counter > 5
        assert result["counter"] > 5

    @pytest.mark.asyncio
    async def test_node_failure_error(self):
        """Test that failures raise by default."""
        graph = StateGraph()
        graph.add_node("fail", failing_node)
        graph.add_edge("fail", "END")
        graph.set_entry_point("fail")

        with pytest.raises(ValueError, match="Intentional failure"):
            await graph.run({})

    @pytest.mark.asyncio
    async def test_node_failure_skip(self):
        """Test on_failure='skip' behavior."""
        graph = StateGraph()
        graph.add_node("fail", failing_node, on_failure="skip")
        graph.add_node("after", increment_node)
        graph.add_edge("fail", "after")
        graph.add_edge("after", "END")
        graph.set_entry_point("fail")

        result = await graph.run({"counter": 0})

        assert result["counter"] == 1
        assert result["_node_status"] == NodeStatus.SUCCESS.value

    @pytest.mark.asyncio
    async def test_node_failure_redirect(self):
        """Test on_failure redirects to another node."""
        graph = StateGraph()
        graph.add_node("fail", failing_node, on_failure="recovery")
        graph.add_node("recovery", increment_node)
        graph.add_edge("fail", "END")  # Never reached
        graph.add_edge("recovery", "END")
        graph.set_entry_point("fail")

        result = await graph.run({"counter": 0})

        assert result["counter"] == 1
        assert "_error" in result

    @pytest.mark.asyncio
    async def test_checkpointing(self):
        """Test state persistence with checkpointer."""
        checkpointer = MemoryCheckpointer()
        graph = StateGraph()
        graph.add_node("increment", increment_node)
        graph.add_edge("increment", "END")
        graph.set_entry_point("increment")

        result = await graph.run(
            {"thread_id": "test-123", "counter": 0},
            checkpointer=checkpointer,
        )

        assert result["counter"] == 1

        # Check checkpoint was saved
        saved = await checkpointer.load("test-123")
        assert saved is not None
        assert saved["counter"] == 1

    def test_validation_no_entry_point(self):
        """Test validation catches missing entry point."""
        graph = StateGraph()
        graph.add_node("test", increment_node)
        graph.add_edge("test", "END")

        errors = graph.validate()
        assert "No entry point set" in errors

    def test_validation_invalid_edge_target(self):
        """Test validation catches invalid edge targets."""
        graph = StateGraph()
        graph.add_node("test", increment_node)
        graph.add_edge("test", "nonexistent")
        graph.set_entry_point("test")

        errors = graph.validate()
        assert any("nonexistent" in e for e in errors)

    def test_get_node_names(self):
        """Test getting node names."""
        graph = StateGraph()
        graph.add_node("a", increment_node)
        graph.add_node("b", double_node)

        names = graph.get_node_names()
        assert set(names) == {"a", "b"}


class TestStateGraphWithRetry:
    """Tests for StateGraph with RetryPolicy."""

    @pytest.mark.asyncio
    async def test_retry_on_failure(self):
        """Test retry policy is applied."""
        attempt_count = 0

        async def flaky_node(state: dict) -> dict:
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ValueError("Temporary failure")
            state["success"] = True
            return state

        policy = RetryPolicy(
            max_attempts=3,
            initial_interval=0.01,  # Fast for testing
            retry_on=(ValueError,),
        )

        graph = StateGraph()
        graph.add_node("flaky", flaky_node, retry_policy=policy)
        graph.add_edge("flaky", "END")
        graph.set_entry_point("flaky")

        result = await graph.run({})

        assert result["success"] is True
        assert attempt_count == 3
