"""Uçtan uca akış: yükle → çıkar → doğrula → yönlendir → düzelt → onayla → export.

Canlı PostgreSQL gerektirir; yoksa `engine` fixture'ı tüm modülü atlar.
"""

import json
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from documentflow.db import models
from documentflow.db.models import AuditEventType
from documentflow.extraction import ExtractionStatus, FakeExtractor, RecordedExtractor
from documentflow.workflow import (
    AlreadyApproved,
    DocumentNotAcceptable,
    ExtractionUnavailable,
    InvalidCorrection,
    NotApproved,
    apply_correction,
    approve,
    audit_trail,
    current_invoice,
    export_approved,
    export_payload_bytes,
    ingest_document,
    run_extraction,
)
from tests.extraction._fixtures import ok_field, wire_json, wire_payload
from tests.ingestion._pdf_builder import corrupt_pdf, image_only_pdf, text_layer_pdf


def _extractor(payload: dict | None = None) -> RecordedExtractor:
    return RecordedExtractor(wire_json(payload if payload is not None else wire_payload()))


def _inconsistent_payload() -> dict:
    """İki bilinçli sorun: hem `review` hem `blocking` sinyali üretir.

    - `fatura_no` kâğıt fatura biçiminde -> FNO-001 (warning)
    - ara 3.000 + kdv 600 != genel 3.599 -> ARITH-001 (error)
    """
    payload = wire_payload()
    payload["header"]["fatura_no"] = ok_field("A-2025/000123")
    payload["header"]["genel_toplam"] = ok_field("3.599,00")
    return payload


def _ingest(session: Session, storage_root: Path, data: bytes | None = None) -> models.Document:
    return ingest_document(
        session,
        filename="ornek.pdf",
        data=data if data is not None else text_layer_pdf(),
        storage_root=storage_root,
    )


def _event_types(session: Session, run: models.ExtractionRun) -> list[str]:
    return [event.event_type for event in audit_trail(session, run)]


# --- 1. Yükleme ---------------------------------------------------------------------------


def test_accepted_document_is_stored_and_audited(session: Session, storage_root: Path) -> None:
    document = _ingest(session, storage_root)
    assert document.accepted is True
    assert document.rejection_reason is None
    assert document.relative_path is not None
    assert (storage_root / document.relative_path).is_file()
    assert document.page_count == 1

    events = session.scalars(
        select(models.AuditEvent).where(models.AuditEvent.document_id == document.id)
    ).all()
    assert [event.event_type for event in events] == [AuditEventType.document_uploaded.value]


@pytest.mark.parametrize(
    ("data", "reason"),
    [
        (b"bu bir PDF degil", "not_pdf"),
        (image_only_pdf(), "no_text_layer"),
        (corrupt_pdf(), "unreadable"),
    ],
)
def test_out_of_scope_upload_is_rejected_and_not_stored(
    session: Session, storage_root: Path, data: bytes, reason: str
) -> None:
    document = _ingest(session, storage_root, data)
    assert document.accepted is False
    assert document.rejection_reason == reason
    # Kapsam disi icerik diske yazilmaz.
    assert document.relative_path is None
    assert list(storage_root.rglob("*.pdf")) == []


def test_rejected_document_cannot_be_extracted(session: Session, storage_root: Path) -> None:
    document = _ingest(session, storage_root, image_only_pdf())
    with pytest.raises(DocumentNotAcceptable):
        run_extraction(session, document, _extractor(), storage_root=storage_root)


# --- 2-4. Çıkarım, doğrulama, flag --------------------------------------------------------


def test_happy_path_records_snapshot_findings_and_flags(
    session: Session, storage_root: Path
) -> None:
    document = _ingest(session, storage_root)
    run = run_extraction(
        session, document, _extractor(_inconsistent_payload()), storage_root=storage_root
    )

    assert run.status == ExtractionStatus.ok.value
    snapshot = session.scalars(
        select(models.ExtractedInvoice).where(models.ExtractedInvoice.extraction_run_id == run.id)
    ).one()
    assert snapshot.payload["header"]["genel_toplam"]["value"] == "3599.00"

    findings = session.scalars(
        select(models.ValidationFinding)
        .where(models.ValidationFinding.extraction_run_id == run.id)
        .order_by(models.ValidationFinding.sequence)
    ).all()
    assert [finding.rule_id for finding in findings] == ["FNO-001", "ARITH-001"]
    assert findings[0].ruleset_version == "0.1"

    flags = session.scalars(
        select(models.ReviewFlag)
        .where(models.ReviewFlag.extraction_run_id == run.id)
        .order_by(models.ReviewFlag.sequence)
    ).all()
    assert [flag.signal_code for flag in flags] == ["invoice_number_format", "header_arithmetic"]
    assert [flag.severity for flag in flags] == ["review", "blocking"]


@pytest.mark.parametrize(
    "status",
    [
        ExtractionStatus.timeout,
        ExtractionStatus.provider_error,
        ExtractionStatus.refused,
        ExtractionStatus.invalid_json,
        ExtractionStatus.schema_mismatch,
        ExtractionStatus.truncated,
    ],
)
def test_extraction_failure_records_run_without_snapshot(
    session: Session, storage_root: Path, status: ExtractionStatus
) -> None:
    document = _ingest(session, storage_root)
    run = run_extraction(
        session,
        document,
        FakeExtractor.failing(status, error_detail="sentetik"),
        storage_root=storage_root,
    )
    assert run.status == status.value
    assert run.error_detail == "sentetik"
    assert (
        session.scalars(
            select(models.ExtractedInvoice).where(
                models.ExtractedInvoice.extraction_run_id == run.id
            )
        ).one_or_none()
        is None
    )
    assert AuditEventType.extraction_failed.value in _event_types(session, run)
    with pytest.raises(ExtractionUnavailable):
        current_invoice(session, run)


def test_provider_metadata_is_persisted(session: Session, storage_root: Path) -> None:
    document = _ingest(session, storage_root)
    run = run_extraction(session, document, _extractor(), storage_root=storage_root)
    assert run.provider == "recorded"
    assert run.schema_version == "0.1"
    assert run.prompt_version == "none"


# --- 5-6. Düzeltme ------------------------------------------------------------------------


def test_correction_records_before_and_after(session: Session, storage_root: Path) -> None:
    document = _ingest(session, storage_root)
    run = run_extraction(
        session, document, _extractor(_inconsistent_payload()), storage_root=storage_root
    )

    correction = apply_correction(session, run, "header.genel_toplam", "3.600,00")
    assert correction.before_value == "3599.00"
    assert correction.before_status == "ok"
    assert correction.after_value == "3600.00"
    assert correction.after_status == "ok"

    invoice = current_invoice(session, run)
    assert invoice.header.genel_toplam.value == Decimal("3600.00")


def test_correction_does_not_mutate_the_original_snapshot(
    session: Session, storage_root: Path
) -> None:
    document = _ingest(session, storage_root)
    run = run_extraction(
        session, document, _extractor(_inconsistent_payload()), storage_root=storage_root
    )
    snapshot = session.scalars(
        select(models.ExtractedInvoice).where(models.ExtractedInvoice.extraction_run_id == run.id)
    ).one()
    before = json.dumps(snapshot.payload, sort_keys=True)

    apply_correction(session, run, "header.genel_toplam", "3.600,00")
    session.flush()
    session.refresh(snapshot)
    assert json.dumps(snapshot.payload, sort_keys=True) == before


def test_correction_repairs_the_blocking_flag(session: Session, storage_root: Path) -> None:
    from documentflow.flagging import build_review_flags
    from documentflow.validation import validate_invoice

    document = _ingest(session, storage_root)
    run = run_extraction(
        session, document, _extractor(_inconsistent_payload()), storage_root=storage_root
    )
    apply_correction(session, run, "header.genel_toplam", "3.600,00")

    invoice = current_invoice(session, run)
    flags = build_review_flags(invoice, validate_invoice(invoice))
    assert [flag.signal_code.value for flag in flags] == ["invoice_number_format"]


def test_missing_field_correction_uses_input_as_raw(session: Session, storage_root: Path) -> None:
    payload = wire_payload()
    payload["header"]["fatura_no"] = {"raw": None, "value": None, "status": "missing"}
    document = _ingest(session, storage_root)
    run = run_extraction(session, document, _extractor(payload), storage_root=storage_root)

    apply_correction(session, run, "header.fatura_no", "ABC2025000000123")
    invoice = current_invoice(session, run)
    assert invoice.header.fatura_no.value == "ABC2025000000123"
    assert invoice.header.fatura_no.raw == "ABC2025000000123"


def test_unparseable_correction_is_rejected(session: Session, storage_root: Path) -> None:
    document = _ingest(session, storage_root)
    run = run_extraction(session, document, _extractor(), storage_root=storage_root)
    with pytest.raises(InvalidCorrection):
        apply_correction(session, run, "header.ara_toplam", "uc bin lira")


# --- 7. Onay ------------------------------------------------------------------------------


def test_approval_freezes_corrected_snapshot(session: Session, storage_root: Path) -> None:
    document = _ingest(session, storage_root)
    run = run_extraction(
        session, document, _extractor(_inconsistent_payload()), storage_root=storage_root
    )
    apply_correction(session, run, "header.genel_toplam", "3.600,00")

    approval = approve(session, run)
    assert approval.correction_count == 1
    assert approval.approved_payload["header"]["genel_toplam"]["value"] == "3600.00"


def test_second_approval_is_rejected(session: Session, storage_root: Path) -> None:
    document = _ingest(session, storage_root)
    run = run_extraction(session, document, _extractor(), storage_root=storage_root)
    approve(session, run)
    with pytest.raises(AlreadyApproved):
        approve(session, run)


def test_correction_after_approval_is_rejected(session: Session, storage_root: Path) -> None:
    document = _ingest(session, storage_root)
    run = run_extraction(session, document, _extractor(), storage_root=storage_root)
    approve(session, run)
    with pytest.raises(AlreadyApproved):
        apply_correction(session, run, "header.genel_toplam", "3.600,00")


# --- 8. Export ----------------------------------------------------------------------------


def test_export_without_approval_is_rejected_and_audited(
    session: Session, storage_root: Path
) -> None:
    document = _ingest(session, storage_root)
    run = run_extraction(session, document, _extractor(), storage_root=storage_root)

    with pytest.raises(NotApproved):
        export_approved(session, run)

    assert session.scalars(select(models.ExportRecord)).all() == []
    assert AuditEventType.export_rejected.value in _event_types(session, run)


def test_export_returns_approved_payload_with_stable_hash(
    session: Session, storage_root: Path
) -> None:
    document = _ingest(session, storage_root)
    run = run_extraction(session, document, _extractor(), storage_root=storage_root)
    approval = approve(session, run)

    record, body = export_approved(session, run)
    assert record.export_format == "json"
    assert json.loads(body) == approval.approved_payload
    # Kaydedilen hash, kanonik serilestirmenin hash'idir.
    assert record.payload_sha256 == __import__("hashlib").sha256(body).hexdigest()
    # Ayni payload her zaman ayni baytlari uretir.
    assert export_payload_bytes(approval.approved_payload) == body


# --- 9. Audit -----------------------------------------------------------------------------


def test_audit_events_follow_the_workflow_order(session: Session, storage_root: Path) -> None:
    document = _ingest(session, storage_root)
    run = run_extraction(
        session, document, _extractor(_inconsistent_payload()), storage_root=storage_root
    )
    apply_correction(session, run, "header.genel_toplam", "3.600,00")
    approve(session, run)
    export_approved(session, run)

    assert _event_types(session, run) == [
        AuditEventType.document_uploaded.value,
        AuditEventType.extraction_started.value,
        AuditEventType.extraction_completed.value,
        AuditEventType.validation_completed.value,
        AuditEventType.flags_generated.value,
        AuditEventType.correction_applied.value,
        AuditEventType.approved.value,
        AuditEventType.export_created.value,
    ]


def test_audit_detail_carries_no_field_values(session: Session, storage_root: Path) -> None:
    document = _ingest(session, storage_root)
    run = run_extraction(
        session, document, _extractor(_inconsistent_payload()), storage_root=storage_root
    )
    apply_correction(session, run, "header.satici_unvan", "Duzeltilmis Unvan A.S.")
    approve(session, run)

    serialized = json.dumps(
        [event.detail for event in audit_trail(session, run)], ensure_ascii=False
    )
    # Alan degerleri ve dosya adi audit detayina yazilmaz; onlar
    # user_corrections / documents satirlarinda denetlenebilir durumda durur.
    assert "Duzeltilmis Unvan" not in serialized
    assert "ornek.pdf" not in serialized
    assert "3599" not in serialized


def test_audit_events_are_ordered_by_identity_not_timestamp(
    session: Session, storage_root: Path
) -> None:
    document = _ingest(session, storage_root)
    run = run_extraction(session, document, _extractor(), storage_root=storage_root)
    events = audit_trail(session, run)
    assert [event.id for event in events] == sorted(event.id for event in events)
    # Ayni islemdeki olaylar ayni zaman damgasini alabilir; sira yine de kesindir.
    assert len({event.occurred_at for event in events}) <= len(events)
