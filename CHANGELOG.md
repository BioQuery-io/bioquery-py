# 1.0.0 (2025-12-11)


### Bug Fixes

* resolve ruff lint errors ([944e3b5](https://github.com/BioQuery-io/bioquery-py/commit/944e3b576391254f8a7cceb53a169bf33bf92a66))

# Changelog

All notable changes to the BioQuery Python SDK will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- (No unreleased changes yet)

## [0.1.0] - 2025-12-08

### Added
- Initial release
- `BioQueryClient` class for API interaction
- `QueryCard` dataclass for query results
- Synchronous and async support
- Methods:
  - `query()` - Submit natural language queries
  - `get_card()` - Retrieve existing cards
  - `get_sql()` - Get SQL for reproducibility
  - `get_methods()` - Get publication-ready methods text
  - `get_figure()` - Get Plotly figure data
- Error handling with custom exceptions
- Type hints throughout
- Comprehensive docstrings

[Unreleased]: https://github.com/BioQuery-io/bioquery-py/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/BioQuery-io/bioquery-py/releases/tag/v0.1.0
