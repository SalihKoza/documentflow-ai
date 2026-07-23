"""FastAPI uygulama giriş noktası (D-004).

FastAPI yalnızca API ve transport katmanında kullanılır. Extraction, validation
ve diğer çekirdek iş mantığı ayrı modüllerde, framework'ten bağımsız tutulur.
"""

from fastapi import FastAPI

from documentflow.api import health, review
from documentflow.core.config import get_settings


def create_app() -> FastAPI:
    """Uygulama fabrikası: router'ları bağlar ve FastAPI örneğini döndürür."""
    settings = get_settings()
    app = FastAPI(
        title="DocumentFlow AI",
        version="0.1.0",
        debug=settings.app_env == "development",
    )
    # Saklama kökü açıkça burada oluşturulur; `store_document` bilinçli olarak
    # kök oluşturmaz (yapılandırma hatası sessizce yeni bir ağaç açmasın diye).
    settings.storage_root.mkdir(parents=True, exist_ok=True)
    app.include_router(health.router)
    app.include_router(review.router)
    return app


app = create_app()
