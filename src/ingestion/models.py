"""Data models and validation for SEC EDGAR ingestion."""

import re

from pydantic import BaseModel, Field, field_validator, model_validator

ACCESSION_PATTERN = re.compile(r"^\d{10}-\d{2}-\d{6}$")


class FilingMetadata(BaseModel):
    """Metadata representing an SEC filing."""

    cik: str
    ticker: str | None = None
    period: str
    accession_number: str
    form_type: str = "10-K"

    @field_validator("cik", mode="before")
    @classmethod
    def validate_cik(cls, value: object) -> str:
        """Validate and zero-pad CIK to a 10-digit string."""
        if isinstance(value, int):
            if value < 0:
                raise ValueError("CIK cannot be negative.")
            str_val = str(value)
        elif isinstance(value, str):
            str_val = value.strip()
        else:
            raise ValueError(
                f"CIK must be a string or integer, got {type(value).__name__}."
            )

        if not str_val:
            raise ValueError("CIK cannot be empty.")
        if not str_val.isdigit():
            raise ValueError(f"CIK must contain only digits, got: {str_val!r}")
        if len(str_val) > 10:
            raise ValueError(f"CIK cannot exceed 10 digits, got: {str_val!r}")

        return str_val.zfill(10)

    @field_validator("ticker", mode="before")
    @classmethod
    def validate_ticker(cls, value: object) -> str | None:
        """Normalize ticker symbol to uppercase string or None."""
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError(f"ticker must be a string, got {type(value).__name__}.")
        cleaned = value.strip().upper()
        return cleaned if cleaned else None

    @field_validator("period")
    @classmethod
    def validate_period(cls, value: str) -> str:
        """Validate that period is a non-empty string."""
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("period cannot be empty.")
        return cleaned

    @field_validator("accession_number")
    @classmethod
    def validate_accession_number(cls, value: str) -> str:
        """Validate accession number matches SEC format: 0000000000-00-000000."""
        cleaned = value.strip()
        if not ACCESSION_PATTERN.match(cleaned):
            raise ValueError(
                f"Invalid accession number format: {value!r}. "
                "Expected format: 0000000000-00-000000."
            )
        return cleaned

    @field_validator("form_type")
    @classmethod
    def validate_form_type(cls, value: str) -> str:
        """Normalize form_type to uppercase and ensure it is non-empty."""
        cleaned = value.strip().upper()
        if not cleaned:
            raise ValueError("form_type cannot be empty.")
        return cleaned


class ParsedSection(BaseModel):
    """Represents an extracted section of an SEC filing."""

    section_name: str
    raw_text: str
    word_count: int = 0

    @model_validator(mode="before")
    @classmethod
    def compute_word_count(cls, data: object) -> object:
        """Auto-compute word_count from raw_text if omitted or None."""
        if (
            isinstance(data, dict)
            and data.get("word_count") is None
            and isinstance(data.get("raw_text"), str)
        ):
            data = dict(data)
            data["word_count"] = len(data["raw_text"].split())
        return data

    @field_validator("section_name")
    @classmethod
    def validate_section_name(cls, value: str) -> str:
        """Validate and normalize section_name to lowercase."""
        cleaned = value.strip().lower()
        if not cleaned:
            raise ValueError("section_name cannot be empty.")
        return cleaned

    @field_validator("word_count")
    @classmethod
    def validate_word_count(cls, value: int) -> int:
        """Validate that word_count is non-negative."""
        if value < 0:
            raise ValueError("word_count must be greater than or equal to 0.")
        return value


class ParsedDocument(BaseModel):
    """Container for complete parsed filing metadata and extracted sections."""

    metadata: FilingMetadata
    sections: list[ParsedSection] = Field(default_factory=list)

    def get_section(self, section_name: str) -> ParsedSection | None:
        """Retrieve a section by its canonical name (case-insensitive)."""
        target = section_name.strip().lower()
        for section in self.sections:
            if section.section_name == target:
                return section
        return None

    @property
    def total_word_count(self) -> int:
        """Return the sum of word counts across all sections."""
        return sum(section.word_count for section in self.sections)
