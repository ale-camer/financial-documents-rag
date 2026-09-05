"""Unit tests for SectionExtractor service."""

from pathlib import Path

import pytest

from src.ingestion.exceptions import SectionExtractionError
from src.ingestion.section_extractor import SectionExtractor

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLE_PARSED_10K = FIXTURES_DIR / "sample_parsed_10k.txt"


@pytest.fixture
def extractor() -> SectionExtractor:
    """Provide a SectionExtractor instance for testing."""
    return SectionExtractor()


@pytest.fixture
def sample_text() -> str:
    """Load sample parsed 10-K document text."""
    return SAMPLE_PARSED_10K.read_text(encoding="utf-8")


def test_extract_all_supported_sections(
    extractor: SectionExtractor, sample_text: str
) -> None:
    """Verify that all 5 supported sections are extracted from complete text."""
    sections = extractor.extract_sections(sample_text)

    expected_keys = {"item_1", "item_1a", "item_7", "item_7a", "item_8"}
    assert set(sections.keys()) == expected_keys

    assert "CorePlatform" in sections["item_1"]
    assert "Macroeconomic Volatility" in sections["item_1a"]
    assert "Total revenue for fiscal year 2023" in sections["item_7"]
    assert "Interest Rate Risk" in sections["item_7a"]
    assert "Consolidated Balance Sheets" in sections["item_8"]


def test_extract_single_section(extractor: SectionExtractor, sample_text: str) -> None:
    """Verify that extract_section retrieves a specific target section."""
    item_1a = extractor.extract_section(sample_text, "item_1a")
    assert item_1a is not None
    assert "Cybersecurity and Data Privacy" in item_1a


def test_missing_section_graceful_handling(
    extractor: SectionExtractor,
) -> None:
    """Verify that missing sections are omitted without raising errors."""
    partial_text = """
    ITEM 1. BUSINESS
    We build software products.

    ITEM 8. FINANCIAL STATEMENTS
    Balance sheet numbers.
    """
    sections = extractor.extract_sections(partial_text)

    assert set(sections.keys()) == {"item_1", "item_8"}
    assert "item_1a" not in sections
    assert "item_7" not in sections

    assert extractor.extract_section(partial_text, "item_7") is None


def test_section_boundaries_no_bleed(
    extractor: SectionExtractor, sample_text: str
) -> None:
    """Verify boundaries are strictly respected with no content bleeding."""
    sections = extractor.extract_sections(sample_text)

    item_1 = sections["item_1"]
    assert "Sample Financial Corp." in item_1
    assert "ITEM 1A" not in item_1
    assert "Macroeconomic Volatility" not in item_1

    item_7 = sections["item_7"]
    assert "Total revenue for fiscal year 2023" in item_7
    assert "ITEM 7A" not in item_7
    assert "Foreign Exchange Risk" not in item_7


def test_heading_variation_matching(extractor: SectionExtractor) -> None:
    """Verify matching headings with colons, dashes, periods, and casing."""
    text_with_variants = """
    item 1: Business Overview
    Body content for item 1.

    Item 1A - Risk Factors
    Body content for item 1a.

    ITEM 7. MD&A
    Body content for item 7.
    """
    sections = extractor.extract_sections(text_with_variants)

    assert "item_1" in sections
    assert sections["item_1"] == "Body content for item 1."

    assert "item_1a" in sections
    assert sections["item_1a"] == "Body content for item 1a."

    assert "item_7" in sections
    assert sections["item_7"] == "Body content for item 7."


def test_empty_and_whitespace_input(extractor: SectionExtractor) -> None:
    """Verify empty string or whitespace returns an empty dictionary."""
    assert extractor.extract_sections("") == {}
    assert extractor.extract_sections("   \n\t  ") == {}
    assert extractor.extract_section("", "item_1") is None


def test_no_matching_headings_input(extractor: SectionExtractor) -> None:
    """Verify text without SEC headings returns an empty dictionary."""
    generic_text = "This is a press release with no Item headings whatsoever."
    assert extractor.extract_sections(generic_text) == {}
    assert extractor.extract_section(generic_text, "item_1") is None


def test_key_normalization(extractor: SectionExtractor) -> None:
    """Verify that section aliases are normalized to canonical keys."""
    assert extractor.normalize_section_name("1") == "item_1"
    assert extractor.normalize_section_name("Item 1") == "item_1"
    assert extractor.normalize_section_name("item_1") == "item_1"
    assert extractor.normalize_section_name("1A") == "item_1a"
    assert extractor.normalize_section_name("Item 7") == "item_7"
    assert extractor.normalize_section_name("7a") == "item_7a"
    assert extractor.normalize_section_name("8") == "item_8"


def test_unsupported_section_normalization(
    extractor: SectionExtractor,
) -> None:
    """Verify unsupported section name raises SectionExtractionError."""
    with pytest.raises(SectionExtractionError, match="Unsupported section"):
        extractor.normalize_section_name("item_99")

    # In extract_section it returns None gracefully
    assert extractor.extract_section("ITEM 1. Content", "item_99") is None


def test_extracted_text_is_trimmed(
    extractor: SectionExtractor, sample_text: str
) -> None:
    """Verify that extracted section text has no leading/trailing whitespace."""
    sections = extractor.extract_sections(sample_text)
    for section_text in sections.values():
        assert section_text == section_text.strip()
