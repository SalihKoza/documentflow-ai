"""DocumentFlow AI uçtan uca akış katmanı - public arayüz.

DB-aware fakat FastAPI-agnostiktir: `Session` ve `ExtractorProtocol` dışarıdan
verilir, hiçbir web framework'ü import edilmez.
"""

from documentflow.workflow.pipeline import (
    AlreadyApproved,
    DocumentNotAcceptable,
    ExtractionUnavailable,
    InvalidCorrection,
    NotApproved,
    WorkflowError,
    apply_correction,
    approve,
    audit_trail,
    current_invoice,
    export_approved,
    export_payload_bytes,
    ingest_document,
    record_event,
    run_extraction,
)

__all__ = [
    "AlreadyApproved",
    "DocumentNotAcceptable",
    "ExtractionUnavailable",
    "InvalidCorrection",
    "NotApproved",
    "WorkflowError",
    "apply_correction",
    "approve",
    "audit_trail",
    "current_invoice",
    "export_approved",
    "export_payload_bytes",
    "ingest_document",
    "record_event",
    "run_extraction",
]
