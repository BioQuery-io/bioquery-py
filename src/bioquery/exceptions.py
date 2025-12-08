"""BioQuery SDK exceptions."""


class BioQueryError(Exception):
    """Base exception for BioQuery SDK."""

    pass


class AuthenticationError(BioQueryError):
    """Raised when API authentication fails."""

    pass


class QueryError(BioQueryError):
    """Raised when query processing fails."""

    pass


class RateLimitError(BioQueryError):
    """Raised when API rate limit is exceeded."""

    pass
