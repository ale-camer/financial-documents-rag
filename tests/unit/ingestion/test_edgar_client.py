"""Unit tests for EdgarClient using httpx.MockTransport."""

from unittest.mock import patch

import httpx
import pytest

from src.ingestion.edgar_client import EdgarClient
from src.ingestion.exceptions import (
    EdgarAPIError,
    EdgarRateLimitError,
    EdgarRequestError,
    InvalidUserAgentError,
)


def test_user_agent_empty() -> None:
    """Verify that an empty or whitespace User-Agent raises InvalidUserAgentError."""
    with pytest.raises(InvalidUserAgentError, match="cannot be empty"):
        EdgarClient(user_agent="")

    with pytest.raises(InvalidUserAgentError, match="cannot be empty"):
        EdgarClient(user_agent="   ")


def test_user_agent_placeholder() -> None:
    """Verify that default placeholder User-Agents are rejected."""
    with pytest.raises(InvalidUserAgentError, match="default placeholder"):
        EdgarClient(user_agent="Your Name your@email.com")

    with pytest.raises(InvalidUserAgentError, match="default placeholder"):
        EdgarClient(
            user_agent="Sample Company Name AdminContact@<sample company domain>.com"
        )


def test_user_agent_no_email() -> None:
    """Verify that a User-Agent missing an email raises InvalidUserAgentError."""
    with pytest.raises(InvalidUserAgentError, match="valid contact email"):
        EdgarClient(user_agent="MyFinancialApp AdminContact")


def test_user_agent_valid() -> None:
    """Verify that a valid User-Agent initializes without error."""
    client = EdgarClient(user_agent="FinancialRAG/1.0 (dev@firm.com)")
    assert client.user_agent == "FinancialRAG/1.0 (dev@firm.com)"


@pytest.mark.asyncio
async def test_headers_sent() -> None:
    """Verify that User-Agent and Accept-Encoding headers are sent in every request."""
    captured_headers: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_headers
        captured_headers = dict(request.headers)
        return httpx.Response(200, json={"status": "ok"})

    transport = httpx.MockTransport(handler)
    async with EdgarClient(
        user_agent="FinancialRAG/1.0 (dev@firm.com)", transport=transport
    ) as client:
        await client.get_json("/test")

    assert captured_headers.get("user-agent") == "FinancialRAG/1.0 (dev@firm.com)"
    assert "gzip" in captured_headers.get("accept-encoding", "")


@pytest.mark.asyncio
async def test_get_json_200() -> None:
    """Verify that get_json parses and returns a dictionary payload on HTTP 200."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"key": "value"})

    transport = httpx.MockTransport(handler)
    async with EdgarClient(
        user_agent="FinancialRAG/1.0 (dev@firm.com)", transport=transport
    ) as client:
        result = await client.get_json("/endpoint")

    assert result == {"key": "value"}


@pytest.mark.asyncio
async def test_get_json_non_dict() -> None:
    """Verify that get_json raises EdgarAPIError when JSON payload is not an object."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=["item1", "item2"])

    transport = httpx.MockTransport(handler)
    async with EdgarClient(
        user_agent="FinancialRAG/1.0 (dev@firm.com)", transport=transport
    ) as client:
        with pytest.raises(EdgarAPIError, match="Expected JSON object"):
            await client.get_json("/endpoint")


@pytest.mark.asyncio
async def test_get_text_200() -> None:
    """Verify that get_text returns the decoded text payload on HTTP 200."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html>10-K Report</html>")

    transport = httpx.MockTransport(handler)
    async with EdgarClient(
        user_agent="FinancialRAG/1.0 (dev@firm.com)", transport=transport
    ) as client:
        result = await client.get_text("/report.htm")

    assert result == "<html>10-K Report</html>"


@pytest.mark.asyncio
async def test_get_company_submissions_cik_format() -> None:
    """Verify that CIKs are zero-padded to 10 digits in company submission paths."""
    requested_paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_paths.append(request.url.path)
        return httpx.Response(200, json={"cik": "0000320193"})

    transport = httpx.MockTransport(handler)
    async with EdgarClient(
        user_agent="FinancialRAG/1.0 (dev@firm.com)", transport=transport
    ) as client:
        await client.get_company_submissions("320193")
        await client.get_company_submissions(320193)

    assert requested_paths == [
        "/submissions/CIK0000320193.json",
        "/submissions/CIK0000320193.json",
    ]


@pytest.mark.asyncio
async def test_retry_429_eventual_success() -> None:
    """Verify that client recovers and succeeds after transient 429 responses."""
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            return httpx.Response(429, text="Rate limit exceeded")
        return httpx.Response(200, json={"success": True})

    transport = httpx.MockTransport(handler)
    async with EdgarClient(
        user_agent="FinancialRAG/1.0 (dev@firm.com)",
        transport=transport,
        backoff_factor=0.001,
    ) as client:
        data = await client.get_json("/test")

    assert attempts == 3
    assert data == {"success": True}


@pytest.mark.asyncio
async def test_retry_429_exhausted() -> None:
    """Verify that persistent 429 errors exhaust retries and raise error."""
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(429, text="Rate limit exceeded")

    transport = httpx.MockTransport(handler)
    async with EdgarClient(
        user_agent="FinancialRAG/1.0 (dev@firm.com)",
        transport=transport,
        max_retries=3,
        backoff_factor=0.001,
    ) as client:
        with pytest.raises(EdgarRateLimitError):
            await client.get_json("/test")

    assert attempts == 4


@pytest.mark.asyncio
async def test_retry_after_respected() -> None:
    """Verify that numeric Retry-After header is honored during rate limiting."""
    attempts = 0
    sleep_calls: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(
                429,
                headers={"Retry-After": "1.5"},
                text="Rate limited",
            )
        return httpx.Response(200, json={"recovered": True})

    async def fake_sleep(duration: float) -> None:
        sleep_calls.append(duration)

    transport = httpx.MockTransport(handler)
    async with EdgarClient(
        user_agent="FinancialRAG/1.0 (dev@firm.com)",
        transport=transport,
    ) as client:
        with patch("asyncio.sleep", side_effect=fake_sleep):
            result = await client.get_json("/test")

    assert attempts == 2
    assert result == {"recovered": True}
    assert 1.5 in sleep_calls


@pytest.mark.asyncio
async def test_retry_503_eventual_success() -> None:
    """Verify that transient 503 Service Unavailable retries and recovers."""
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(503, text="Service Unavailable")
        return httpx.Response(200, json={"status": "ok"})

    transport = httpx.MockTransport(handler)
    async with EdgarClient(
        user_agent="FinancialRAG/1.0 (dev@firm.com)",
        transport=transport,
        backoff_factor=0.001,
    ) as client:
        data = await client.get_json("/test")

    assert attempts == 2
    assert data == {"status": "ok"}


@pytest.mark.asyncio
async def test_500_exhausted() -> None:
    """Verify that persistent 500 errors exhaust retries and raise EdgarAPIError."""
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(500, text="Internal Server Error")

    transport = httpx.MockTransport(handler)
    async with EdgarClient(
        user_agent="FinancialRAG/1.0 (dev@firm.com)",
        transport=transport,
        max_retries=3,
        backoff_factor=0.001,
    ) as client:
        with pytest.raises(EdgarAPIError) as exc_info:
            await client.get("/test")

    assert attempts == 4
    assert exc_info.value.status_code == 500


@pytest.mark.asyncio
async def test_404_no_retry() -> None:
    """Verify that HTTP 404 fails immediately without retrying."""
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(404, text="Not Found")

    transport = httpx.MockTransport(handler)
    async with EdgarClient(
        user_agent="FinancialRAG/1.0 (dev@firm.com)",
        transport=transport,
        max_retries=3,
    ) as client:
        with pytest.raises(EdgarAPIError) as exc_info:
            await client.get("/test")

    assert attempts == 1
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_403_no_retry() -> None:
    """Verify that HTTP 403 fails immediately without retrying."""
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(403, text="Forbidden")

    transport = httpx.MockTransport(handler)
    async with EdgarClient(
        user_agent="FinancialRAG/1.0 (dev@firm.com)",
        transport=transport,
        max_retries=3,
    ) as client:
        with pytest.raises(EdgarAPIError) as exc_info:
            await client.get("/test")

    assert attempts == 1
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_timeout_exhausted() -> None:
    """Verify that persistent timeouts exhaust retries and raise EdgarRequestError."""
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        raise httpx.ConnectTimeout("Connection timed out", request=request)

    transport = httpx.MockTransport(handler)
    async with EdgarClient(
        user_agent="FinancialRAG/1.0 (dev@firm.com)",
        transport=transport,
        max_retries=3,
        backoff_factor=0.001,
    ) as client:
        with pytest.raises(EdgarRequestError):
            await client.get("/test")

    assert attempts == 4


@pytest.mark.asyncio
async def test_context_manager() -> None:
    """Verify that async with context manager properly opens and closes client."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": True})

    transport = httpx.MockTransport(handler)
    client = EdgarClient(
        user_agent="FinancialRAG/1.0 (dev@firm.com)",
        transport=transport,
    )
    assert not client._client.is_closed

    async with client as c:
        await c.get_json("/test")

    assert client._client.is_closed
