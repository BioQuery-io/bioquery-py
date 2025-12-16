# bioquery-agents

Lightweight graph-based agent orchestration for Python.

**Repository:** Private (BioQuery-io/bioquery-agents)

## Project Structure

```
agents/
├── src/bioquery_agents/
│   ├── __init__.py        # Package exports
│   ├── graph.py           # StateGraph, Node, Edge, NodeStatus
│   ├── retry.py           # RetryPolicy
│   ├── checkpoint.py      # Checkpointer ABC, MemoryCheckpointer
│   ├── middleware.py      # AgentMiddleware, MiddlewareStack
│   ├── planning.py        # PlanningLoop, Todo, TodoStatus
│   ├── subgraph.py        # SubgraphExecutor, SubgraphBuilder
│   └── consultants/       # Domain expert consultants (ADR-0013)
│       ├── __init__.py
│       ├── base.py        # DomainConsultant base class
│       ├── definitions.py # Consultant prompts (proprietary)
│       ├── orchestrator.py # ConsultantOrchestrator
│       ├── schemas.py     # Request/response models
│       └── tool.py        # consult_expert tool definition
├── tests/
│   ├── test_graph.py
│   ├── test_checkpoint.py
│   ├── test_consultants.py  # 38 tests for consultants
│   └── ...
├── pyproject.toml
└── README.md
```

## Key Components

| Component | Purpose |
|-----------|---------|
| `StateGraph` | Directed graph for agent execution with conditional routing |
| `RetryPolicy` | Exponential backoff with configurable exception handling |
| `Checkpointer` | State persistence for resumable execution |
| `AgentMiddleware` | Composable extensions for tool interception |
| `PlanningLoop` | Multi-step task decomposition and tracking |
| `SubgraphExecutor` | Isolated execution for parallel sub-queries |
| `consultants` | Domain expert agents for statistics, clinical, immunology, genomics |

## Design Principles

1. **Zero LLM dependencies** - Core package has no LangChain, OpenAI, or Anthropic SDKs
2. **Minimal external deps** - Only `pydantic>=2.0` for core; `anthropic` optional for consultants
3. **Async-first** - All operations are async
4. **Type-safe** - Full type hints, mypy strict
5. **Protocol-based** - ABCs for Checkpointer, AgentMiddleware

## Consultants Module

The `consultants` subpackage provides domain expert agents (ADR-0013):

```python
from bioquery_agents.consultants import get_orchestrator

orchestrator = get_orchestrator()

# Single consultation
response = await orchestrator.consult(
    consultant_name="statistics",
    question="What test for comparing two groups?",
    context={"n_samples": 50},
)

# Parallel consultation
responses = await orchestrator.consult_parallel(
    consultant_names=["statistics", "clinical"],
    question="Reviewing survival analysis",
    context={"analysis_type": "survival"},
)

# Auto-detect which consultants to use
recommended = orchestrator.should_consult("survival_analysis", context)
```

**Available consultants:**
- `statistics` - Test selection, multiple testing, effect sizes
- `clinical` - Staging, treatment context, clinical significance
- `immunology` - TME, checkpoints, immunotherapy signatures
- `genomics` - Gene function, pathways, variant interpretation

## Quick Commands

```bash
# Install for development
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=bioquery_agents

# Type checking
mypy src/

# Linting
ruff check src/ tests/

# Format
ruff format src/ tests/
```

## Usage in BioQuery API

This package is used by the BioQuery API for query orchestration:

```python
# In api/app/orchestration/bioquery_graph.py
from bioquery_agents import StateGraph, RetryPolicy
from bioquery_agents.checkpoint import SupabaseCheckpointer  # Custom impl

graph = StateGraph()
graph.add_node("parse", parse_query, retry_policy=CLAUDE_RETRY)
graph.add_node("validate", validate_inputs)
graph.add_node("fetch", fetch_data, retry_policy=BIGQUERY_RETRY)
# ...
```

## Related Documentation

- [ADR-0012: Graph-Based Orchestration](https://github.com/BioQuery-io/.github-private/wiki/ADR-0012-Graph-Based-Orchestration)
- [ADR-0011: Advanced API and Agent Patterns](https://github.com/BioQuery-io/.github-private/wiki/ADR-0011-Advanced-API-and-Agent-Patterns)

## CI/CD

- **GitHub Actions**: Runs on push/PR to main
- **Tests**: pytest with coverage on Python 3.11, 3.12
- **Linting**: ruff check + format
- **Type checking**: mypy strict
- **Publishing**: Auto-publish to PyPI on version bump
