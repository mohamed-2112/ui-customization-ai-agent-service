import logging
from uuid import uuid4

from fastapi import FastAPI, Request

from app.api.health import router as health_router
from app.api.ui_customization import router as ui_customization_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.core.request_context import request_id_context


configure_logging()

logger = logging.getLogger(__name__)


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
)


@app.middleware("http")
async def add_request_context(request: Request, call_next):
    request_id = request.headers.get("X-Request-Id", str(uuid4()))
    token = request_id_context.set(request_id)

    try:
        logger.info(
            "http_request_started",
            extra={
                "method": request.method,
                "path": request.url.path,
            },
        )

        response = await call_next(request)

        response.headers["X-Request-Id"] = request_id

        logger.info(
            "http_request_finished",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
            },
        )

        return response

    finally:
        request_id_context.reset(token)


app.include_router(health_router)
app.include_router(ui_customization_router)


@app.get("/")
def root():
    return {
        "message": "AI Agent Service is running",
        "environment": settings.app_env,
    }