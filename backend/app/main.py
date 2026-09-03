from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.logging import get_logger, setup_logging
from app.db.database import init_db

settings = get_settings()
setup_logging(settings.LOG_LEVEL)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "app_starting",
        extra={"env": settings.ENVIRONMENT.value, "version": settings.APP_VERSION},
    )
    await init_db()
    logger.info("database_tables_ready")
    yield
    logger.info("app_shutting_down")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="RecoverFlow - Autonomous Payment Recovery System",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Validation error",
            "errors": exc.errors(),
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "unhandled_exception",
        extra={"path": request.url.path, "method": request.method, "error": str(exc)},
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", "")
    response = await call_next(request)
    if request_id:
        response.headers["X-Request-ID"] = request_id
    return response


from app.api.health import router as health_router
from app.api.payments import router as payments_router
from app.api.webhooks import router as webhook_router
from app.api.customers import router as customer_router
from app.api.recovery_attempts import router as recovery_attempts_router
from app.api.agents import router as agents_router
from app.api.policies import router as policies_router
from app.api.audit import router as audit_router
from app.api.consent import router as consent_router
from app.api.recovery_v2 import router as recovery_v2_router
from app.api.simulate import router as simulate_router
from app.api.auth_routes import router as auth_router
from app.api.monitoring import router as monitoring_router
from app.api.incidents import router as incidents_router
from app.api.alerts import router as alerts_router
from app.api.sentinel import router as sentinel_router
from app.api.investigations import router as investigations_router

app.include_router(health_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(payments_router, prefix="/api")
app.include_router(webhook_router, prefix="/api")
app.include_router(customer_router, prefix="/api")
app.include_router(recovery_attempts_router, prefix="/api")
app.include_router(agents_router, prefix="/api")
app.include_router(policies_router, prefix="/api")
app.include_router(audit_router, prefix="/api")
app.include_router(consent_router, prefix="/api")
app.include_router(recovery_v2_router, prefix="/api")
app.include_router(simulate_router, prefix="/api")
app.include_router(monitoring_router, prefix="/api")
app.include_router(incidents_router, prefix="/api")
app.include_router(alerts_router, prefix="/api")
app.include_router(sentinel_router, prefix="/api")
app.include_router(investigations_router, prefix="/api")


@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }
