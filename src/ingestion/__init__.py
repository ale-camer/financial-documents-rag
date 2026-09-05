"""SEC EDGAR ingestion package."""

from src.ingestion.edgar_client import EdgarClient
from src.ingestion.exceptions import (
    EdgarAPIError,
    EdgarClientError,
    EdgarRateLimitError,
    EdgarRequestError,
    FilingDownloadError,
    FilingNotFoundError,
    InvalidUserAgentError,
    ParserError,
    SectionExtractionError,
)
from src.ingestion.filing_downloader import FilingDownloader
from src.ingestion.html_parser import TenKParser
from src.ingestion.models import FilingMetadata, ParsedDocument, ParsedSection
from src.ingestion.rate_limiter import AsyncTokenBucket
from src.ingestion.section_extractor import SectionExtractor

__all__ = [
    "AsyncTokenBucket",
    "EdgarAPIError",
    "EdgarClient",
    "EdgarClientError",
    "EdgarRateLimitError",
    "EdgarRequestError",
    "FilingDownloadError",
    "FilingDownloader",
    "FilingMetadata",
    "FilingNotFoundError",
    "InvalidUserAgentError",
    "ParsedDocument",
    "ParsedSection",
    "ParserError",
    "SectionExtractionError",
    "SectionExtractor",
    "TenKParser",
]
