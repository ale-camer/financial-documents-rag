"""Parser for SEC EDGAR 10-K HTML and inline XBRL documents."""

import re
import warnings
from pathlib import Path

from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

from src.ingestion.exceptions import ParserError

# Ignore bs4 warning when iXBRL documents contain XML declarations
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

# Tags to completely remove along with their contents
UNWANTED_TAGS = [
    "script",
    "style",
    "head",
    "meta",
    "link",
    "noscript",
    "ix:header",
    "ix:hidden",
]

# Inline XBRL data tags whose inner content must be preserved
IXBRL_DATA_TAGS = {
    "ix:nonnumeric",
    "ix:nonfraction",
    "ix:continuation",
    "ix:fraction",
}

# Regex to detect table of contents dot leader lines (e.g. 'Item 1 ... 5')
TOC_DOT_LEADER_REGEX = re.compile(r"(?:\.\s*){4,}\s*\d*\s*$", re.MULTILINE)

# Regex to detect standalone navigation anchors
TOC_NAV_REGEX = re.compile(
    r"^\s*(?:table\s+of\s+contents|index\s+to\s+financial\s+statements)\s*$",
    re.IGNORECASE,
)

# Regex to detect exhibit index section header
EXHIBIT_INDEX_REGEX = re.compile(r"^\s*EXHIBIT\s+INDEX\s*$", re.IGNORECASE)

# Regex to identify SEC 10-K Item headings
ITEM_HEADING_REGEX = re.compile(
    r"^\s*(ITEM\s+(?:1A|1B|7A|1[0-6]|[1-9])(?:[\.\:\s].*)?)$",
    re.IGNORECASE,
)


class TenKParser:
    """Parser to convert raw 10-K HTML and iXBRL into structured plain text."""

    def __init__(self, parser: str = "lxml") -> None:
        """Initialize the 10-K parser.

        Args:
            parser: BeautifulSoup parser engine (default: 'lxml').
        """
        self.parser = parser

    def parse(self, raw_html: str | bytes) -> str:
        """Parse raw HTML or iXBRL content into clean, structured plain text.

        Args:
            raw_html: Raw filing content as string or bytes.

        Returns:
            str: Cleaned plain text with preserved section headings.

        Raises:
            ParserError: If content cannot be decoded or parsed.
        """
        html_str = self._decode_content(raw_html)
        if not html_str.strip():
            return ""

        soup = self._build_soup(html_str)
        self._strip_unwanted_tags(soup)
        self._unwrap_ixbrl_tags(soup)

        raw_text = soup.get_text(separator="\n\n")
        return self._clean_and_normalize(raw_text)

    def parse_file(self, file_path: Path | str) -> str:
        """Parse a local HTML filing file into plain text.

        Args:
            file_path: Path to the HTML filing file.

        Returns:
            str: Cleaned plain text content.

        Raises:
            ParserError: If file does not exist or parsing fails.
        """
        path = Path(file_path)
        if not path.is_file():
            raise ParserError(f"Filing file not found: {path}")

        try:
            content = path.read_bytes()
            return self.parse(content)
        except OSError as exc:
            raise ParserError(f"Error reading file {path}: {exc}") from exc

    @staticmethod
    def _decode_content(raw_html: str | bytes) -> str:
        """Decode raw input into a string using UTF-8 or Latin-1 fallback."""
        if isinstance(raw_html, str):
            return raw_html
        if isinstance(raw_html, bytes):
            try:
                return raw_html.decode("utf-8")
            except UnicodeDecodeError:
                return raw_html.decode("latin-1", errors="replace")
        raise ParserError(f"Expected str or bytes, got {type(raw_html).__name__}")

    def _build_soup(self, html_str: str) -> BeautifulSoup:
        """Construct BeautifulSoup tree, falling back to html.parser if needed."""
        try:
            return BeautifulSoup(html_str, self.parser)
        except Exception:
            return BeautifulSoup(html_str, "html.parser")

    @staticmethod
    def _strip_unwanted_tags(soup: BeautifulSoup) -> None:
        """Decompose non-content boilerplate elements."""
        for tag in soup.find_all(UNWANTED_TAGS):
            tag.decompose()

    @staticmethod
    def _unwrap_ixbrl_tags(soup: BeautifulSoup) -> None:
        """Unwrap inline XBRL data tags so their textual content is preserved."""
        for tag in soup.find_all(
            lambda t: t.name and t.name.lower() in IXBRL_DATA_TAGS
        ):
            tag.unwrap()

    def _clean_and_normalize(self, text: str) -> str:
        """Normalize whitespace, remove TOC and exhibit indexes, format headings."""
        # Replace non-breaking spaces and zero-width spaces
        text = text.replace("\xa0", " ").replace("\u200b", "")

        lines = text.split("\n")
        cleaned_lines: list[str] = []
        in_exhibit_index = False

        for line in lines:
            line_str = re.sub(r"[ \t]+", " ", line).strip()
            if not line_str:
                if cleaned_lines and cleaned_lines[-1] != "":
                    cleaned_lines.append("")
                continue

            # Detect and skip exhibit index section at document end
            if EXHIBIT_INDEX_REGEX.match(line_str):
                in_exhibit_index = True
                continue
            if in_exhibit_index:
                # If another major ITEM heading starts, resume
                if ITEM_HEADING_REGEX.match(line_str):
                    in_exhibit_index = False
                else:
                    continue

            # Strip standalone TOC navigation anchors
            if TOC_NAV_REGEX.match(line_str):
                continue

            # Strip TOC dot leader lines
            if TOC_DOT_LEADER_REGEX.search(line_str):
                continue

            # Format Item headings clearly with paragraph separation
            item_match = ITEM_HEADING_REGEX.match(line_str)
            if item_match:
                if cleaned_lines and cleaned_lines[-1] != "":
                    cleaned_lines.append("")
                cleaned_lines.append(line_str)
                cleaned_lines.append("")
            else:
                cleaned_lines.append(line_str)

        combined = "\n".join(cleaned_lines)
        # Collapse three or more consecutive newlines into double newline
        normalized = re.sub(r"\n{3,}", "\n\n", combined).strip()
        return normalized
