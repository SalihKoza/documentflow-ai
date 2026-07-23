"""Human review yüzeyi: minimal FastAPI + server-rendered HTML.

Tek kullanıcı; auth, rol ve çok kullanıcılı yapı yoktur. SPA yoktur — sayfalar
sunucuda render edilir ve form gönderimiyle ilerler. Amaç görsel gösteriş değil,
çıkarılan alanların anlaşılır biçimde incelenip düzeltilmesidir
(PROJECT_BRIEF §9).

Şablonlarda Jinja2 autoescape açıktır: fatura metni güvenilmeyen girdidir.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select

from documentflow.api.deps import (
    ExtractorDep,
    SessionDep,
    SettingsDep,
    StorageRootDep,
    is_demo_extractor,
)
from documentflow.api.schemas import ApprovedExportOut, AuditEventOut, AuditTrailOut
from documentflow.db import models
from documentflow.extraction import UnknownFieldPathError
from documentflow.flagging import ReviewFlag, build_review_flags
from documentflow.schema import Invoice, InvoiceHeader, LineItem
from documentflow.validation import validate_invoice
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
    ingest_document,
    run_extraction,
)

router = APIRouter(tags=["review"])
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


@dataclass
class FieldRow:
    """Review tablosunda tek bir alan satırı."""

    path: str
    name: str
    raw: str | None
    value: str | None
    field_status: str
    flags: list[ReviewFlag] = field(default_factory=list)


def _field_rows(invoice: Invoice, flags: list[ReviewFlag]) -> list[FieldRow]:
    """Alanları şema bildirim sırasında, flag'leriyle eşleşmiş olarak listeler."""
    by_path: dict[str, list[ReviewFlag]] = {}
    for flag in flags:
        by_path.setdefault(flag.field_path, []).append(flag)

    rows: list[FieldRow] = []

    def add(path: str, name: str, value_field: Any) -> None:
        rows.append(
            FieldRow(
                path=path,
                name=name,
                raw=value_field.raw,
                value=None if value_field.value is None else str(value_field.value),
                field_status=value_field.status.value,
                flags=by_path.get(path, []),
            )
        )

    for name in InvoiceHeader.model_fields:
        add(f"header.{name}", name, getattr(invoice.header, name))

    if invoice.kalemler.value is not None:
        for index, line in enumerate(invoice.kalemler.value):
            for name in LineItem.model_fields:
                add(f"kalemler[{index}].{name}", f"[{index}] {name}", getattr(line, name))

    return rows


def _get_run(session: SessionDep, run_id: int) -> models.ExtractionRun:
    run = session.get(models.ExtractionRun, run_id)
    if run is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="extraction run bulunamadi")
    return run


@router.get("/", response_class=HTMLResponse)
def index(request: Request, session: SessionDep, settings: SettingsDep) -> Any:
    """Belge listesi ve yükleme formu."""
    documents = list(
        session.scalars(select(models.Document).order_by(models.Document.id.desc()).limit(50))
    )
    latest_run: dict[int, int] = {}
    for run in session.scalars(select(models.ExtractionRun).order_by(models.ExtractionRun.id)):
        latest_run[run.document_id] = run.id

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "documents": documents,
            "latest_run": latest_run,
            "demo": is_demo_extractor(settings),
        },
    )


@router.post("/documents")
def upload_document(
    session: SessionDep,
    extractor: ExtractorDep,
    storage_root: StorageRootDep,
    upload: Annotated[UploadFile, File()],
) -> RedirectResponse:
    """Tek PDF yükler; kabul edilirse çıkarım, doğrulama ve flag üretimini çalıştırır."""
    storage_root.mkdir(parents=True, exist_ok=True)
    data = upload.file.read()
    document = ingest_document(
        session, filename=upload.filename, data=data, storage_root=storage_root
    )
    if not document.accepted:
        session.commit()
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    try:
        run = run_extraction(session, document, extractor, storage_root=storage_root)
    except DocumentNotAcceptable as exc:
        session.commit()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    session.commit()
    return RedirectResponse(url=f"/runs/{run.id}", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/runs/{run_id}", response_class=HTMLResponse)
def review_run(request: Request, session: SessionDep, settings: SettingsDep, run_id: int) -> Any:
    """Review ekranı: güncel alanlar, güncel sinyaller, düzeltme ve onay."""
    run = _get_run(session, run_id)
    approval = session.scalars(
        select(models.Approval).where(models.Approval.extraction_run_id == run.id)
    ).one_or_none()

    rows: list[FieldRow] = []
    flags: list[ReviewFlag] = []
    extraction_failed = False
    try:
        invoice = current_invoice(session, run)
    except ExtractionUnavailable:
        extraction_failed = True
    else:
        snapshot = session.scalars(
            select(models.ExtractedInvoice).where(
                models.ExtractedInvoice.extraction_run_id == run.id
            )
        ).one()
        report = validate_invoice(invoice)
        # Ekranda GUNCEL durum gosterilir (duzeltmeler uygulanmis). Cikarimin
        # orijinal bulgu ve flag'leri audit icin veritabaninda korunur.
        flags = list(build_review_flags(invoice, report, parse_failures=snapshot.parse_failures))
        rows = _field_rows(invoice, flags)

    corrections = list(
        session.scalars(
            select(models.UserCorrection)
            .where(models.UserCorrection.extraction_run_id == run.id)
            .order_by(models.UserCorrection.id)
        )
    )

    return templates.TemplateResponse(
        request=request,
        name="review.html",
        context={
            "run": run,
            "rows": rows,
            "flags": flags,
            "corrections": corrections,
            "approval": approval,
            "extraction_failed": extraction_failed,
            "blocking_count": sum(1 for flag in flags if flag.severity.value == "blocking"),
            "events": audit_trail(session, run),
            "demo": is_demo_extractor(settings),
        },
    )


@router.post("/runs/{run_id}/corrections")
def correct_field(
    session: SessionDep,
    run_id: int,
    field_path: Annotated[str, Form()],
    new_value: Annotated[str, Form()],
) -> RedirectResponse:
    """Bir alanı düzeltir. Orijinal anlık görüntü değişmez."""
    run = _get_run(session, run_id)
    try:
        apply_correction(session, run, field_path, new_value)
    except (InvalidCorrection, UnknownFieldPathError) as exc:
        session.rollback()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except (AlreadyApproved, ExtractionUnavailable) as exc:
        session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    session.commit()
    return RedirectResponse(url=f"/runs/{run_id}", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/runs/{run_id}/approve")
def approve_run(session: SessionDep, run_id: int) -> RedirectResponse:
    """Düzeltmeler uygulanmış anlık görüntüyü onaylar."""
    run = _get_run(session, run_id)
    try:
        approve(session, run)
    except (AlreadyApproved, ExtractionUnavailable) as exc:
        session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    session.commit()
    return RedirectResponse(url=f"/runs/{run_id}", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/runs/{run_id}/export", response_model=ApprovedExportOut)
def export_run(session: SessionDep, run_id: int) -> ApprovedExportOut:
    """Onaylanmış JSON export. Onay yoksa 409 ve hiçbir veri dönmez.

    POST'tur çünkü yan etkilidir: `export_records` satırı ve `export_created`
    audit olayı üretir (D-057). GET rotaları safe kalır — browser prefetch,
    tekrar tıklama veya otomatik link taraması kazara export üretmemelidir.
    """
    run = _get_run(session, run_id)
    try:
        record, _ = export_approved(session, run)
    except NotApproved as exc:
        # Reddedilen export girisimi de audit'e yazilir; bu yuzden commit edilir.
        session.commit()
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="onaylanmamis veri disa aktarilamaz"
        ) from exc
    approval = record.approval
    session.commit()
    return ApprovedExportOut(
        document_id=run.document_id,
        extraction_run_id=run.id,
        export_id=record.id,
        approved_at=approval.approved_at,
        correction_count=approval.correction_count,
        payload_sha256=record.payload_sha256,
        invoice=approval.approved_payload,
    )


@router.get("/runs/{run_id}/audit", response_model=AuditTrailOut)
def run_audit(session: SessionDep, run_id: int) -> AuditTrailOut:
    """Audit olayları, yazılma sırasıyla."""
    run = _get_run(session, run_id)
    return AuditTrailOut(
        extraction_run_id=run.id,
        events=[
            AuditEventOut(
                sequence=event.id,
                event_type=event.event_type,
                occurred_at=event.occurred_at,
                document_id=event.document_id,
                extraction_run_id=event.extraction_run_id,
                detail=event.detail,
            )
            for event in audit_trail(session, run)
        ],
    )
