"""Veritabanı katmanı: migration uyumu, Decimal/JSON serileştirme, audit append.

Canlı PostgreSQL gerektirir; yoksa `engine` fixture'ı modülü atlar.
"""

from decimal import Decimal

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from documentflow.db.base import Base
from documentflow.db.models import AuditEvent, AuditEventType, Document, ExtractionRun
from documentflow.extraction import ExtractionRequest, RecordedExtractor
from documentflow.schema import Invoice
from documentflow.workflow import record_event
from tests.extraction._fixtures import wire_json, wire_payload


def test_migration_matches_the_orm_models(engine: Engine) -> None:
    """Elle yazılan migration ile modeller arasında fark olmamalı."""
    with engine.connect() as connection:
        context = MigrationContext.configure(connection)
        diff = compare_metadata(context, Base.metadata)
    assert diff == [], f"migration ile modeller arasinda fark var: {diff}"


def _document(session: Session) -> Document:
    document = Document(sha256="a" * 64, size_bytes=10, accepted=True, relative_path="aa/x.pdf")
    session.add(document)
    session.flush()
    return document


def test_money_column_round_trips_as_decimal(session: Session) -> None:
    document = _document(session)
    run = ExtractionRun(
        document_id=document.id,
        status="ok",
        provider="recorded",
        model="none",
        prompt_version="none",
        schema_version="0.1",
        estimated_cost_usd=Decimal("0.001234"),
    )
    session.add(run)
    session.flush()
    session.expire(run)

    assert isinstance(run.estimated_cost_usd, Decimal)
    assert not isinstance(run.estimated_cost_usd, float)
    assert run.estimated_cost_usd == Decimal("0.001234")


def test_invoice_snapshot_round_trips_without_float() -> None:
    """JSONB'ye yazılan Decimal değerleri metin olarak döner ve birebir korunur."""
    result = RecordedExtractor(wire_json(wire_payload())).extract(
        ExtractionRequest(document_id="1", content=b"%PDF-")
    )
    assert result.invoice is not None
    payload = result.invoice.model_dump(mode="json")

    # Serilestirme metindir: JSON sayisi (dolayisiyla float) hic olusmaz.
    assert payload["header"]["genel_toplam"]["value"] == "3600.00"
    assert isinstance(payload["header"]["genel_toplam"]["value"], str)

    restored = Invoice.model_validate(payload)
    assert restored.header.genel_toplam.value == Decimal("3600.00")
    assert not isinstance(restored.header.genel_toplam.value, float)
    # Ondalik basamak sayisi da korunur (3600.00 != 3600.0 metin olarak).
    assert str(restored.header.genel_toplam.value) == "3600.00"


def test_audit_events_are_written_in_call_order(session: Session) -> None:
    document = _document(session)
    first = record_event(session, AuditEventType.document_uploaded, document=document)
    second = record_event(session, AuditEventType.extraction_started, document=document)
    third = record_event(session, AuditEventType.extraction_failed, document=document)

    assert first.id < second.id < third.id
    stored = session.scalars(
        select(AuditEvent).where(AuditEvent.document_id == document.id).order_by(AuditEvent.id)
    ).all()
    assert [event.event_type for event in stored] == [
        AuditEventType.document_uploaded.value,
        AuditEventType.extraction_started.value,
        AuditEventType.extraction_failed.value,
    ]


def test_audit_detail_defaults_to_empty_mapping(session: Session) -> None:
    document = _document(session)
    event = record_event(session, AuditEventType.document_uploaded, document=document)
    session.expire(event)
    assert event.detail == {}
