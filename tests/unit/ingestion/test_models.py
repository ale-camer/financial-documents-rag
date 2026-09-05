"""Unit tests for Pydantic ingestion data models."""

import pytest
from pydantic import ValidationError

from src.ingestion.models import FilingMetadata, ParsedDocument, ParsedSection


def test_filing_metadata_valid() -> None:
    """Verify creating FilingMetadata with valid fields."""
    metadata = FilingMetadata(
        cik="0000320193",
        ticker="AAPL",
        period="2023-09-30",
        accession_number="0000320193-23-000106",
        form_type="10-K",
    )
    assert metadata.cik == "0000320193"
    assert metadata.ticker == "AAPL"
    assert metadata.period == "2023-09-30"
    assert metadata.accession_number == "0000320193-23-000106"
    assert metadata.form_type == "10-K"


def test_filing_metadata_cik_padding_int() -> None:
    """Verify integer CIK is zero-padded to 10 digits."""
    metadata = FilingMetadata(
        cik=320193,  # type: ignore[arg-type]
        period="2023-09-30",
        accession_number="0000320193-23-000106",
    )
    assert metadata.cik == "0000320193"


def test_filing_metadata_cik_padding_str() -> None:
    """Verify unpadded string CIK is zero-padded to 10 digits."""
    metadata = FilingMetadata(
        cik="320193",
        period="2023-09-30",
        accession_number="0000320193-23-000106",
    )
    assert metadata.cik == "0000320193"


def test_filing_metadata_cik_invalid_non_numeric() -> None:
    """Verify non-numeric CIK raises ValidationError."""
    with pytest.raises(ValidationError, match="must contain only digits"):
        FilingMetadata(
            cik="AAPL",
            period="2023-09-30",
            accession_number="0000320193-23-000106",
        )


def test_filing_metadata_cik_too_long() -> None:
    """Verify CIK longer than 10 digits raises ValidationError."""
    with pytest.raises(ValidationError, match="cannot exceed 10 digits"):
        FilingMetadata(
            cik="12345678901",
            period="2023-09-30",
            accession_number="0000320193-23-000106",
        )


def test_filing_metadata_cik_negative() -> None:
    """Verify negative integer CIK raises ValidationError."""
    with pytest.raises(ValidationError, match="cannot be negative"):
        FilingMetadata(
            cik=-123,  # type: ignore[arg-type]
            period="2023-09-30",
            accession_number="0000320193-23-000106",
        )


def test_filing_metadata_cik_empty() -> None:
    """Verify empty CIK raises ValidationError."""
    with pytest.raises(ValidationError, match="cannot be empty"):
        FilingMetadata(
            cik="",
            period="2023-09-30",
            accession_number="0000320193-23-000106",
        )


def test_filing_metadata_cik_invalid_type() -> None:
    """Verify non-string non-int CIK raises ValidationError."""
    with pytest.raises(ValidationError, match="must be a string or integer"):
        FilingMetadata(
            cik=[123],  # type: ignore[arg-type]
            period="2023-09-30",
            accession_number="0000320193-23-000106",
        )


@pytest.mark.parametrize(
    "invalid_acc",
    [
        "000032019323000106",
        "0000320193-23-00010",
        "0000320193-23-0001067",
        "000032019-23-000106",
        "invalid-accession-num",
    ],
)
def test_filing_metadata_accession_number_invalid(invalid_acc: str) -> None:
    """Verify malformed accession numbers raise ValidationError."""
    with pytest.raises(ValidationError, match="Invalid accession number format"):
        FilingMetadata(
            cik="0000320193",
            period="2023-09-30",
            accession_number=invalid_acc,
        )


def test_filing_metadata_ticker_capitalization() -> None:
    """Verify lowercase ticker is automatically converted to uppercase."""
    metadata = FilingMetadata(
        cik="0000320193",
        ticker="  aapl  ",
        period="2023-09-30",
        accession_number="0000320193-23-000106",
    )
    assert metadata.ticker == "AAPL"


def test_filing_metadata_ticker_none() -> None:
    """Verify ticker defaults to None and accepts None."""
    metadata = FilingMetadata(
        cik="0000320193",
        period="2023-09-30",
        accession_number="0000320193-23-000106",
    )
    assert metadata.ticker is None

    metadata_explicit = FilingMetadata(
        cik="0000320193",
        ticker=None,
        period="2023-09-30",
        accession_number="0000320193-23-000106",
    )
    assert metadata_explicit.ticker is None


def test_filing_metadata_ticker_invalid_type() -> None:
    """Verify non-string ticker raises ValidationError."""
    with pytest.raises(ValidationError, match="ticker must be a string"):
        FilingMetadata(
            cik="0000320193",
            ticker=123,  # type: ignore[arg-type]
            period="2023-09-30",
            accession_number="0000320193-23-000106",
        )


def test_filing_metadata_form_type_default_and_custom() -> None:
    """Verify form_type defaults to 10-K and normalizes to uppercase."""
    metadata_default = FilingMetadata(
        cik="0000320193",
        period="2023-09-30",
        accession_number="0000320193-23-000106",
    )
    assert metadata_default.form_type == "10-K"

    metadata_custom = FilingMetadata(
        cik="0000320193",
        period="2023-09-30",
        accession_number="0000320193-23-000106",
        form_type="10-k/a",
    )
    assert metadata_custom.form_type == "10-K/A"


def test_filing_metadata_form_type_empty() -> None:
    """Verify empty form_type raises ValidationError."""
    with pytest.raises(ValidationError, match="form_type cannot be empty"):
        FilingMetadata(
            cik="0000320193",
            period="2023-09-30",
            accession_number="0000320193-23-000106",
            form_type="  ",
        )


def test_filing_metadata_period_empty() -> None:
    """Verify empty period raises ValidationError."""
    with pytest.raises(ValidationError, match="period cannot be empty"):
        FilingMetadata(
            cik="0000320193",
            period="   ",
            accession_number="0000320193-23-000106",
        )


def test_parsed_section_auto_word_count() -> None:
    """Verify word_count is automatically computed from raw_text when omitted."""
    section = ParsedSection(
        section_name="item_1",
        raw_text="Business overview and operations across multiple sectors.",
    )
    assert section.section_name == "item_1"
    assert section.word_count == 7


def test_parsed_section_explicit_word_count() -> None:
    """Verify explicitly passed word_count is preserved."""
    section = ParsedSection(
        section_name="item_1",
        raw_text="Short text",
        word_count=50,
    )
    assert section.word_count == 50


def test_parsed_section_empty_text() -> None:
    """Verify empty raw_text results in 0 word count."""
    section = ParsedSection(
        section_name="item_7",
        raw_text="",
    )
    assert section.word_count == 0


def test_parsed_section_negative_word_count() -> None:
    """Verify negative word count raises ValidationError."""
    with pytest.raises(ValidationError, match="word_count"):
        ParsedSection(
            section_name="item_1",
            raw_text="Some text",
            word_count=-5,
        )


def test_parsed_section_name_normalization() -> None:
    """Verify section_name is stripped and lowercased."""
    section = ParsedSection(
        section_name="  ITEM_1A  ",
        raw_text="Risk factors discussion.",
    )
    assert section.section_name == "item_1a"


def test_parsed_section_empty_name() -> None:
    """Verify empty section_name raises ValidationError."""
    with pytest.raises(ValidationError, match="section_name cannot be empty"):
        ParsedSection(
            section_name="   ",
            raw_text="Some text",
        )


def test_parsed_document_get_section_found() -> None:
    """Verify retrieving existing section by name (case-insensitive)."""
    meta = FilingMetadata(
        cik="0000320193",
        period="2023-09-30",
        accession_number="0000320193-23-000106",
    )
    section_1 = ParsedSection(
        section_name="item_1",
        raw_text="Business description content.",
    )
    section_7 = ParsedSection(
        section_name="item_7",
        raw_text="MD&A financial overview and analysis.",
    )
    doc = ParsedDocument(
        metadata=meta,
        sections=[section_1, section_7],
    )

    found = doc.get_section("item_1")
    assert found is not None
    assert found.section_name == "item_1"
    assert found.raw_text == "Business description content."

    # Test case-insensitive lookup
    found_upper = doc.get_section("ITEM_7")
    assert found_upper is not None
    assert found_upper.section_name == "item_7"


def test_parsed_document_get_section_missing() -> None:
    """Verify get_section returns None when section does not exist."""
    meta = FilingMetadata(
        cik="0000320193",
        period="2023-09-30",
        accession_number="0000320193-23-000106",
    )
    doc = ParsedDocument(metadata=meta, sections=[])
    assert doc.get_section("item_1") is None


def test_parsed_document_total_word_count() -> None:
    """Verify total_word_count computes sum across all sections."""
    meta = FilingMetadata(
        cik="0000320193",
        period="2023-09-30",
        accession_number="0000320193-23-000106",
    )
    sec1 = ParsedSection(section_name="item_1", raw_text="One two three")
    sec2 = ParsedSection(section_name="item_7", raw_text="Four five six seven")
    doc = ParsedDocument(metadata=meta, sections=[sec1, sec2])

    assert sec1.word_count == 3
    assert sec2.word_count == 4
    assert doc.total_word_count == 7


def test_parsed_document_empty_sections() -> None:
    """Verify document with no sections has total_word_count of 0."""
    meta = FilingMetadata(
        cik="0000320193",
        period="2023-09-30",
        accession_number="0000320193-23-000106",
    )
    doc = ParsedDocument(metadata=meta)
    assert doc.sections == []
    assert doc.total_word_count == 0
