"""
State graph implementation for agent orchestration.

Inspired by LangGraph's StateGraph but without the dependency.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from bioquery_agents.checkpoint import Checkpointer
    from bioquery_agents.retry import RetryPolicy

logger = logging.getLogger(__name__)

# Type variable for state
S = TypeVar("S", bound=dict[str, Any])


class NodeStatus(Enum):
    """Status of a node execution."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class Node:
    """A node in the execution graph."""

    name: str
    handler: Callable[[dict[str, Any]], Any]
    retry_policy: RetryPolicy | None = None
    on_failure: str = "error"  # "error", "skip", or target node name


@dataclass
class Edge:
    """An edge connecting nodes."""

    source: str
    target: str | None  # None if conditional
    condition: Callable[[dict[str, Any]], str] | None = None


@dataclass
class StateGraph:
    """
    Simple state graph for agent orchestration.

    A StateGraph defines a directed graph where:
    - Nodes are async functions that transform state
    - Edges define transitions between nodes
    - Conditional edges route based on state

    Example:
        ```python
        graph = StateGraph()
        graph.add_node("parse", parse_query)
        graph.add_node("fetch", fetch_data, retry_policy=BIGQUERY_RETRY)
        graph.add_node("respond", generate_response)

        graph.add_edge("parse", "fetch")
        graph.add_conditional_edge("fetch", route_after_fetch)
        graph.add_edge("respond", "END")

        graph.set_entry_point("parse")

        result = await graph.run({"query": "..."})
        ```
    """

    nodes: dict[str, Node] = field(default_factory=dict)
    edges: list[Edge] = field(default_factory=list)
    entry_point: str | None = None

    def add_node(
        self,
        name: str,
        handler: Callable[[dict[str, Any]], Any],
        retry_policy: RetryPolicy | None = None,
        on_failure: str = "error",
    ) -> None:
        """
        Add a node to the graph.

        Args:
            name: Unique node identifier
            handler: Async function that takes state dict and returns updated state
            retry_policy: Optional retry policy for transient failures
            on_failure: What to do on failure: "error", "skip", or target node name
        """
        self.nodes[name] = Node(
            name=name,
            handler=handler,
            retry_policy=retry_policy,
            on_failure=on_failure,
        )

    def add_edge(self, source: str, target: str) -> None:
        """
        Add unconditional edge from source to target.

        Args:
            source: Source node name
            target: Target node name (use "END" to terminate)
        """
        self.edges.append(Edge(source=source, target=target))

    def add_conditional_edge(
        self,
        source: str,
        router: Callable[[dict[str, Any]], str],
    ) -> None:
        """
        Add conditional edge based on state.

        Args:
            source: Source node name
            router: Function that takes state and returns target node name
        """
        self.edges.append(Edge(source=source, target=None, condition=router))

    def set_entry_point(self, node: str) -> None:
        """Set the starting node."""
        if node not in self.nodes:
            raise ValueError(f"Unknown node: {node}")
        self.entry_point = node

    async def run(
        self,
        initial_state: dict[str, Any],
        checkpointer: Checkpointer | None = None,
    ) -> dict[str, Any]:
        """
        Execute the graph.

        Args:
            initial_state: Initial state dictionary
            checkpointer: Optional checkpointer for state persistence

        Returns:
            Final state after graph execution
        """
        if self.entry_point is None:
            raise ValueError("Entry point not set. Call set_entry_point() first.")

        state = {**initial_state}
        current_node: str | None = self.entry_point

        # Load checkpoint if exists
        thread_id = state.get("thread_id")
        if checkpointer and thread_id:
            saved = await checkpointer.load(thread_id)
            if saved:
                state = {**state, **saved}
                current_node = state.get("_current_node", self.entry_point)
                logger.info(f"Resumed from checkpoint at node: {current_node}")

        while current_node and current_node != "END":
            node = self.nodes.get(current_node)
            if not node:
                raise ValueError(f"Unknown node: {current_node}")

            logger.debug(f"Executing node: {current_node}")
            state["_current_node"] = current_node
            state["_node_status"] = NodeStatus.RUNNING.value

            # Execute node with retry
            try:
                state = await self._execute_node(node, state)
                state["_node_status"] = NodeStatus.SUCCESS.value
            except Exception as e:
                logger.error(f"Node {current_node} failed: {e}")
                state["_node_status"] = NodeStatus.FAILED.value
                state["_error"] = str(e)

                if node.on_failure == "error":
                    # Save checkpoint before raising
                    if checkpointer and thread_id:
                        await checkpointer.save(thread_id, state)
                    raise
                elif node.on_failure == "skip":
                    state["_node_status"] = NodeStatus.SKIPPED.value
                else:
                    # on_failure is a target node name (e.g., "replan")
                    current_node = node.on_failure
                    continue

            # Save checkpoint
            if checkpointer and thread_id:
                await checkpointer.save(thread_id, state)

            # Find next node
            current_node = self._get_next_node(current_node, state)

        return state

    async def _execute_node(
        self,
        node: Node,
        state: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a node with optional retry."""
        if node.retry_policy:
            return await node.retry_policy.execute(node.handler, state)
        result: dict[str, Any] = await node.handler(state)
        return result

    def _get_next_node(
        self,
        current: str,
        state: dict[str, Any],
    ) -> str | None:
        """Determine next node based on edges."""
        for edge in self.edges:
            if edge.source != current:
                continue
            if edge.condition:
                return edge.condition(state)
            return edge.target
        return None

    def get_node_names(self) -> list[str]:
        """Get list of all node names."""
        return list(self.nodes.keys())

    def validate(self) -> list[str]:
        """
        Validate the graph structure.

        Returns:
            List of validation errors (empty if valid)
        """
        errors: list[str] = []

        if self.entry_point is None:
            errors.append("No entry point set")

        if self.entry_point and self.entry_point not in self.nodes:
            errors.append(f"Entry point '{self.entry_point}' not found in nodes")

        # Check all edge targets exist
        for edge in self.edges:
            if edge.source not in self.nodes:
                errors.append(f"Edge source '{edge.source}' not found in nodes")
            if edge.target and edge.target != "END" and edge.target not in self.nodes:
                errors.append(f"Edge target '{edge.target}' not found in nodes")

        # Check all nodes have outgoing edges (except END targets)
        nodes_with_edges = {edge.source for edge in self.edges}
        for node_name in self.nodes:
            if node_name not in nodes_with_edges:
                errors.append(f"Node '{node_name}' has no outgoing edges")

        return errors
