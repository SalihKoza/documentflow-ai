"""FastAPI uygulama giriş noktası (D-004).

FastAPI yalnızca API ve transport katmanında kullanılır. Extraction, validation
ve diğer çekirdek iş mantığı ayrı modüllerde, framework'ten bağımsız tutulur.
"""

from fastapi import FastAPI

from documentflow.api import health
from documentflow.core.config import get_settings


def create_app() -> FastAPI:
    """Uygulama fabrikası: router'ları bağlar ve FastAPI örneğini döndürür."""
    settings = get_settings()
    app = FastAPI(
        title="DocumentFlow AI",
        version="0.1.0",
        debug=settings.app_env == "development",
    )
    app.include_router(health.router)
    return app


app = create_app()
