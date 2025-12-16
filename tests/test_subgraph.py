"""Tests for SubgraphExecutor."""

import pytest

from bioquery_agents import StateGraph
from bioquery_agents.subgraph import SubgraphBuilder, SubgraphExecutor


async def add_one(state: dict) -> dict:
    """Test node that adds one."""
    state["value"] = state.get("value", 0) + 1
    return state


async def multiply_two(state: dict) -> dict:
    """Test node that multiplies by two."""
    state["value"] = state.get("value", 0) * 2
    return state


async def failing_node(state: dict) -> dict:
    """Test node that fails."""
    raise ValueError("Subgraph failure")


def create_test_graph() -> StateGraph:
    """Create a test graph."""
    graph = StateGraph()
    graph.add_node("add", add_one)
    graph.add_node("multiply", multiply_two)
    graph.add_edge("add", "multiply")
    graph.add_edge("multiply", "END")
    graph.set_entry_point("add")
    return graph


class TestSubgraphExecutor:
    """Tests for SubgraphExecutor class."""

    @pytest.mark.asyncio
    async def test_basic_execution(self):
        """Test basic subgraph execution."""
        graph = create_test_graph()
        executor = SubgraphExecutor(graph)

        result = await executor.execute({"value": 5})

        assert result["success"] is True
        assert result["result"]["value"] == 12  # (5 + 1) * 2

    @pytest.mark.asyncio
    async def test_inherit_keys(self):
        """Test inheriting keys from parent state."""
        graph = create_test_graph()
        executor = SubgraphExecutor(graph)

        parent_state = {"user_id": "123", "session": "abc"}

        result = await executor.execute(
            initial_state={"value": 0},
            inherit_keys=["user_id"],
            parent_state=parent_state,
        )

        # Should inherit user_id but not session
        assert result["success"] is True
        inner_result = result["result"]
        assert "user_id" in inner_result
        assert inner_result["user_id"] == "123"

    @pytest.mark.asyncio
    async def test_return_keys(self):
        """Test filtering return keys."""
        graph = create_test_graph()
        executor = SubgraphExecutor(graph)

        result = await executor.execute(
            initial_state={"value": 5, "extra": "data"},
            return_keys=["value"],
        )

        assert result["success"] is True
        assert "value" in result["result"]
        assert "extra" not in result["result"]

    @pytest.mark.asyncio
    async def test_failure_isolation(self):
        """Test that failures are isolated."""
        graph = StateGraph()
        graph.add_node("fail", failing_node)
        graph.add_edge("fail", "END")
        graph.set_entry_point("fail")

        executor = SubgraphExecutor(graph)

        result = await executor.execute({})

        assert result["success"] is False
        assert "error" in result
        assert "Subgraph failure" in result["error"]

    @pytest.mark.asyncio
    async def test_parallel_execution(self):
        """Test parallel subgraph execution."""
        graph = create_test_graph()
        executor = SubgraphExecutor(graph)

        states = [
            {"value": 1},
            {"value": 2},
            {"value": 3},
        ]

        results = await executor.execute_parallel(states)

        assert len(results) == 3
        assert all(r["success"] for r in results)
        assert results[0]["result"]["value"] == 4  # (1 + 1) * 2
        assert results[1]["result"]["value"] == 6  # (2 + 1) * 2
        assert results[2]["result"]["value"] == 8  # (3 + 1) * 2


class TestSubgraphBuilder:
    """Tests for SubgraphBuilder class."""

    def test_extract_nodes(self):
        """Test extracting subset of nodes."""
        parent = StateGraph()
        parent.add_node("a", add_one)
        parent.add_node("b", multiply_two)
        parent.add_node("c", add_one)
        parent.add_edge("a", "b")
        parent.add_edge("b", "c")
        parent.add_edge("c", "END")
        parent.set_entry_point("a")

        builder = SubgraphBuilder(parent)
        subgraph = builder.extract(["a", "b"], entry_point="a")

        assert "a" in subgraph.nodes
        assert "b" in subgraph.nodes
        assert "c" not in subgraph.nodes

    def test_extract_preserves_edges(self):
        """Test that edges between extracted nodes are preserved."""
        parent = StateGraph()
        parent.add_node("a", add_one)
        parent.add_node("b", multiply_two)
        parent.add_edge("a", "b")
        parent.add_edge("b", "END")
        parent.set_entry_point("a")

        builder = SubgraphBuilder(parent)
        subgraph = builder.extract(["a", "b"], entry_point="a")

        # Should have edge from a to b
        edge_targets = [e.target for e in subgraph.edges if e.source == "a"]
        assert "b" in edge_targets

    def test_extract_invalid_node(self):
        """Test extracting nonexistent node raises error."""
        parent = StateGraph()
        parent.add_node("a", add_one)

        builder = SubgraphBuilder(parent)

        with pytest.raises(ValueError, match="not found"):
            builder.extract(["a", "nonexistent"], entry_point="a")

    @pytest.mark.asyncio
    async def test_extracted_graph_runs(self):
        """Test that extracted graph executes correctly."""
        parent = StateGraph()
        parent.add_node("a", add_one)
        parent.add_node("b", multiply_two)
        parent.add_node("c", add_one)  # Not extracted
        parent.add_edge("a", "b")
        parent.add_edge("b", "c")
        parent.add_edge("c", "END")
        parent.set_entry_point("a")

        builder = SubgraphBuilder(parent)
        subgraph = builder.extract(["a", "b"], entry_point="a")
        subgraph.add_edge("b", "END")  # Need to terminate

        result = await subgraph.run({"value": 5})

        assert result["value"] == 12  # (5 + 1) * 2
