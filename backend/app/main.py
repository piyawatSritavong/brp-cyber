import logging
import os
import sys
import time
from uuid import UUID, uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from pythonjsonlogger import jsonlogger

from app.api.bootstrap import router as bootstrap_router
from app.api.control_plane import router as control_plane_router
from app.api.events import router as events_router
from app.api.enterprise import router as enterprise_router
from app.api.assurance import router as assurance_router
from app.api.guardrails import router as guardrails_router
from app.api.health import router as health_router
from app.api.ingest import router as ingest_router
from app.api.integrations import router as integrations_router
from app.api.competitive import router as competitive_router
from app.api.orchestrator import router as orchestrator_router
from app.api.purple import router as purple_router
from app.api.red_sim import router as red_sim_router
from app.api.sites import router as sites_router
from app.core.config import settings
from app.db.models import Base
from app.db.session import engine
from app.services.autonomous_runtime import autonomous_runtime
from app.services.runtime_state import runtime_state
from app.services.enterprise.slo import record_http_result

REQUEST_COUNT = Counter("brp_http_requests_total", "Total HTTP requests", ["method", "path", "status"])
REQUEST_LATENCY = Histogram("brp_http_request_duration_seconds", "HTTP request latency", ["method", "path"])

SAFE_PATH_PREFIXES = ("/health", "/metrics", "/guardrails")
SAFE_PATH_EXACT = {"/", "/bootstrap/phase0/init-db"}


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    formatter = jsonlogger.JsonFormatter("%(asctime)s %(name)s %(levelname)s %(message)s")
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)


def _allowed_origins() -> list[str]:
    return [origin.strip() for origin in settings.cors_allow_origins.split(",") if origin.strip()]


configure_logging()
logger = logging.getLogger("brp_cyber.api")

app = FastAPI(title=settings.app_name)

cors_origins = _allowed_origins()
cors_methods = [method.strip().upper() for method in settings.cors_allow_methods.split(",") if method.strip()]
cors_headers = [header.strip() for header in settings.cors_allow_headers.split(",") if header.strip()]
if not cors_headers:
    cors_headers = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins or ["*"],
    allow_credentials=True,
    allow_methods=cors_methods or ["*"],
    allow_headers=cors_headers,
)

app.include_router(health_router)
app.include_router(bootstrap_router)
app.include_router(control_plane_router)
app.include_router(guardrails_router)
app.include_router(events_router)
app.include_router(ingest_router)
app.include_router(integrations_router)
app.include_router(purple_router)
app.include_router(red_sim_router)
app.include_router(orchestrator_router)
app.include_router(enterprise_router)
app.include_router(assurance_router)
app.include_router(sites_router)
app.include_router(competitive_router)


@app.on_event("startup")
async def startup_event() -> None:
    # Do not auto-run background loops while pytest is executing.
    if os.getenv("PYTEST_CURRENT_TEST"):
        return
    if settings.auto_init_db_on_startup:
        Base.metadata.create_all(bind=engine)
    if settings.autonomous_orchestration_enabled:
        state = autonomous_runtime.start()
        logger.info("autonomous_runtime_started", extra={"state": state})


@app.on_event("shutdown")
async def shutdown_event() -> None:
    state = autonomous_runtime.stop()
    logger.info("autonomous_runtime_stopped", extra={"state": state})


@app.middleware("http")
async def trace_middleware(request: Request, call_next):
    start = time.perf_counter()
    tenant_id = request.headers.get("x-tenant-id", "unknown")
    correlation_id = request.headers.get("x-correlation-id", str(uuid4()))
    trace_id = request.headers.get("x-trace-id", str(uuid4()))

    request.state.tenant_id = tenant_id
    request.state.correlation_id = correlation_id
    request.state.trace_id = trace_id

    path = request.url.path
    if runtime_state.is_kill_switch_enabled() and not path.startswith(SAFE_PATH_PREFIXES) and path not in SAFE_PATH_EXACT:
        return JSONResponse(status_code=503, content={"detail": "kill_switch_enabled"})

    try:
        response = await call_next(request)
    except Exception:
        logger.exception(
            "request_failed",
            extra={
                "path": request.url.path,
                "method": request.method,
                "tenant_id": tenant_id,
                "correlation_id": correlation_id,
                "trace_id": trace_id,
            },
        )
        response = JSONResponse(status_code=500, content={"detail": "internal_server_error"})
        origin = request.headers.get("origin", "")
        allowed = _allowed_origins()
        if "*" in allowed:
            response.headers["access-control-allow-origin"] = "*"
        elif origin and origin in allowed:
            response.headers["access-control-allow-origin"] = origin
            response.headers["vary"] = "Origin"
            response.headers["access-control-allow-credentials"] = "true"
        return response

    duration = time.perf_counter() - start
    status = str(response.status_code)
    REQUEST_COUNT.labels(request.method, path, status).inc()
    REQUEST_LATENCY.labels(request.method, path).observe(duration)
    if tenant_id != "unknown":
        try:
            parsed_tenant_id = UUID(tenant_id)
            record_http_result(tenant_id=parsed_tenant_id, duration_seconds=duration, success=response.status_code < 500)
        except Exception:
            logger.exception("slo_record_failed", extra={"tenant_id": tenant_id, "path": path})

    response.headers["x-correlation-id"] = correlation_id
    response.headers["x-trace-id"] = trace_id
    return response


@app.get("/metrics")
def metrics() -> PlainTextResponse:
    return PlainTextResponse(generate_latest().decode("utf-8"), media_type=CONTENT_TYPE_LATEST)


@app.get("/")
def root() -> dict[str, str]:
    return {"service": settings.app_name, "status": "running"}
