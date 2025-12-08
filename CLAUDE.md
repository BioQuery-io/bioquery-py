# BioQuery Python SDK

Python client library for the BioQuery API.

## Installation

```bash
pip install bioquery
```

## Quick Start

```python
import bioquery

# Initialize client
client = bioquery.Client(api_key="your-api-key")

# Submit a query
card = client.query("Is DDR1 expression higher in KIRP vs KIRC?")

# Access results
print(card.answer)
print(card.statistics)

# Get the plot
card.show_figure()
card.save_figure("ddr1_comparison.png")

# Export data
card.to_dataframe()
card.to_json()
```

## Project Structure

```
sdk-python/
├── src/
│   └── bioquery/
│       ├── __init__.py        # Package exports
│       ├── client.py          # BioQueryClient class
│       ├── models.py          # Pydantic models (QueryCard, etc.)
│       ├── exceptions.py      # Custom exceptions
│       └── utils.py           # Helper functions
├── tests/
│   ├── __init__.py
│   ├── test_client.py
│   └── test_models.py
├── examples/
│   └── basic_usage.py
├── pyproject.toml             # Package metadata & dependencies
├── README.md
├── LICENSE
└── CLAUDE.md                  # This file
```

## Key Classes

### BioQueryClient (`src/bioquery/client.py`)
Main client for API interaction:
- `query(question: str) -> QueryCard` - Submit natural language query
- `get_card(card_id: str) -> QueryCard` - Retrieve existing card
- `stream_query(question: str, callback) -> QueryCard` - Stream with progress

### QueryCard (`src/bioquery/models.py`)
Represents a Query Card result:
- `card_id: str` - Unique identifier
- `question: str` - Original question
- `answer: str` - Natural language answer
- `interpretation: str` - How BioQuery understood the query
- `figure: PlotlyFigure` - Interactive visualization
- `statistics: dict` - Statistical results
- `sql_query: str` - Executed BigQuery SQL
- `methods_text: str` - Grant-ready methods

Methods:
- `show_figure()` - Display in notebook
- `save_figure(path, format)` - Export figure
- `to_dataframe()` - Get data as pandas DataFrame
- `to_json()` - Export full card as JSON

## Development

```bash
# Setup
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black src tests
isort src tests

# Type check
mypy src
```

## API Endpoints Used

| Method | Path | Description |
|--------|------|-------------|
| POST | `/query` | Submit query |
| GET | `/cards/{id}` | Get card by ID |

## Environment Variables

```bash
BIOQUERY_API_KEY=your-api-key
BIOQUERY_API_URL=https://api.bioquery.io  # Optional, defaults to production
```

## Publishing

```bash
# Build
python -m build

# Upload to PyPI
python -m twine upload dist/*
```

## Error Handling

```python
from bioquery.exceptions import (
    BioQueryError,        # Base exception
    AuthenticationError,  # Invalid API key
    QueryError,           # Query processing failed
    RateLimitError,       # Too many requests
)
```

## Async Support

```python
import asyncio
from bioquery import AsyncClient

async def main():
    client = AsyncClient(api_key="...")
    card = await client.query("...")

asyncio.run(main())
```
