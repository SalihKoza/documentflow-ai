"""Health check endpoint.

Sistemin ayakta olduğunu doğrulayan sade bir kontrol. Veritabanı bağlantısı
gerektirmez; yalnızca uygulamanın yanıt verdiğini bildirir.
"""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Basit canlılık kontrolü."""
    return {"status": "ok"}
