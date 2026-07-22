"""DocumentFlow AI ingestion katmani (V1.0) - public arayuz."""

from documentflow.ingestion.pdf import (
    DEFAULT_MAX_BYTES,
    DEFAULT_MIN_TEXT_CHARACTERS,
    PdfInspection,
    PdfRejectionReason,
    inspect_pdf,
)

__all__ = [
    "DEFAULT_MAX_BYTES",
    "DEFAULT_MIN_TEXT_CHARACTERS",
    "PdfInspection",
    "PdfRejectionReason",
    "inspect_pdf",
]
