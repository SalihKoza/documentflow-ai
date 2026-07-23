"""DocumentFlow AI extraction katmani (v0.1) - public arayuz.

Sagalayicidan bagimsizdir: bu paket hicbir LLM SDK'si, FastAPI veya veritabani
importu icermez (testle kilitli).
"""

from documentflow.extraction.fake import FakeExtractor, RecordedExtractor, fake_metadata
from documentflow.extraction.mapping import (
    UnknownFieldPathError,
    WireContractError,
    build_result,
    parse_field_value,
    wire_to_invoice,
)
from documentflow.extraction.protocol import ExtractorProtocol
from documentflow.extraction.types import (
    DEFAULT_SCHEMA_VERSION,
    ExtractionRequest,
    ExtractionResult,
    ExtractionStatus,
    ProviderMetadata,
)
from documentflow.extraction.wire import (
    WireField,
    WireHeader,
    WireInvoice,
    WireLineItem,
    WireLineItems,
)

__all__ = [
    "DEFAULT_SCHEMA_VERSION",
    "ExtractionRequest",
    "ExtractionResult",
    "ExtractionStatus",
    "ExtractorProtocol",
    "FakeExtractor",
    "ProviderMetadata",
    "RecordedExtractor",
    "UnknownFieldPathError",
    "WireContractError",
    "WireField",
    "WireHeader",
    "WireInvoice",
    "WireLineItem",
    "WireLineItems",
    "build_result",
    "fake_metadata",
    "parse_field_value",
    "wire_to_invoice",
]
