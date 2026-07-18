"""Health endpoint testi.

Veritabanı gerektirmez; yalnızca uygulamanın ayakta olduğunu ve /health'in
beklenen yanıtı verdiğini doğrular.
"""

from fastapi.testclient import TestClient

from documentflow.main import app

client = TestClient(app)


def test_health_ok() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
