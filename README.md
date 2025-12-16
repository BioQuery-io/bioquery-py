# bioquery-agents

Lightweight graph-based agent orchestration for Python. Inspired by [LangGraph](https://langchain-ai.github.io/langgraph/) and [deepagents](https://pypi.org/project/deepagents/), but without the dependency chain.

## Features

- **StateGraph**: Define execution flows as directed graphs with conditional routing
- **RetryPolicy**: Exponential backoff with configurable retry conditions
- **Checkpointer**: State persistence for resumable execution and human-in-the-loop
- **Middleware**: Composable extensions for tool interception and state modification
- **PlanningLoop**: Multi-step task decomposition and tracking
- **SubgraphExecutor**: Isolated execution for parallel sub-queries

## Installation

```bash
pip install bioquery-agents
```

Or for development:

```bash
git clone https://github.com/BioQuery-io/bioquery-agents.git
cd bioquery-agents
pip install -e ".[dev]"
```

## Quick Start

```python
from bioquery_agents import StateGraph, RetryPolicy

# Define node handlers
async def parse_query(state: dict) -> dict:
    state["parsed"] = {"intent": "analyze", "gene": "TP53"}
    return state

async def fetch_data(state: dict) -> dict:
    # Fetch data based on parsed intent
    state["data"] = {"expression": [1.2, 3.4, 5.6]}
    return state

async def generate_response(state: dict) -> dict:
    state["response"] = f"Found data for {state['parsed']['gene']}"
    return state

# Create graph
graph = StateGraph()
graph.add_node("parse", parse_query)
graph.add_node("fetch", fetch_data, retry_policy=RetryPolicy(max_attempts=3))
graph.add_node("respond", generate_response)

graph.add_edge("parse", "fetch")
graph.add_edge("fetch", "respond")
graph.add_edge("respond", "END")
graph.set_entry_point("parse")

# Execute
result = await graph.run({"query": "What is TP53 expression?"})
print(result["response"])
```

## Core Components

### StateGraph

The state graph is the core abstraction for defining execution flows:

```python
from bioquery_agents import StateGraph, NodeStatus

graph = StateGraph()

# Add nodes with optional retry policies
graph.add_node("step1", handler_func)
graph.add_node("step2", handler_func, retry_policy=my_policy)
graph.add_node("step3", handler_func, on_failure="recovery")  # Redirect on failure

# Add edges
graph.add_edge("step1", "step2")  # Unconditional
graph.add_conditional_edge("step2", route_function)  # Based on state

# Execute
result = await graph.run(initial_state, checkpointer=my_checkpointer)
```

### RetryPolicy

Configure automatic retries with exponential backoff:

```python
from bioquery_agents import RetryPolicy

policy = RetryPolicy(
    max_attempts=3,
    initial_interval=1.0,
    backoff_multiplier=2.0,
    max_interval=30.0,
    retry_on=(TimeoutError, APIError),
)
```

### Checkpointer

Persist state for resumable execution:

```python
from bioquery_agents import MemoryCheckpointer

# For development
checkpointer = MemoryCheckpointer(ttl_seconds=3600)

# Execute with checkpointing
result = await graph.run(
    {"thread_id": "unique-id", "query": "..."},
    checkpointer=checkpointer,
)

# Resume from checkpoint
result = await graph.run(
    {"thread_id": "unique-id"},  # Same thread_id
    checkpointer=checkpointer,
)
```

### PlanningLoop

Decompose complex queries into steps:

```python
from bioquery_agents import PlanningLoop, TodoStatus

loop = PlanningLoop(max_iterations=10)
loop.set_todos([
    "Parse user query",
    "Fetch relevant data",
    "Generate visualization",
    "Create response",
])

while loop.can_continue():
    todo = loop.get_next_pending()
    loop.mark_in_progress(todo.id)

    try:
        result = await execute_step(todo.description)
        loop.mark_complete(todo.id, result)
    except Exception as e:
        loop.mark_failed(todo.id, str(e))
```

### Middleware

Extend agent behavior with composable middleware:

```python
from bioquery_agents import AgentMiddleware
from bioquery_agents.middleware import MiddlewareStack

class LoggingMiddleware(AgentMiddleware):
    async def pre_invoke(self, state: dict) -> dict:
        print(f"Starting with: {state.keys()}")
        return state

    async def post_invoke(self, state: dict) -> dict:
        print(f"Finished with status: {state.get('_node_status')}")
        return state

stack = MiddlewareStack([LoggingMiddleware()])
state = await stack.apply_pre_invoke(state)
```

### SubgraphExecutor

Execute isolated subgraphs for parallel processing:

```python
from bioquery_agents import StateGraph
from bioquery_agents.subgraph import SubgraphExecutor

executor = SubgraphExecutor(analysis_graph)

# Execute with isolation
result = await executor.execute(
    initial_state={"query": "sub-query"},
    inherit_keys=["user_id"],  # From parent state
    return_keys=["result"],    # Filter output
    parent_state=main_state,
)

# Parallel execution
results = await executor.execute_parallel([
    {"query": "query1"},
    {"query": "query2"},
    {"query": "query3"},
])
```

## Design Philosophy

This library implements patterns from LangGraph and deepagents without the heavy dependency chain:

- **Zero LLM dependencies**: No LangChain, OpenAI, or Anthropic SDKs required
- **Minimal deps**: Only `pydantic>=2.0`
- **Async-first**: All operations are async for non-blocking execution
- **Type-safe**: Full type hints with mypy strict mode
- **Extensible**: Abstract base classes for custom implementations

## License

MIT

## Contributing

Contributions welcome! Please read our contributing guidelines and submit PRs to the `main` branch.
