"""DocumentFlow AI extraction katmani (v0.1) - public arayuz.

Sagalayicidan bagimsizdir: bu paket hicbir LLM SDK'si, FastAPI veya veritabani
importu icermez (testle kilitli).
"""

from documentflow.extraction.fake import FakeExtractor, RecordedExtractor, fake_metadata
from documentflow.extraction.mapping import WireContractError, build_result, wire_to_invoice
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
    "WireContractError",
    "WireField",
    "WireHeader",
    "WireInvoice",
    "WireLineItem",
    "WireLineItems",
    "build_result",
    "fake_metadata",
    "wire_to_invoice",
]
