"""Service for identifying and extracting structured 10-K sections."""

import re

from src.ingestion.exceptions import SectionExtractionError

# Regex to detect SEC 10-K Item headings at the beginning of a line.
# Compound items (1A, 7A, 9A, etc.) are matched before single-digit items.
ITEM_HEADER_PATTERN = re.compile(
    r"(?m)^\s*ITEM\s+(1A|1B|1C|7A|9A|9B|9C|1[0-6]|[1-9])\b[.:\-—\s]*([^\n]*)",
    re.IGNORECASE,
)

TARGET_SECTIONS = {
    "item_1",
    "item_1a",
    "item_7",
    "item_7a",
    "item_8",
}

SECTION_ALIASES: dict[str, str] = {
    "1": "item_1",
    "item 1": "item_1",
    "item_1": "item_1",
    "item1": "item_1",
    "1a": "item_1a",
    "item 1a": "item_1a",
    "item_1a": "item_1a",
    "item1a": "item_1a",
    "7": "item_7",
    "item 7": "item_7",
    "item_7": "item_7",
    "item7": "item_7",
    "7a": "item_7a",
    "item 7a": "item_7a",
    "item_7a": "item_7a",
    "item7a": "item_7a",
    "8": "item_8",
    "item 8": "item_8",
    "item_8": "item_8",
    "item8": "item_8",
}


class SectionExtractor:
    """Extracts named SEC sections (Item 1, 1A, 7, 7A, 8) from 10-K text."""

    @staticmethod
    def normalize_section_name(section_name: str) -> str:
        """Normalize an item key or alias to canonical form (e.g. 'item_1a').

        Args:
            section_name: Section name or alias (e.g. 'Item 1A', '1a', 'item_1a').

        Returns:
            str: Canonical section key (e.g. 'item_1a').

        Raises:
            SectionExtractionError: If the section name is unrecognized.
        """
        clean = section_name.strip().lower()
        if clean in SECTION_ALIASES:
            return SECTION_ALIASES[clean]
        raise SectionExtractionError(f"Unsupported section name: {section_name}")

    def extract_sections(self, text: str) -> dict[str, str]:
        """Extract all supported sections from parsed 10-K document text.

        Args:
            text: Clean plain text of the 10-K filing.

        Returns:
            dict[str, str]: Extracted sections keyed by canonical name
                ('item_1', 'item_1a', 'item_7', 'item_7a', 'item_8').
                Missing sections are omitted from the dictionary.
        """
        if not text or not text.strip():
            return {}

        matches = list(ITEM_HEADER_PATTERN.finditer(text))
        if not matches:
            return {}

        results: dict[str, str] = {}

        for i, match in enumerate(matches):
            item_num = match.group(1).upper()
            canonical_key = f"item_{item_num.lower()}"

            if canonical_key not in TARGET_SECTIONS:
                continue

            start_idx = match.end()
            end_idx = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            section_text = text[start_idx:end_idx].strip()

            if not section_text:
                continue

            # If section was already encountered, keep the longest content span
            if canonical_key not in results or len(section_text) > len(
                results[canonical_key]
            ):
                results[canonical_key] = section_text

        return results

    def extract_section(self, text: str, section_name: str) -> str | None:
        """Extract a single section by name or alias.

        Args:
            text: Clean plain text of the 10-K filing.
            section_name: Target section name or alias (e.g. 'Item 1A', '1a').

        Returns:
            str | None: Extracted section text, or None if the section is not found.
        """
        try:
            canonical_key = self.normalize_section_name(section_name)
        except SectionExtractionError:
            return None

        sections = self.extract_sections(text)
        return sections.get(canonical_key)
