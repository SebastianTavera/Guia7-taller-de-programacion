"""Vitreo FastAPI application: middleware, error handlers and routers."""

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware

import vitreo.models  # noqa: F401  (registers the tables on Base.metadata)
from vitreo.api.errors import error_response, register_error_handlers
from vitreo.api.routers import admin, auth, citas, medicos, pacientes, triage
from vitreo.config import settings
from vitreo.db import Base, engine

API_VERSION = "1.0.0"
MAX_BODY_BYTES = 64 * 1024

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
}
# Swagger UI loads its own scripts and styles, so it cannot use the strict API policy.
DOCS_PATHS = ("/docs", "/redoc")

DESCRIPTION = """
**Vitreo API**: medical appointments and emergency triage (ESI scale).

Authenticate with `POST /api/v1/auth/login`, then click **Authorize** and paste the `access_token`.
Roles: `ADMIN`, `MEDICO`, `ENFERMERIA`, `RECEPCION`.
"""


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    Base.metadata.create_all(bind=engine)
    yield


async def security_middleware(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    content_length = request.headers.get("content-length", "0")
    if not content_length.isdigit() or int(content_length) > MAX_BODY_BYTES:
        return error_response(status.HTTP_413_CONTENT_TOO_LARGE, f"Request body limit is {MAX_BODY_BYTES} bytes.")

    response = await call_next(request)
    response.headers.update(SECURITY_HEADERS)
    if request.url.path.startswith(DOCS_PATHS):
        del response.headers["Content-Security-Policy"]
    if settings.is_production:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


def create_app() -> FastAPI:
    # API docs are an inventory of the attack surface: only published outside production.
    docs = not settings.is_production
    app = FastAPI(
        title="Vitreo API",
        version=API_VERSION,
        description=DESCRIPTION,
        lifespan=lifespan,
        docs_url="/docs" if docs else None,
        redoc_url="/redoc" if docs else None,
        openapi_url="/openapi.json" if docs else None,
    )
    app.middleware("http")(security_middleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_methods=["GET", "POST", "PATCH"],
        allow_headers=["Authorization", "Content-Type"],
    )
    register_error_handlers(app)
    for module in (auth, admin, pacientes, medicos, citas, triage):
        app.include_router(module.router)

    @app.get("/health", tags=["Health"], summary="Health check")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": API_VERSION}

    return app


app = create_app()
