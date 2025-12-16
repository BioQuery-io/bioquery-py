"""
bioquery-agents: Lightweight graph-based agent orchestration for Python.

Inspired by LangGraph and deepagents, but without the dependency chain.
"""

from bioquery_agents.checkpoint import Checkpointer, MemoryCheckpointer
from bioquery_agents.graph import Edge, Node, NodeStatus, StateGraph
from bioquery_agents.middleware import AgentMiddleware, MiddlewareStack
from bioquery_agents.planning import PlanningLoop, Todo, TodoStatus
from bioquery_agents.retry import RetryPolicy
from bioquery_agents.subgraph import SubgraphBuilder, SubgraphExecutor

# Consultants - import selectively to avoid requiring anthropic
# Users should import from bioquery_agents.consultants directly

__version__ = "0.1.0"

__all__ = [
    # Graph
    "StateGraph",
    "Node",
    "Edge",
    "NodeStatus",
    # Retry
    "RetryPolicy",
    # Checkpoint
    "Checkpointer",
    "MemoryCheckpointer",
    # Middleware
    "AgentMiddleware",
    "MiddlewareStack",
    # Planning
    "PlanningLoop",
    "Todo",
    "TodoStatus",
    # Subgraph
    "SubgraphBuilder",
    "SubgraphExecutor",
]
