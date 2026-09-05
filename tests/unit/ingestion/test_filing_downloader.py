"""Unit tests for FilingDownloader service."""

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import pytest

from src.ingestion.edgar_client import EdgarClient
from src.ingestion.exceptions import (
    FilingDownloadError,
    InvalidUserAgentError,
)
from src.ingestion.filing_downloader import FilingDownloader

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "submissions_sample.json"


@pytest.fixture
def sample_submissions() -> dict[str, Any]:
    """Load sample SEC submissions JSON fixture."""
    data: dict[str, Any] = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return data


def create_mock_client(
    handler: Callable[[httpx.Request], httpx.Response],
) -> EdgarClient:
    """Helper to create EdgarClient with a MockTransport."""
    transport = httpx.MockTransport(handler)
    return EdgarClient(
        user_agent="TestApp/1.0 (contact@firm.com)",
        transport=transport,
    )


@pytest.mark.asyncio
async def test_get_10k_filings_filters_forms(
    sample_submissions: dict[str, Any],
) -> None:
    """Verify that only 10-K filings are extracted, filtering out 10-Q and 8-K."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=sample_submissions)

    client = create_mock_client(handler)
    downloader = FilingDownloader(client=client)

    filings = await downloader.get_10k_filings("320193", limit=10)

    assert len(filings) == 2
    for filing in filings:
        assert filing["form"] == "10-K"

    assert filings[0]["accessionNumber"] == "0000320193-23-000106"
    assert filings[0]["primaryDocument"] == "aapl-20230930.htm"
    assert filings[1]["accessionNumber"] == "0000320193-22-000108"


@pytest.mark.asyncio
async def test_get_10k_filings_respects_limit(
    sample_submissions: dict[str, Any],
) -> None:
    """Verify that the limit parameter restricts the number of returned filings."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=sample_submissions)

    client = create_mock_client(handler)
    downloader = FilingDownloader(client=client)

    filings = await downloader.get_10k_filings("320193", limit=1)

    assert len(filings) == 1
    assert filings[0]["accessionNumber"] == "0000320193-23-000106"


@pytest.mark.asyncio
async def test_get_10k_filings_no_results() -> None:
    """Verify that an empty list is returned when no 10-K filings exist."""
    payload = {
        "filings": {
            "recent": {
                "form": ["10-Q", "8-K"],
                "accessionNumber": ["001", "002"],
                "filingDate": ["2023-01-01", "2023-02-01"],
                "reportDate": ["2023-01-01", "2023-02-01"],
                "primaryDocument": ["doc1.htm", "doc2.htm"],
            }
        }
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    client = create_mock_client(handler)
    downloader = FilingDownloader(client=client)

    filings = await downloader.get_10k_filings("320193", limit=5)
    assert filings == []


@pytest.mark.asyncio
async def test_get_10k_filings_missing_recent_field() -> None:
    """Verify graceful handling when submissions JSON lacks recent filings key."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"filings": {}})

    client = create_mock_client(handler)
    downloader = FilingDownloader(client=client)

    filings = await downloader.get_10k_filings("320193", limit=5)
    assert filings == []


@pytest.mark.asyncio
async def test_download_filing_document_success(tmp_path: Path) -> None:
    """Verify downloading and saving a primary document HTML file."""
    doc_html = "<html><body>Apple 10-K Content</body></html>"

    def handler(request: httpx.Request) -> httpx.Response:
        expected_url = (
            "https://www.sec.gov/Archives/edgar/data/"
            "320193/000032019323000106/aapl-20230930.htm"
        )
        if str(request.url) == expected_url:
            return httpx.Response(200, text=doc_html)
        return httpx.Response(404, text="Not Found")

    client = create_mock_client(handler)
    downloader = FilingDownloader(client=client, storage_dir=tmp_path)

    saved_path = await downloader.download_filing_document(
        cik="320193",
        accession_number="0000320193-23-000106",
        primary_document="aapl-20230930.htm",
    )

    expected_path = (
        tmp_path / "0000320193" / "0000320193-23-000106" / "aapl-20230930.htm"
    )
    assert saved_path == expected_path
    assert saved_path.is_file()
    assert saved_path.read_text(encoding="utf-8") == doc_html


@pytest.mark.asyncio
async def test_download_filing_document_creates_directories(
    tmp_path: Path,
) -> None:
    """Verify target directory hierarchy is automatically created."""
    nested_storage = tmp_path / "deep" / "nested" / "storage"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html>10-K</html>")

    client = create_mock_client(handler)
    downloader = FilingDownloader(client=client, storage_dir=nested_storage)

    saved_path = await downloader.download_filing_document(
        cik="12345",
        accession_number="0000012345-23-000001",
        primary_document="filing.htm",
    )

    assert saved_path.is_file()
    assert nested_storage.is_dir()


@pytest.mark.asyncio
async def test_download_filing_document_error(tmp_path: Path) -> None:
    """Verify FilingDownloadError is raised when the HTTP request fails."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="Not Found")

    client = create_mock_client(handler)
    downloader = FilingDownloader(client=client, storage_dir=tmp_path)

    with pytest.raises(FilingDownloadError, match="Failed to download"):
        await downloader.download_filing_document(
            cik="320193",
            accession_number="0000320193-23-000106",
            primary_document="missing.htm",
        )


@pytest.mark.asyncio
async def test_download_recent_10k_orchestration(
    tmp_path: Path,
    sample_submissions: dict[str, Any],
) -> None:
    """Verify coordinating metadata fetch and batch document downloading."""

    def handler(request: httpx.Request) -> httpx.Response:
        if "/submissions/CIK0000320193.json" in str(request.url):
            return httpx.Response(200, json=sample_submissions)
        if "aapl-20230930.htm" in str(request.url):
            return httpx.Response(200, text="<html>2023 10-K</html>")
        if "aapl-20220924.htm" in str(request.url):
            return httpx.Response(200, text="<html>2022 10-K</html>")
        return httpx.Response(404, text="Not Found")

    client = create_mock_client(handler)
    downloader = FilingDownloader(client=client, storage_dir=tmp_path)

    paths = await downloader.download_recent_10k("320193", limit=2)

    assert len(paths) == 2
    for path in paths:
        assert path.is_file()

    assert paths[0].name == "aapl-20230930.htm"
    assert paths[1].name == "aapl-20220924.htm"


def test_custom_storage_dir(tmp_path: Path) -> None:
    """Verify that custom storage_dir path is respected."""
    custom_dir = tmp_path / "custom_data"
    client = create_mock_client(lambda r: httpx.Response(200))
    downloader = FilingDownloader(client=client, storage_dir=custom_dir)

    assert downloader.storage_dir == custom_dir


def test_init_without_client_missing_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify error when initializing without client and no env var set."""
    monkeypatch.delenv("SEC_EDGAR_USER_AGENT", raising=False)
    with pytest.raises(InvalidUserAgentError, match="SEC_EDGAR_USER_AGENT"):
        FilingDownloader(client=None)


def test_init_without_client_with_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify initialization without client when env var is present."""
    monkeypatch.setenv("SEC_EDGAR_USER_AGENT", "FirmApp/1.0 (contact@firm.com)")
    downloader = FilingDownloader(client=None)
    assert downloader.client.user_agent == "FirmApp/1.0 (contact@firm.com)"
    assert downloader._owns_client is True


@pytest.mark.asyncio
async def test_context_manager(tmp_path: Path) -> None:
    """Verify that async with context manager cleanly exits."""
    client = create_mock_client(lambda r: httpx.Response(200))
    async with FilingDownloader(client=client, storage_dir=tmp_path) as downloader:
        assert downloader.storage_dir == tmp_path
