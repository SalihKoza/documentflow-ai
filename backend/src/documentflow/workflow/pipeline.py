"""Uçtan uca fatura işleme akışı (DB-aware, FastAPI-agnostik).

`Session` ve `ExtractorProtocol` dışarıdan verilir; bu modül hiçbir web
framework'ü import etmez. Böylece akış bir HTTP isteği olmadan da (test, CLI,
ileride bir zamanlayıcı) aynı biçimde sürülebilir.

Akış: yükle → çıkar → doğrula → yönlendir → düzelt → onayla → export. Her adım
append-only bir audit olayı yazar.

Değişmezlik kuralları:

- Orijinal çıkarım anlık görüntüsü (`ExtractedInvoice`) **hiçbir zaman
  güncellenmez**. Düzeltmeler ayrı satırlara, onaylanan sonuç ayrı bir
  görüntüye yazılır.
- **Onaylanmamış veri dışa aktarılamaz.**
"""

import hashlib
import json
import re
from collections.abc import Sequence
from copy import deepcopy
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from documentflow.db import models
from documentflow.db.models import AuditEventType
from documentflow.documents import store_document
from documentflow.extraction import (
    ExtractionRequest,
    ExtractionStatus,
    ExtractorProtocol,
    UnknownFieldPathError,
    parse_field_value,
)
from documentflow.flagging import build_review_flags
from documentflow.ingestion import inspect_pdf
from documentflow.schema import FieldStatus, Invoice
from documentflow.validation import Severity, validate_invoice

_LINE_PATH = re.compile(r"\Akalemler\[(\d+)\]\.(\w+)\Z")
_HEADER_PATH = re.compile(r"\Aheader\.(\w+)\Z")


class WorkflowError(Exception):
    """Akış kuralı ihlali. API katmanı bunları HTTP durumlarına çevirir."""


class DocumentNotAcceptable(WorkflowError):
    """Belge V1.0 kapsam kapısından geçmedi; çıkarım çalıştırılamaz."""


class ExtractionUnavailable(WorkflowError):
    """Çıkarım başarısız olduğu için üzerinde çalışılacak bir fatura yok."""


class AlreadyApproved(WorkflowError):
    """Onaylanmış bir çıkarım üzerinde düzeltme veya ikinci onay yapılamaz."""


class NotApproved(WorkflowError):
    """Onaylanmamış veri dışa aktarılamaz."""


class InvalidCorrection(WorkflowError):
    """Düzeltme değeri alanın beklediği biçimde parse edilemedi."""


# --- Audit --------------------------------------------------------------------------------


def record_event(
    session: Session,
    event_type: AuditEventType,
    *,
    document: models.Document | None = None,
    run: models.ExtractionRun | None = None,
    detail: dict[str, Any] | None = None,
) -> models.AuditEvent:
    """Append-only audit olayı yazar.

    `detail` yalnızca ayrımlayıcı bilgi taşımalıdır (sayılar, durumlar, kural
    kimlikleri, alan yolları). Belge içeriği, alan DEĞERLERİ ve dosya adı
    buraya yazılmaz.
    """
    event = models.AuditEvent(
        event_type=event_type.value,
        document_id=document.id if document is not None else None,
        extraction_run_id=run.id if run is not None else None,
        detail=detail or {},
    )
    session.add(event)
    session.flush()
    return event


def audit_trail(session: Session, run: models.ExtractionRun) -> list[models.AuditEvent]:
    """Bir çıkarıma ait olayları yazılma sırasıyla döndürür.

    Sıralama `id` üzerindendir: `occurred_at` PostgreSQL'de işlem başlangıç
    zamanıdır ve aynı işlemdeki olaylar aynı damgayı alır.
    """
    statement = (
        select(models.AuditEvent)
        .where(
            (models.AuditEvent.extraction_run_id == run.id)
            | (models.AuditEvent.document_id == run.document_id)
        )
        .order_by(models.AuditEvent.id)
    )
    return list(session.scalars(statement))


# --- 1. Yükleme ---------------------------------------------------------------------------


def ingest_document(
    session: Session, *, filename: str | None, data: bytes, storage_root: Any
) -> models.Document:
    """Belgeyi V1.0 kapsam kapısından geçirir ve kabul edilirse saklar.

    Reddedilen belge diske YAZILMAZ (kapsam dışı içerik biriktirmemek için);
    yalnızca metadata ve ret nedeni kaydedilir.
    """
    inspection = inspect_pdf(data)
    document = models.Document(
        sha256=hashlib.sha256(data).hexdigest(),
        size_bytes=len(data),
        page_count=inspection.page_count,
        original_filename=filename,
        accepted=inspection.accepted,
        rejection_reason=inspection.reason.value if inspection.reason else None,
    )

    if inspection.accepted:
        stored = store_document(data, root=storage_root)
        document.relative_path = stored.relative_path
        document.sha256 = stored.sha256

    session.add(document)
    session.flush()
    record_event(
        session,
        AuditEventType.document_uploaded
        if inspection.accepted
        else AuditEventType.document_rejected,
        document=document,
        detail={
            "accepted": inspection.accepted,
            "reason": document.rejection_reason,
            "page_count": inspection.page_count,
            "size_bytes": len(data),
        },
    )
    return document


# --- 2-4. Çıkarım, doğrulama, yönlendirme -------------------------------------------------


def run_extraction(
    session: Session,
    document: models.Document,
    extractor: ExtractorProtocol,
    *,
    storage_root: Any,
) -> models.ExtractionRun:
    """Çıkarımı çalıştırır; başarılıysa doğrulama ve flag üretimini de yürütür."""
    if not document.accepted or document.relative_path is None:
        raise DocumentNotAcceptable(document.rejection_reason or "not_accepted")

    record_event(session, AuditEventType.extraction_started, document=document)

    data = (storage_root / document.relative_path).read_bytes()
    result = extractor.extract(
        ExtractionRequest(
            # Opak kimlik: dosya adi saglayiciya gonderilmez.
            document_id=str(document.id),
            content=data,
            page_count=document.page_count,
        )
    )

    metadata = result.metadata
    run = models.ExtractionRun(
        document_id=document.id,
        status=result.status.value,
        provider=metadata.provider,
        model=metadata.model,
        prompt_version=metadata.prompt_version,
        schema_version=metadata.schema_version,
        latency_ms=metadata.latency_ms,
        input_tokens=metadata.input_tokens,
        output_tokens=metadata.output_tokens,
        cache_read_input_tokens=metadata.cache_read_input_tokens,
        cache_creation_input_tokens=metadata.cache_creation_input_tokens,
        estimated_cost_usd=metadata.estimated_cost_usd,
        error_detail=result.error_detail,
    )
    session.add(run)
    session.flush()

    if result.status is not ExtractionStatus.ok or result.invoice is None:
        record_event(
            session,
            AuditEventType.extraction_failed,
            document=document,
            run=run,
            detail={"status": result.status.value},
        )
        return run

    session.add(
        models.ExtractedInvoice(
            extraction_run_id=run.id,
            payload=result.invoice.model_dump(mode="json"),
            parse_failures=list(result.parse_failures),
        )
    )
    record_event(
        session,
        AuditEventType.extraction_completed,
        document=document,
        run=run,
        detail={
            "parse_failure_count": len(result.parse_failures),
            "latency_ms": metadata.latency_ms,
        },
    )

    report = validate_invoice(result.invoice)
    for index, finding in enumerate(report.findings):
        session.add(
            models.ValidationFinding(
                extraction_run_id=run.id,
                sequence=index,
                rule_id=finding.rule_id,
                severity=finding.severity.value,
                field_paths=list(finding.field_paths),
                message=finding.message,
                ruleset_version=report.ruleset_version,
            )
        )
    record_event(
        session,
        AuditEventType.validation_completed,
        document=document,
        run=run,
        detail={
            "ruleset_version": report.ruleset_version,
            "finding_count": len(report.findings),
            "error_count": sum(1 for f in report.findings if f.severity is Severity.error),
            "review_required": report.review_required,
        },
    )

    flags = build_review_flags(result.invoice, report, parse_failures=result.parse_failures)
    for index, flag in enumerate(flags):
        session.add(
            models.ReviewFlag(
                extraction_run_id=run.id,
                sequence=index,
                field_path=flag.field_path,
                signal_code=flag.signal_code.value,
                severity=flag.severity.value,
                reason=flag.reason,
                originating_rule=flag.originating_rule,
                suggested_action=flag.suggested_action.value,
            )
        )
    record_event(
        session,
        AuditEventType.flags_generated,
        document=document,
        run=run,
        detail={
            "flag_count": len(flags),
            "signals": sorted({flag.signal_code.value for flag in flags}),
        },
    )
    session.flush()
    return run


# --- Anlık görüntü + düzeltme ---------------------------------------------------------------


def _snapshot_payload(session: Session, run: models.ExtractionRun) -> dict[str, Any]:
    snapshot = session.scalars(
        select(models.ExtractedInvoice).where(models.ExtractedInvoice.extraction_run_id == run.id)
    ).one_or_none()
    if snapshot is None:
        raise ExtractionUnavailable(run.status)
    return deepcopy(snapshot.payload)


def _locate_field(payload: dict[str, Any], field_path: str) -> dict[str, Any]:
    """Alan yolundan payload içindeki alan sözlüğünü bulur."""
    header_match = _HEADER_PATH.match(field_path)
    if header_match:
        field = payload["header"].get(header_match.group(1))
        if field is None:
            raise UnknownFieldPathError(field_path)
        return field

    line_match = _LINE_PATH.match(field_path)
    if line_match:
        index = int(line_match.group(1))
        lines = payload["kalemler"].get("value") or []
        if index >= len(lines):
            raise UnknownFieldPathError(field_path)
        field = lines[index].get(line_match.group(2))
        if field is None:
            raise UnknownFieldPathError(field_path)
        return field

    raise UnknownFieldPathError(field_path)


def _json_value(parsed: str | date | Decimal) -> str:
    """Parse edilmiş değeri snapshot'taki JSON biçimine çevirir (float yok)."""
    if isinstance(parsed, date):
        return parsed.isoformat()
    return str(parsed)


def _apply_corrections(
    payload: dict[str, Any], corrections: Sequence[models.UserCorrection]
) -> dict[str, Any]:
    """Düzeltmeleri bir payload KOPYASINA sırayla uygular."""
    result = deepcopy(payload)
    for correction in corrections:
        field = _locate_field(result, correction.field_path)
        # Belgenin ham metni korunur; yalnizca alan hic yoksa kullanicinin
        # girdisi raw olarak kullanilir (FieldValue invariant'i raw zorunlu kilar).
        if not field.get("raw"):
            field["raw"] = correction.after_value
        field["value"] = correction.after_value
        field["status"] = correction.after_status
    return result


def current_invoice(session: Session, run: models.ExtractionRun) -> Invoice:
    """Orijinal anlık görüntü + uygulanmış düzeltmeler (orijinal değişmez)."""
    payload = _snapshot_payload(session, run)
    corrections = session.scalars(
        select(models.UserCorrection)
        .where(models.UserCorrection.extraction_run_id == run.id)
        .order_by(models.UserCorrection.id)
    ).all()
    return Invoice.model_validate(_apply_corrections(payload, corrections))


def _approval_for(session: Session, run: models.ExtractionRun) -> models.Approval | None:
    return session.scalars(
        select(models.Approval).where(models.Approval.extraction_run_id == run.id)
    ).one_or_none()


def apply_correction(
    session: Session, run: models.ExtractionRun, field_path: str, new_value: str
) -> models.UserCorrection:
    """Bir alanı düzeltir; ÖNCE ve SONRA değerlerini denetlenebilir biçimde kaydeder."""
    if _approval_for(session, run) is not None:
        raise AlreadyApproved(str(run.id))

    payload = _snapshot_payload(session, run)
    corrections = list(
        session.scalars(
            select(models.UserCorrection)
            .where(models.UserCorrection.extraction_run_id == run.id)
            .order_by(models.UserCorrection.id)
        )
    )
    # "Once" degeri, kullanicinin ekranda gordugu guncel deger olmalidir.
    before = _locate_field(_apply_corrections(payload, corrections), field_path)

    parsed = parse_field_value(field_path, new_value)
    if parsed is None:
        raise InvalidCorrection(field_path)

    correction = models.UserCorrection(
        extraction_run_id=run.id,
        field_path=field_path,
        before_raw=before.get("raw"),
        before_value=before.get("value"),
        before_status=before.get("status", FieldStatus.missing.value),
        after_value=_json_value(parsed),
        after_status=FieldStatus.ok.value,
    )
    session.add(correction)
    session.flush()

    record_event(
        session,
        AuditEventType.correction_applied,
        document=run.document,
        run=run,
        detail={
            # Alan DEGERLERI audit detayina yazilmaz; onlar user_corrections
            # satirinda denetlenebilir durumda zaten duruyor.
            "field_path": field_path,
            "correction_id": correction.id,
            "before_status": correction.before_status,
            "after_status": correction.after_status,
        },
    )
    return correction


# --- 7. Onay ------------------------------------------------------------------------------


def approve(session: Session, run: models.ExtractionRun) -> models.Approval:
    """Düzeltmeler uygulanmış YENİ bir anlık görüntüyü onaylar."""
    if _approval_for(session, run) is not None:
        raise AlreadyApproved(str(run.id))

    invoice = current_invoice(session, run)
    corrections = list(
        session.scalars(
            select(models.UserCorrection).where(models.UserCorrection.extraction_run_id == run.id)
        )
    )

    approval = models.Approval(
        extraction_run_id=run.id,
        approved_payload=invoice.model_dump(mode="json"),
        correction_count=len(corrections),
    )
    session.add(approval)
    session.flush()

    report = validate_invoice(invoice)
    record_event(
        session,
        AuditEventType.approved,
        document=run.document,
        run=run,
        detail={
            "approval_id": approval.id,
            "correction_count": len(corrections),
            # Onay aninda kalan deterministik sinyal sayisi: insan bunlara ragmen
            # onaylamayi secmis olabilir, kayit bunu gorunur kilar.
            "remaining_error_count": sum(
                1 for f in report.findings if f.severity is Severity.error
            ),
            "remaining_finding_count": len(report.findings),
        },
    )
    return approval


# --- 8. Export ----------------------------------------------------------------------------


def export_payload_bytes(payload: dict[str, Any]) -> bytes:
    """Export gövdesini deterministik biçimde serileştirir (hash kararlı olsun)."""
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode(
        "utf-8"
    )


def export_approved(
    session: Session, run: models.ExtractionRun
) -> tuple[models.ExportRecord, bytes]:
    """Onaylanmış veriyi dışa aktarır.

    Onay yoksa `NotApproved` fırlatır, audit'e `export_rejected` yazar ve
    **hiçbir çıktı üretmez**.
    """
    approval = _approval_for(session, run)
    if approval is None:
        record_event(
            session,
            AuditEventType.export_rejected,
            document=run.document,
            run=run,
            detail={"reason": "not_approved"},
        )
        raise NotApproved(str(run.id))

    body = export_payload_bytes(approval.approved_payload)
    record = models.ExportRecord(
        approval_id=approval.id,
        payload_sha256=hashlib.sha256(body).hexdigest(),
        export_format="json",
    )
    session.add(record)
    session.flush()
    record_event(
        session,
        AuditEventType.export_created,
        document=run.document,
        run=run,
        detail={
            "export_id": record.id,
            "approval_id": approval.id,
            "payload_sha256": record.payload_sha256,
        },
    )
    return record, body
