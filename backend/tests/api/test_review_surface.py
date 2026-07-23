"""Review yüzeyi (FastAPI + server-rendered HTML) uçtan uca testleri.

Canlı PostgreSQL gerektirir; yoksa `engine` fixture'ı modülü atlar. Auth yoktur
(tek kullanıcı), bu yüzden istekler kimlik bilgisi taşımaz.

HTML iddiaları bilinçli olarak dar tutulur: alan kimlikleri ve durum metinleri
kontrol edilir, sayfa düzeni değil.
"""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from documentflow.api.deps import get_db, get_extractor
from documentflow.core.config import get_settings
from documentflow.extraction import RecordedExtractor
from documentflow.main import create_app
from tests.extraction._fixtures import ok_field, wire_json, wire_payload
from tests.ingestion._pdf_builder import image_only_pdf, text_layer_pdf


def _inconsistent_payload() -> dict:
    """Hem `review` (FNO-001) hem `blocking` (ARITH-001) sinyali üreten payload."""
    payload = wire_payload()
    payload["header"]["fatura_no"] = ok_field("A-2025/000123")
    payload["header"]["genel_toplam"] = ok_field("3.599,00")
    return payload


@pytest.fixture
def client(
    session: Session, storage_root: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[TestClient]:
    monkeypatch.setenv("STORAGE_ROOT", str(storage_root))
    get_settings.cache_clear()
    app = create_app()
    app.dependency_overrides[get_db] = lambda: session
    app.dependency_overrides[get_extractor] = lambda: RecordedExtractor(
        wire_json(_inconsistent_payload())
    )
    with TestClient(app) as test_client:
        yield test_client
    get_settings.cache_clear()


def _upload(client: TestClient, data: bytes | None = None) -> object:
    return client.post(
        "/documents",
        files={"upload": ("ornek.pdf", data or text_layer_pdf(), "application/pdf")},
    )


def _run_id(client: TestClient) -> int:
    response = client.post(
        "/documents",
        files={"upload": ("ornek.pdf", text_layer_pdf(), "application/pdf")},
        follow_redirects=False,
    )
    assert response.status_code == 303
    return int(response.headers["location"].rsplit("/", 1)[1])


def _event_types(client: TestClient, run_id: int) -> list[str]:
    body = client.get(f"/runs/{run_id}/audit").json()
    return [event["event_type"] for event in body["events"]]


# --- Sayfalar -----------------------------------------------------------------------------


def test_index_offers_upload_and_shows_demo_banner(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert 'action="/documents"' in response.text
    # Kaydedilmis yanit kullanildigi kullanicidan gizlenmez.
    assert "Demo modu" in response.text


def test_upload_runs_the_whole_chain_and_lands_on_review(client: TestClient) -> None:
    response = _upload(client)
    assert response.status_code == 200
    assert "Deterministik sinyaller (2)" in response.text
    assert "header.genel_toplam" in response.text
    assert "header_arithmetic" in response.text
    assert "invoice_number_format" in response.text


def test_out_of_scope_upload_is_rejected_and_listed(client: TestClient) -> None:
    response = _upload(client, image_only_pdf())
    assert response.status_code == 200
    assert "reddedildi" in response.text
    assert "no_text_layer" in response.text


def test_unknown_run_returns_404(client: TestClient) -> None:
    assert client.get("/runs/999999").status_code == 404


# --- Düzeltme ve onay ---------------------------------------------------------------------


def test_correction_updates_the_review_screen(client: TestClient) -> None:
    run_id = _run_id(client)
    response = client.post(
        f"/runs/{run_id}/corrections",
        data={"field_path": "header.genel_toplam", "new_value": "3.600,00"},
    )
    assert response.status_code == 200
    # Blocking sinyal kalkti, uyari sinyali kaldi. Sayim uzerinden dogrulanir:
    # `header_arithmetic` metni sayfada hala gorunur, cunku audit tablosu
    # cikarimin ORIJINAL sinyallerini korur (tasarim geregi).
    assert "Deterministik sinyaller (1)" in response.text
    assert "invoice_number_format" in response.text
    assert "Düzeltmeler (1)" in response.text


def test_unparseable_correction_returns_400(client: TestClient) -> None:
    run_id = _run_id(client)
    response = client.post(
        f"/runs/{run_id}/corrections",
        data={"field_path": "header.ara_toplam", "new_value": "uc bin lira"},
    )
    assert response.status_code == 400


def test_unknown_field_path_returns_400(client: TestClient) -> None:
    run_id = _run_id(client)
    response = client.post(
        f"/runs/{run_id}/corrections",
        data={"field_path": "header.olmayan_alan", "new_value": "1"},
    )
    assert response.status_code == 400


def test_approval_marks_the_run_and_hides_correction_form(client: TestClient) -> None:
    run_id = _run_id(client)
    response = client.post(f"/runs/{run_id}/approve")
    assert response.status_code == 200
    assert "Onaylandı" in response.text
    assert f'action="/runs/{run_id}/corrections"' not in response.text


def test_second_approval_returns_409(client: TestClient) -> None:
    run_id = _run_id(client)
    client.post(f"/runs/{run_id}/approve")
    assert client.post(f"/runs/{run_id}/approve").status_code == 409


# --- Export -------------------------------------------------------------------------------


def test_export_without_approval_is_refused(client: TestClient) -> None:
    run_id = _run_id(client)
    response = client.post(f"/runs/{run_id}/export")
    assert response.status_code == 409
    assert "onaylanmamis" in response.json()["detail"]


def test_export_after_approval_returns_the_frozen_payload(client: TestClient) -> None:
    run_id = _run_id(client)
    client.post(
        f"/runs/{run_id}/corrections",
        data={"field_path": "header.genel_toplam", "new_value": "3.600,00"},
    )
    client.post(f"/runs/{run_id}/approve")

    response = client.post(f"/runs/{run_id}/export")
    assert response.status_code == 200
    body = response.json()
    assert body["extraction_run_id"] == run_id
    assert body["correction_count"] == 1
    assert len(body["payload_sha256"]) == 64
    assert body["invoice"]["header"]["genel_toplam"]["value"] == "3600.00"


def test_get_on_the_export_path_is_not_allowed(client: TestClient) -> None:
    """Export yolu yalnızca POST için kayıtlıdır."""
    run_id = _run_id(client)
    assert client.get(f"/runs/{run_id}/export").status_code == 405


def test_the_old_side_effectful_get_url_is_gone(client: TestClient) -> None:
    """Yan etkili `GET .../export.json` rotası kaldırıldı."""
    run_id = _run_id(client)
    assert client.get(f"/runs/{run_id}/export.json").status_code == 404


def test_get_requests_create_no_export_and_no_audit_event(client: TestClient) -> None:
    """Hiçbir GET export kaydı veya export audit olayı üretmez.

    Çıkarım ONAYLIDIR: yani export mümkün olduğu hâlde, yalnızca GET yapıldığında
    oluşmamalıdır. Browser prefetch veya otomatik link taraması bu yüzden zararsızdır.
    """
    run_id = _run_id(client)
    client.post(f"/runs/{run_id}/approve")

    client.get(f"/runs/{run_id}")
    client.get(f"/runs/{run_id}/export")
    client.get(f"/runs/{run_id}/export.json")
    client.get(f"/runs/{run_id}/audit")

    events = _event_types(client, run_id)
    assert "export_created" not in events
    assert "export_rejected" not in events


def test_review_page_export_uses_a_post_form(client: TestClient) -> None:
    """Onaydan sonra export bir link değil, POST formudur."""
    run_id = _run_id(client)
    response = client.post(f"/runs/{run_id}/approve")

    assert f'action="/runs/{run_id}/export"' in response.text
    assert 'method="post"' in response.text
    assert f'href="/runs/{run_id}/export.json"' not in response.text


def test_successful_post_creates_exactly_one_export_event(client: TestClient) -> None:
    run_id = _run_id(client)
    client.post(f"/runs/{run_id}/approve")

    assert client.post(f"/runs/{run_id}/export").status_code == 200
    assert _event_types(client, run_id).count("export_created") == 1


def test_two_explicit_posts_create_two_export_records(client: TestClient) -> None:
    """İki açık POST iki ayrı export işlemidir; ikisi de kaydedilir.

    Aynı onaylı anlık görüntüden üretildikleri için hash AYNIDIR: değişen şey
    "ne aktarıldı" değil, "kaç kez aktarıldı"dır.
    """
    run_id = _run_id(client)
    client.post(f"/runs/{run_id}/approve")

    first = client.post(f"/runs/{run_id}/export").json()
    second = client.post(f"/runs/{run_id}/export").json()

    assert first["export_id"] != second["export_id"]
    assert first["payload_sha256"] == second["payload_sha256"]
    assert _event_types(client, run_id).count("export_created") == 2


# --- Audit --------------------------------------------------------------------------------


def test_audit_endpoint_lists_events_in_order(client: TestClient) -> None:
    run_id = _run_id(client)
    client.post(
        f"/runs/{run_id}/corrections",
        data={"field_path": "header.genel_toplam", "new_value": "3.600,00"},
    )
    client.post(f"/runs/{run_id}/approve")
    client.post(f"/runs/{run_id}/export")

    body = client.get(f"/runs/{run_id}/audit").json()
    sequences = [event["sequence"] for event in body["events"]]
    assert sequences == sorted(sequences)
    assert [event["event_type"] for event in body["events"]] == [
        "document_uploaded",
        "extraction_started",
        "extraction_completed",
        "validation_completed",
        "flags_generated",
        "correction_applied",
        "approved",
        "export_created",
    ]


def test_rejected_export_attempt_is_visible_in_the_audit(client: TestClient) -> None:
    run_id = _run_id(client)
    client.post(f"/runs/{run_id}/export")
    body = client.get(f"/runs/{run_id}/audit").json()
    assert "export_rejected" in [event["event_type"] for event in body["events"]]


def test_audit_response_carries_no_field_values(client: TestClient) -> None:
    run_id = _run_id(client)
    client.post(
        f"/runs/{run_id}/corrections",
        data={"field_path": "header.satici_unvan", "new_value": "Duzeltilmis Unvan A.S."},
    )
    body = client.get(f"/runs/{run_id}/audit").text
    assert "Duzeltilmis Unvan" not in body
    assert "ornek.pdf" not in body
