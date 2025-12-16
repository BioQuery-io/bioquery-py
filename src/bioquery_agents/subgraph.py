"""
Subgraph execution for isolated agent workflows.

Inspired by LangGraph subgraph pattern.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bioquery_agents.checkpoint import Checkpointer
    from bioquery_agents.graph import StateGraph

logger = logging.getLogger(__name__)


class SubgraphExecutor:
    """
    Execute isolated subgraphs for complex queries.

    Provides context isolation so subgraph failures
    don't pollute parent state. Useful for:
    - Parallel sub-queries
    - Specialized analysis branches
    - Error containment

    Example:
        ```python
        executor = SubgraphExecutor(analysis_graph)

        # Execute with isolated state
        result = await executor.execute(
            initial_state={"query": "sub-query"},
            inherit_keys=["user_id", "session_id"],
            return_keys=["result", "figure"],
        )

        if result.get("success"):
            main_state["sub_result"] = result
        ```
    """

    def __init__(
        self,
        graph: StateGraph,
        checkpointer: Checkpointer | None = None,
    ):
        """
        Initialize subgraph executor.

        Args:
            graph: The graph to execute
            checkpointer: Optional checkpointer for subgraph state
        """
        self.graph = graph
        self.checkpointer = checkpointer

    async def execute(
        self,
        initial_state: dict[str, Any],
        inherit_keys: list[str] | None = None,
        return_keys: list[str] | None = None,
        parent_state: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Execute subgraph with isolated state.

        Args:
            initial_state: State to pass to subgraph
            inherit_keys: Keys to copy from parent state (if parent_state provided)
            return_keys: Keys to return from subgraph result
            parent_state: Optional parent state for inheritance

        Returns:
            Dict with:
            - "success": bool
            - "result": filtered result dict (if return_keys specified)
            - "error": error message (if failed)
        """
        # Create isolated state
        substate: dict[str, Any] = {**initial_state}

        # Inherit specified keys from parent
        if parent_state and inherit_keys:
            for key in inherit_keys:
                if key in parent_state:
                    substate[key] = parent_state[key]

        logger.debug(f"Executing subgraph with keys: {list(substate.keys())}")

        # Execute subgraph
        try:
            result = await self.graph.run(substate, checkpointer=self.checkpointer)

            # Extract return values
            if return_keys:
                filtered = {k: result.get(k) for k in return_keys if k in result}
                return {"success": True, "result": filtered}

            return {"success": True, "result": result}

        except Exception as e:
            logger.error(f"Subgraph execution failed: {e}")
            # Isolation: exception doesn't propagate full state
            return {"success": False, "error": str(e)}

    async def execute_parallel(
        self,
        states: list[dict[str, Any]],
        inherit_keys: list[str] | None = None,
        return_keys: list[str] | None = None,
        parent_state: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Execute multiple subgraph instances in parallel.

        Args:
            states: List of initial states for each execution
            inherit_keys: Keys to copy from parent state
            return_keys: Keys to return from each result
            parent_state: Optional parent state for inheritance

        Returns:
            List of result dicts (same order as input states)
        """
        import asyncio

        tasks = [
            self.execute(
                initial_state=state,
                inherit_keys=inherit_keys,
                return_keys=return_keys,
                parent_state=parent_state,
            )
            for state in states
        ]

        return await asyncio.gather(*tasks)


class SubgraphBuilder:
    """
    Helper for building subgraphs from parent graphs.

    Allows extracting a subset of nodes into a subgraph.
    """

    def __init__(self, parent_graph: StateGraph):
        """
        Initialize builder with parent graph.

        Args:
            parent_graph: Graph to extract nodes from
        """
        self.parent = parent_graph

    def extract(
        self,
        node_names: list[str],
        entry_point: str,
    ) -> StateGraph:
        """
        Extract specified nodes into a new subgraph.

        Args:
            node_names: Names of nodes to include
            entry_point: Entry point for the subgraph

        Returns:
            New StateGraph with extracted nodes
        """
        from bioquery_agents.graph import StateGraph

        subgraph = StateGraph()

        # Copy specified nodes
        for name in node_names:
            if name not in self.parent.nodes:
                raise ValueError(f"Node '{name}' not found in parent graph")
            node = self.parent.nodes[name]
            subgraph.add_node(
                name=node.name,
                handler=node.handler,
                retry_policy=node.retry_policy,
                on_failure=node.on_failure,
            )

        # Copy edges that connect extracted nodes
        for edge in self.parent.edges:
            if edge.source in node_names and (
                edge.target is None or edge.target in node_names or edge.target == "END"
            ):
                if edge.condition:
                    subgraph.add_conditional_edge(edge.source, edge.condition)
                else:
                    subgraph.add_edge(edge.source, edge.target or "END")

        subgraph.set_entry_point(entry_point)
        return subgraph
