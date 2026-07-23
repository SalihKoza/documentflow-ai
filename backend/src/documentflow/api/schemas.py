"""API katmanı şemaları (dışarı verilen şekil).

Domain (`documentflow.schema`) ve ORM (`documentflow.db.models`) modellerinden
BAĞIMSIZDIR. Üçü birbirine dönüşür, birbirinin yerine geçmez: domain kontratı
değişmeden API yanıtı değişebilir ve tersi.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AuditEventOut(BaseModel):
    """Tek bir audit olayı. `sequence`, olayların yazılma sırasıdır."""

    model_config = ConfigDict(extra="forbid")

    sequence: int
    event_type: str
    occurred_at: datetime
    document_id: int | None = None
    extraction_run_id: int | None = None
    detail: dict[str, Any]


class AuditTrailOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    extraction_run_id: int
    events: list[AuditEventOut]


class ApprovedExportOut(BaseModel):
    """Onaylanmış JSON export zarfı.

    `invoice`, onay anında dondurulmuş anlık görüntüdür. `payload_sha256`, o
    anlık görüntünün kanonik serileştirmesinin hash'idir (bu zarfın değil) —
    aynı değer `export_records` satırında saklanır, böylece dışa aktarılan
    içeriğin sonradan değişmediği doğrulanabilir.
    """

    model_config = ConfigDict(extra="forbid")

    document_id: int
    extraction_run_id: int
    export_id: int
    approved_at: datetime
    correction_count: int
    payload_sha256: str
    invoice: dict[str, Any]
