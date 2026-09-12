"""Asynchronous client for the SEC EDGAR API with rate limiting and retry logic."""

import asyncio
import random
import re
from types import TracebackType
from typing import Any

import httpx

from src.ingestion.exceptions import (
    EdgarAPIError,
    EdgarRateLimitError,
    EdgarRequestError,
    InvalidUserAgentError,
)
from src.ingestion.rate_limiter import AsyncTokenBucket

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")

RETRY_STATUS_CODES = {429, 500, 502, 503, 504}


class EdgarClient:
    """Async client for SEC EDGAR API respecting the fair access policy."""

    def __init__(
        self,
        user_agent: str,
        base_url: str = "https://data.sec.gov",
        rate_limit_per_sec: float = 10.0,
        max_retries: int = 3,
        backoff_factor: float = 1.0,
        timeout: float = 30.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        """Initialize the SEC EDGAR client.

        Args:
            user_agent: User-Agent header (required: must include contact email).
            base_url: SEC EDGAR base URL (default: "https://data.sec.gov").
            rate_limit_per_sec: Allowed requests per second (default: 10.0).
            max_retries: Maximum number of retries for transient errors (default: 3).
            backoff_factor: Multiplier for exponential backoff (default: 1.0).
            timeout: Request timeout in seconds (default: 30.0).
            transport: Optional custom httpx transport for testing.

        Raises:
            InvalidUserAgentError: If user_agent is missing, invalid, or
                uses a default placeholder.
        """
        self._validate_user_agent(user_agent)
        self.user_agent = user_agent
        self.base_url = base_url.rstrip("/")
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.timeout = timeout

        self.rate_limiter = AsyncTokenBucket(
            rate=rate_limit_per_sec, capacity=rate_limit_per_sec
        )

        self._tickers_cache: dict[str, str] | None = None

        headers = {
            "User-Agent": self.user_agent,
            "Accept-Encoding": "gzip, deflate",
        }

        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=headers,
            timeout=httpx.Timeout(self.timeout),
            transport=transport,
        )

    @staticmethod
    def _validate_user_agent(user_agent: str) -> None:
        """Validate that the User-Agent complies with SEC EDGAR policy."""
        if not user_agent or not user_agent.strip():
            raise InvalidUserAgentError("User-Agent cannot be empty")

        ua_lower = user_agent.strip().lower()
        if (
            "your name your@email.com" in ua_lower
            or "your@email.com" in ua_lower
            or "<sample company domain>" in ua_lower
        ):
            raise InvalidUserAgentError(
                f"User-Agent cannot be a default placeholder: {user_agent}"
            )

        if not EMAIL_REGEX.search(user_agent):
            raise InvalidUserAgentError(
                "User-Agent must contain a valid contact email address"
            )

    async def get(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Execute an HTTP GET request with rate limiting and exponential retry logic.

        Args:
            url: Target endpoint path or full URL.
            params: Optional query parameters.
            headers: Optional request-specific headers.

        Returns:
            httpx.Response: The successful HTTP response.

        Raises:
            EdgarRateLimitError: If HTTP 429 persists after retries.
            EdgarAPIError: On non-recoverable HTTP status codes (4xx, 5xx).
            EdgarRequestError: On transport/timeout errors after retries.
        """
        for attempt in range(self.max_retries + 1):
            await self.rate_limiter.acquire()
            try:
                response = await self._client.get(url, params=params, headers=headers)
            except (httpx.TransportError, httpx.TimeoutException) as exc:
                if attempt == self.max_retries:
                    raise EdgarRequestError(
                        f"Request failed after {self.max_retries} retries: {exc}"
                    ) from exc
                delay = self.backoff_factor * (2**attempt) + random.uniform(0, 0.5)
                await asyncio.sleep(delay)
                continue

            if response.status_code < 400:
                return response

            if response.status_code == 429:
                if attempt == self.max_retries:
                    raise EdgarRateLimitError(
                        "Rate limit exceeded (HTTP 429) and retries exhausted"
                    )
                retry_after = response.headers.get("Retry-After")
                if retry_after:
                    try:
                        sleep_time = float(retry_after)
                    except ValueError:
                        delay = self.backoff_factor * (2**attempt)
                        sleep_time = delay + random.uniform(0, 0.5)
                else:
                    delay = self.backoff_factor * (2**attempt)
                    sleep_time = delay + random.uniform(0, 0.5)
                await asyncio.sleep(sleep_time)
                continue

            if response.status_code in RETRY_STATUS_CODES:
                if attempt == self.max_retries:
                    raise EdgarAPIError(
                        f"Server error {response.status_code} "
                        f"persisting after {self.max_retries} retries",
                        status_code=response.status_code,
                        response_text=response.text,
                    )
                delay = self.backoff_factor * (2**attempt) + random.uniform(0, 0.5)
                await asyncio.sleep(delay)
                continue

            raise EdgarAPIError(
                f"HTTP error {response.status_code}: {response.text}",
                status_code=response.status_code,
                response_text=response.text,
            )

        raise EdgarAPIError(
            "Unexpected end of retry loop",
            status_code=500,
        )

    async def get_json(
        self, url: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Fetch an endpoint and parse the response as JSON.

        Args:
            url: Target endpoint path or full URL.
            params: Optional query parameters.

        Returns:
            dict[str, Any]: Parsed JSON payload.
        """
        response = await self.get(url, params=params)
        data = response.json()
        if not isinstance(data, dict):
            raise EdgarAPIError(
                f"Expected JSON object response, got {type(data).__name__}",
                status_code=response.status_code,
                response_text=response.text,
            )
        return data

    async def get_text(self, url: str, params: dict[str, Any] | None = None) -> str:
        """Fetch an endpoint and return the decoded text content.

        Args:
            url: Target endpoint path or full URL.
            params: Optional query parameters.

        Returns:
            str: Decoded response text.
        """
        response = await self.get(url, params=params)
        return response.text

    async def get_company_submissions(self, cik: str | int) -> dict[str, Any]:
        """Fetch company submission history by CIK number.

        Args:
            cik: SEC Central Index Key (string or integer).
                Will be zero-padded to 10 digits.

        Returns:
            dict[str, Any]: Company submission metadata.
        """
        cik_str = str(cik).strip().zfill(10)
        return await self.get_json(f"/submissions/CIK{cik_str}.json")

    async def get_cik_from_ticker(self, ticker: str) -> str:
        """Resolve a company ticker to its zero-padded CIK.

        Args:
            ticker: Company ticker symbol (e.g., AAPL).

        Returns:
            str: 10-digit zero-padded CIK.

        Raises:
            ValueError: If the ticker is not found.
        """
        if self._tickers_cache is None:
            url = "https://www.sec.gov/files/company_tickers.json"
            data = await self.get_json(url)
            self._tickers_cache = {
                entry["ticker"].upper(): str(entry["cik_str"]).zfill(10)
                for entry in data.values()
            }

        ticker_upper = ticker.upper()
        if ticker_upper not in self._tickers_cache:
            raise ValueError(f"Ticker '{ticker}' not found in SEC database.")

        return self._tickers_cache[ticker_upper]

    async def close(self) -> None:
        """Close the underlying HTTP client session."""
        await self._client.aclose()

    async def __aenter__(self) -> "EdgarClient":
        """Enter the async context manager."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit the async context manager and close connection pool."""
        await self.close()
