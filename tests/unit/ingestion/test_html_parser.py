"""Unit tests for TenKParser HTML and inline XBRL parser."""

from pathlib import Path

import pytest

from src.ingestion.exceptions import ParserError
from src.ingestion.html_parser import TenKParser

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLE_10K_PATH = FIXTURES_DIR / "sample_10k.html"
SAMPLE_IXBRL_PATH = FIXTURES_DIR / "sample_10k_ixbrl.htm"


@pytest.fixture
def parser() -> TenKParser:
    """Provide a TenKParser instance for testing."""
    return TenKParser()


def test_parse_raw_bytes_and_string(parser: TenKParser) -> None:
    """Verify parser accepts both bytes and string with identical output."""
    html = "<html><body><p>Standard paragraph content.</p></body></html>"
    result_str = parser.parse(html)
    result_bytes = parser.parse(html.encode("utf-8"))

    assert result_str == "Standard paragraph content."
    assert result_str == result_bytes


def test_strip_script_and_style(parser: TenKParser) -> None:
    """Verify script and style blocks and their contents are stripped."""
    html = """
    <html>
    <head>
        <script>var bad = 'should be removed';</script>
        <style>.remove-me { display: none; }</style>
    </head>
    <body>
        <p>Visible filing content.</p>
    </body>
    </html>
    """
    result = parser.parse(html)

    assert "Visible filing content." in result
    assert "bad" not in result
    assert "remove-me" not in result


def test_handle_inline_xbrl_tags(parser: TenKParser) -> None:
    """Verify ix:header/hidden are stripped but ix:nonNumeric content is kept."""
    result = parser.parse_file(SAMPLE_IXBRL_PATH)

    # Hidden metadata stripped
    assert "Hidden metadata text" not in result

    # NonNumeric tags unwrapped and text preserved
    assert "Apple Inc." in result
    assert "Apple designs, manufactures, and markets smartphones" in result
    assert "383285" in result


def test_preserve_section_headers(parser: TenKParser) -> None:
    """Verify that Item headings appear distinctly on their own lines."""
    result = parser.parse_file(SAMPLE_10K_PATH)
    lines = [line.strip() for line in result.split("\n") if line.strip()]

    assert "ITEM 1. BUSINESS" in lines
    assert "ITEM 1A. RISK FACTORS" in lines
    assert any("ITEM 7." in line for line in lines)
    assert any("ITEM 8." in line for line in lines)


def test_strip_table_of_contents(parser: TenKParser) -> None:
    """Verify TOC dot leaders and standalone TOC anchors are removed."""
    result = parser.parse_file(SAMPLE_10K_PATH)

    # Check dot leaders are gone
    assert not any("...." in line for line in result.split("\n"))

    # Check standalone TOC text is removed
    lines = [line.strip().lower() for line in result.split("\n")]
    assert "table of contents" not in lines


def test_strip_exhibit_index(parser: TenKParser) -> None:
    """Verify exhibit index section at document end is removed."""
    result = parser.parse_file(SAMPLE_10K_PATH)

    assert "EXHIBIT INDEX" not in result
    assert "Exhibit 21.1" not in result
    assert "Exhibit 31.1" not in result


def test_normalize_whitespace(parser: TenKParser) -> None:
    """Verify whitespace, non-breaking spaces, and empty lines are cleaned."""
    html = """
    <p>First&nbsp;paragraph&nbsp;&nbsp;with&nbsp;spaces.\u200b</p>
    <p></p>
    <p><br></p>
    <p>Second paragraph.</p>
    """
    result = parser.parse(html)

    assert "\xa0" not in result
    assert "\u200b" not in result
    assert result == "First paragraph with spaces.\n\nSecond paragraph."


def test_parse_file_success(parser: TenKParser, tmp_path: Path) -> None:
    """Verify reading and parsing an HTML file from a Path."""
    test_file = tmp_path / "test_filing.htm"
    test_file.write_text(
        "<html><body><p>Filing file test</p></body></html>",
        encoding="utf-8",
    )

    result = parser.parse_file(test_file)
    assert result == "Filing file test"


def test_empty_input_handling(parser: TenKParser) -> None:
    """Verify empty string or bytes inputs return an empty string."""
    assert parser.parse("") == ""
    assert parser.parse(b"") == ""
    assert parser.parse("   \n\t  ") == ""


def test_malformed_html_handling(parser: TenKParser) -> None:
    """Verify unclosed tags and malformed HTML parse without crash."""
    malformed = "<div><p>Unclosed paragraph <b>Bold text without close"
    result = parser.parse(malformed)

    assert "Unclosed paragraph" in result
    assert "Bold text without close" in result


def test_parse_file_not_found(parser: TenKParser) -> None:
    """Verify ParserError is raised when file does not exist."""
    with pytest.raises(ParserError, match="Filing file not found"):
        parser.parse_file("nonexistent_path_to_10k.html")


def test_invalid_input_type(parser: TenKParser) -> None:
    """Verify ParserError is raised when input is neither str nor bytes."""
    with pytest.raises(ParserError, match="Expected str or bytes"):
        parser.parse(12345)  # type: ignore[arg-type]


def test_parser_engine_fallback() -> None:
    """Verify fallback parser engine operates if invalid parser requested."""
    parser = TenKParser(parser="nonexistent_engine")
    result = parser.parse("<p>Fallback content</p>")
    assert result == "Fallback content"
