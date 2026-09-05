"""Downloader service for SEC EDGAR 10-K filing documents."""

import os
from pathlib import Path
from types import TracebackType
from typing import Any

from src.ingestion.edgar_client import EdgarClient
from src.ingestion.exceptions import (
    EdgarClientError,
    FilingDownloadError,
    InvalidUserAgentError,
)


class FilingDownloader:
    """Service to locate, filter, and download 10-K filings from SEC EDGAR."""

    def __init__(
        self,
        client: EdgarClient | None = None,
        storage_dir: Path | str = "data/raw",
    ) -> None:
        """Initialize the filing downloader.

        Args:
            client: Optional EdgarClient instance. If None, instantiates one
                using the SEC_EDGAR_USER_AGENT environment variable.
            storage_dir: Root directory path where filings will be stored.

        Raises:
            InvalidUserAgentError: If client is None and SEC_EDGAR_USER_AGENT
                is not configured.
        """
        self.storage_dir = Path(storage_dir)
        self._owns_client = False

        if client is not None:
            self.client = client
        else:
            user_agent = os.getenv("SEC_EDGAR_USER_AGENT", "")
            if not user_agent:
                raise InvalidUserAgentError(
                    "SEC_EDGAR_USER_AGENT environment variable must be set "
                    "when client is not provided"
                )
            self.client = EdgarClient(user_agent=user_agent)
            self._owns_client = True

    async def get_10k_filings(
        self,
        cik: str | int,
        limit: int = 1,
    ) -> list[dict[str, Any]]:
        """Fetch and filter the most recent 10-K submissions for a company.

        Args:
            cik: SEC Central Index Key (string or integer).
            limit: Maximum number of recent 10-K filings to return.

        Returns:
            list[dict[str, Any]]: List of metadata dictionaries for 10-K filings.
        """
        cik_str = str(cik).strip().zfill(10)
        submissions = await self.client.get_company_submissions(cik_str)

        recent = submissions.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        accession_numbers = recent.get("accessionNumber", [])
        filing_dates = recent.get("filingDate", [])
        report_dates = recent.get("reportDate", [])
        primary_docs = recent.get("primaryDocument", [])

        results: list[dict[str, Any]] = []
        for i, form in enumerate(forms):
            if form == "10-K":
                results.append(
                    {
                        "accessionNumber": accession_numbers[i],
                        "filingDate": (
                            filing_dates[i] if i < len(filing_dates) else ""
                        ),
                        "reportDate": (
                            report_dates[i] if i < len(report_dates) else ""
                        ),
                        "form": form,
                        "primaryDocument": (
                            primary_docs[i] if i < len(primary_docs) else ""
                        ),
                    }
                )
                if len(results) == limit:
                    break

        return results

    async def download_filing_document(
        self,
        cik: str | int,
        accession_number: str,
        primary_document: str,
    ) -> Path:
        """Download a filing primary document and store it locally.

        Args:
            cik: SEC Central Index Key.
            accession_number: Filing accession number (e.g. '0000320193-23-000106').
            primary_document: Name of primary doc file (e.g. 'aapl-20230930.htm').

        Returns:
            Path: Local path to the saved filing document.

        Raises:
            FilingDownloadError: If download fails or file cannot be written.
        """
        cik_str = str(cik).strip()
        cik_int = str(int(cik_str))
        accession_clean = accession_number.replace("-", "")
        url = (
            f"https://www.sec.gov/Archives/edgar/data/"
            f"{cik_int}/{accession_clean}/{primary_document}"
        )

        try:
            content = await self.client.get_text(url)
            dest_dir = self.storage_dir / cik_str.zfill(10) / accession_number
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest_file = dest_dir / primary_document
            dest_file.write_text(content, encoding="utf-8")
            return dest_file
        except (EdgarClientError, OSError) as exc:
            raise FilingDownloadError(
                f"Failed to download filing document for CIK {cik_str}: {exc}"
            ) from exc

    async def download_recent_10k(
        self,
        cik: str | int,
        limit: int = 1,
    ) -> list[Path]:
        """Download the most recent N 10-K primary documents for a company.

        Args:
            cik: SEC Central Index Key.
            limit: Number of recent 10-K filings to download.

        Returns:
            list[Path]: List of local file paths for the downloaded documents.
        """
        filings = await self.get_10k_filings(cik, limit=limit)
        downloaded_paths: list[Path] = []

        for filing in filings:
            path = await self.download_filing_document(
                cik=cik,
                accession_number=filing["accessionNumber"],
                primary_document=filing["primaryDocument"],
            )
            downloaded_paths.append(path)

        return downloaded_paths

    async def close(self) -> None:
        """Close client connection pool if owned by this downloader."""
        if self._owns_client:
            await self.client.close()

    async def __aenter__(self) -> "FilingDownloader":
        """Enter async context manager."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit async context manager and close client if owned."""
        await self.close()
