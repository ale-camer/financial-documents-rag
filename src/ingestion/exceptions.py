"""Domain exceptions for SEC EDGAR API ingestion."""


class EdgarClientError(Exception):
    """Base exception for all EDGAR client errors."""


class InvalidUserAgentError(EdgarClientError):
    """Raised when User-Agent is missing, invalid, or uses a placeholder."""


class EdgarRateLimitError(EdgarClientError):
    """Raised when rate limit retries are exhausted on HTTP 429 Too Many Requests."""


class EdgarAPIError(EdgarClientError):
    """Raised when the SEC EDGAR API returns an HTTP error."""

    def __init__(
        self,
        message: str,
        status_code: int,
        response_text: str = "",
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text


class EdgarRequestError(EdgarClientError):
    """Raised when a network transport or timeout error persists after retries."""


class FilingNotFoundError(EdgarClientError):
    """Raised when no filings match the requested criteria."""


class FilingDownloadError(EdgarClientError):
    """Raised when downloading or saving a filing document fails."""


class ParserError(EdgarClientError):
    """Raised when parsing or decoding a filing document fails."""
