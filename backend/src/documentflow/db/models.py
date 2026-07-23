"""Kalıcı veri modelleri (D-005, D-006).

Tek kullanıcı; auth, rol ve çok kullanıcılı yapı yoktur. Generic repository veya
her tablo için otomatik CRUD katmanı da yoktur — sorgular ihtiyaç duyulan yerde
açıkça yazılır.

Üç ayrı katman bilinçli olarak korunur:

- **Domain** (`documentflow.schema`): belgeden çıkarılan verinin kontratı. Bu
  dosya onu HİÇ değiştirmez.
- **ORM** (bu dosya): kalıcılık şekli.
- **API** (`documentflow.api.schemas`): dışarı verilen şekil.

Üçü birbirine dönüşür, birbirinin yerine geçmez.

`Invoice` anlık görüntüleri normalize edilmiş kolonlar yerine JSONB olarak
saklanır: şema hâlâ DRAFT (D-021) ve `FieldValue` üçlüsü alan başına üç kolon
demek olurdu; her şema değişikliği migration gerektirirdi. Snapshot'ın amacı
audit doğruluğudur — çıkarımın o anki hâlini birebir korumak.
"""

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from documentflow.db.base import Base

# Parasal tahminler icin olcek. Domain tarafinda Decimal kullanilir (D-017);
# burada da float'a hic donusmemesi icin Numeric secilir.
_MONEY = Numeric(18, 6)


class AuditEventType(StrEnum):
    """Append-only audit akışında görülebilecek olay türleri."""

    document_uploaded = "document_uploaded"
    document_rejected = "document_rejected"
    extraction_started = "extraction_started"
    extraction_completed = "extraction_completed"
    extraction_failed = "extraction_failed"
    validation_completed = "validation_completed"
    flags_generated = "flags_generated"
    correction_applied = "correction_applied"
    approved = "approved"
    export_created = "export_created"
    export_rejected = "export_rejected"


class Document(Base):
    """Yüklenen ham belge. Baytlar dosya sisteminde, burada yalnızca metadata (D-047)."""

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    # Saklama köküne GÖRE yol; mutlak yol taşınabilirliği bozar ve makine
    # bilgisini kayıtlara sızdırır. Reddedilen belgede None olabilir.
    relative_path: Mapped[str | None] = mapped_column(String(255), default=None)
    size_bytes: Mapped[int] = mapped_column(Integer)
    media_type: Mapped[str] = mapped_column(String(128), default="application/pdf")
    page_count: Mapped[int | None] = mapped_column(Integer, default=None)
    original_filename: Mapped[str | None] = mapped_column(String(255), default=None)
    # V1.0 kapsam kapısı sonucu (bkz. documentflow.ingestion).
    accepted: Mapped[bool] = mapped_column(Boolean)
    rejection_reason: Mapped[str | None] = mapped_column(String(32), default=None)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())

    runs: Mapped[list["ExtractionRun"]] = relationship(back_populates="document")


class ExtractionRun(Base):
    """Tek bir çıkarım denemesi ve onun sağlayıcı metadata'sı."""

    __tablename__ = "extraction_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), index=True)

    status: Mapped[str] = mapped_column(String(32))
    provider: Mapped[str] = mapped_column(String(64))
    model: Mapped[str] = mapped_column(String(128))
    prompt_version: Mapped[str] = mapped_column(String(32))
    schema_version: Mapped[str] = mapped_column(String(16))

    latency_ms: Mapped[int | None] = mapped_column(Integer, default=None)
    input_tokens: Mapped[int | None] = mapped_column(Integer, default=None)
    output_tokens: Mapped[int | None] = mapped_column(Integer, default=None)
    cache_read_input_tokens: Mapped[int | None] = mapped_column(Integer, default=None)
    cache_creation_input_tokens: Mapped[int | None] = mapped_column(Integer, default=None)
    estimated_cost_usd: Mapped[Decimal | None] = mapped_column(_MONEY, default=None)

    # Yalnızca alan yolu + hata kodu özeti; belge içeriği içermez (D-045).
    error_detail: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())

    document: Mapped[Document] = relationship(back_populates="runs")
    snapshot: Mapped["ExtractedInvoice | None"] = relationship(back_populates="run")
    findings: Mapped[list["ValidationFinding"]] = relationship(back_populates="run")
    flags: Mapped[list["ReviewFlag"]] = relationship(back_populates="run")
    corrections: Mapped[list["UserCorrection"]] = relationship(back_populates="run")
    approval: Mapped["Approval | None"] = relationship(back_populates="run")


class ExtractedInvoice(Base):
    """Çıkarımın DEĞİŞMEZ anlık görüntüsü.

    Bu satır oluşturulduktan sonra hiçbir zaman güncellenmez: düzeltmeler
    `user_corrections`'a, onaylanan sonuç `approvals.approved_payload`'a yazılır.
    Böylece "model ne üretti" sorusu her zaman yanıtlanabilir kalır.
    """

    __tablename__ = "extracted_invoices"

    id: Mapped[int] = mapped_column(primary_key=True)
    extraction_run_id: Mapped[int] = mapped_column(
        ForeignKey("extraction_runs.id"), unique=True, index=True
    )
    # Invoice.model_dump(mode="json") — Decimal degerleri METIN olarak serilesir,
    # float'a hic donusmez (D-017).
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    parse_failures: Mapped[list[str]] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())

    run: Mapped[ExtractionRun] = relationship(back_populates="snapshot")


class ValidationFinding(Base):
    """Bir validation kuralının ürettiği bulgu (ruleset sürümüyle birlikte)."""

    __tablename__ = "validation_findings"

    id: Mapped[int] = mapped_column(primary_key=True)
    extraction_run_id: Mapped[int] = mapped_column(ForeignKey("extraction_runs.id"), index=True)
    # Raporun deterministik sırasını korur.
    sequence: Mapped[int] = mapped_column(Integer)
    rule_id: Mapped[str] = mapped_column(String(16))
    severity: Mapped[str] = mapped_column(String(16))
    field_paths: Mapped[list[str]] = mapped_column(JSONB)
    message: Mapped[str] = mapped_column(Text)
    ruleset_version: Mapped[str] = mapped_column(String(16))

    run: Mapped[ExtractionRun] = relationship(back_populates="findings")


class ReviewFlag(Base):
    """Deterministik insan denetimi yönlendirme kaydı (LLM confidence içermez)."""

    __tablename__ = "review_flags"

    id: Mapped[int] = mapped_column(primary_key=True)
    extraction_run_id: Mapped[int] = mapped_column(ForeignKey("extraction_runs.id"), index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    field_path: Mapped[str] = mapped_column(String(128))
    signal_code: Mapped[str] = mapped_column(String(48))
    severity: Mapped[str] = mapped_column(String(16))
    reason: Mapped[str] = mapped_column(Text)
    originating_rule: Mapped[str | None] = mapped_column(String(16), default=None)
    suggested_action: Mapped[str] = mapped_column(String(48))

    run: Mapped[ExtractionRun] = relationship(back_populates="flags")


class UserCorrection(Base):
    """Kullanıcının bir alanı düzeltmesi — ÖNCE ve SONRA değerleriyle.

    Değerler metin olarak saklanır (float yok, D-017); `after_value` domain
    parser'larından geçirilerek doğrulanmış olandır.
    """

    __tablename__ = "user_corrections"

    id: Mapped[int] = mapped_column(primary_key=True)
    extraction_run_id: Mapped[int] = mapped_column(ForeignKey("extraction_runs.id"), index=True)
    field_path: Mapped[str] = mapped_column(String(128))

    before_raw: Mapped[str | None] = mapped_column(Text, default=None)
    before_value: Mapped[str | None] = mapped_column(Text, default=None)
    before_status: Mapped[str] = mapped_column(String(16), default="missing")

    after_value: Mapped[str] = mapped_column(Text, default="")
    after_status: Mapped[str] = mapped_column(String(16), default="ok")

    corrected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())

    run: Mapped[ExtractionRun] = relationship(back_populates="corrections")


class Approval(Base):
    """Kullanıcının onayı ve onaylanan nihai anlık görüntü.

    `extraction_run_id` UNIQUE'tir: bir çıkarım en fazla bir kez onaylanır.
    `approved_payload`, orijinal snapshot'ın üzerine düzeltmeler uygulanarak
    üretilen YENİ bir görüntüdür; orijinali değiştirmez.
    """

    __tablename__ = "approvals"

    id: Mapped[int] = mapped_column(primary_key=True)
    extraction_run_id: Mapped[int] = mapped_column(
        ForeignKey("extraction_runs.id"), unique=True, index=True
    )
    approved_payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    correction_count: Mapped[int] = mapped_column(Integer, default=0)
    approved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())

    run: Mapped[ExtractionRun] = relationship(back_populates="approval")
    exports: Mapped[list["ExportRecord"]] = relationship(back_populates="approval")


class ExportRecord(Base):
    """Onaylanmış verinin dışa aktarıldığı an. Onay olmadan satır oluşmaz."""

    __tablename__ = "export_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    approval_id: Mapped[int] = mapped_column(ForeignKey("approvals.id"), index=True)
    payload_sha256: Mapped[str] = mapped_column(String(64))
    export_format: Mapped[str] = mapped_column(String(16), default="json")
    exported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())

    approval: Mapped[Approval] = relationship(back_populates="exports")


class AuditEvent(Base):
    """Append-only audit kaydı.

    Yalnızca `documentflow.workflow.record_event` ile yazılır; güncelleme veya
    silme yolu yoktur. Sıralama `id` (identity) ile yapılır: `occurred_at`
    PostgreSQL'de işlem başlangıç zamanıdır, aynı işlemdeki olaylar AYNI zaman
    damgasını alır ve zaman damgasına göre sıralama belirsiz olurdu.

    `detail` yalnızca ayrımlayıcı bilgi taşır (sayılar, durumlar, kural
    kimlikleri, alan yolları). Belge içeriği, alan DEĞERLERİ ve dosya adı
    buraya yazılmaz.
    """

    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_type: Mapped[str] = mapped_column(String(48), index=True)
    document_id: Mapped[int | None] = mapped_column(
        ForeignKey("documents.id"), default=None, index=True
    )
    extraction_run_id: Mapped[int | None] = mapped_column(
        ForeignKey("extraction_runs.id"), default=None, index=True
    )
    detail: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
