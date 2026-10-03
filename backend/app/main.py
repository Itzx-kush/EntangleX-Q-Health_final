import json
import logging
from contextlib import asynccontextmanager
from uuid import uuid4
from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from sqlalchemy import func, select
from .api import ablation, ai, alignment, audit, controlled_comparison, datasets, experiments, jobs, model_cards, models, pipeline, pipelines, protocols, quantum, runs, shift, studies, training, validation, threshold, condition_tasks, quantum_diagnostics

from .api.middleware import BodyLimitMiddleware
from .api.security import authorize
from .api.schemas import ExperimentOut
from .alignment import alignment_contract
from .config import DISCLAIMER, get_settings
from .database import init_db, session_scope
from .demo_readiness import install_verified_demo_artifacts, validate_readiness_configuration
from .dataset_versions.service import ensure_legacy_versions
from .jobs.manager import manager
from .quantum.backends import availability
from .storage.entities import Dataset, Experiment, Job, ModelRecord
from .utils.errors import AppError

settings = get_settings()
logger = logging.getLogger("qhealth")

class SafeJSONFormatter(logging.Formatter):
    def format(self, record):
        # Application calls supply only fixed messages, opaque IDs and exception types.
        return json.dumps({"level": record.levelname, "logger": record.name, "event": record.getMessage()})

handler = logging.StreamHandler()
handler.setFormatter(SafeJSONFormatter())
logger.handlers = [handler]
logger.setLevel(settings.log_level.upper())
logger.propagate = False

@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_readiness_configuration()
    init_db()
    install_verified_demo_artifacts()
    ensure_legacy_versions()
    manager.start()
    logger.info("application_started mode=single_workstation_research")
    try:
        yield
    finally:
        manager.stop()

app = FastAPI(title="EntangleX Q-Health", version="0.1.0", description=DISCLAIMER, lifespan=lifespan)
app.add_middleware(BodyLimitMiddleware, max_bytes=settings.upload_limit + 65536)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=[s.strip() for s in settings.trusted_hosts.split(",")])
cors_origins = [s.strip() for s in settings.cors_origins.split(",") if s.strip()]
allow_credentials = "*" not in cors_origins
app.add_middleware(CORSMiddleware, allow_origins=cors_origins, allow_credentials=allow_credentials, allow_methods=["GET", "POST", "DELETE"], allow_headers=["Content-Type", "Authorization", "Idempotency-Key"], expose_headers=["Content-Disposition", "X-Request-ID"])

@app.middleware("http")
async def request_context(request: Request, call_next):
    request.state.request_id = str(uuid4())
    try:
        response = await call_next(request)
    except Exception as exc:
        # Handle here without re-raising through ServerErrorMiddleware, which
        # could otherwise cause the ASGI server to log raw exception text.
        logger.error("request_failure request_id=%s exception_type=%s", request.state.request_id, type(exc).__name__)
        response = JSONResponse({"error": {"code": "internal_error", "message": "The operation failed. Raw biomedical inputs are not logged.", "request_id": request.state.request_id}}, status_code=500)
    response.headers["X-Request-ID"] = request.state.request_id
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response

@app.exception_handler(AppError)
async def application_error(request: Request, exc: AppError):
    return JSONResponse({"error": {"code": exc.code, "message": exc.message, "request_id": getattr(request.state, "request_id", None)}}, status_code=exc.status)

@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    # Never reflect Pydantic's raw 'input' or context containing medical values.
    fields = [{"location": [str(v) for v in err["loc"]], "type": err["type"]} for err in exc.errors()]
    return JSONResponse({"error": {"code": "validation_error", "message": "Request validation failed. Check the field types and allowed configuration ranges.", "fields": fields, "request_id": getattr(request.state, "request_id", None)}}, status_code=422)

@app.exception_handler(StarletteHTTPException)
async def http_error(request: Request, exc: StarletteHTTPException):
    return JSONResponse({"error": {"code": "http_error", "message": "The requested operation is unavailable.", "request_id": getattr(request.state, "request_id", None)}}, status_code=exc.status_code)

@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc: Exception):
    logger.error("request_failure request_id=%s exception_type=%s", getattr(request.state, "request_id", None), type(exc).__name__)
    return JSONResponse({"error": {"code": "internal_error", "message": "The operation failed. Review installation and configuration; raw biomedical inputs are not logged.", "request_id": getattr(request.state, "request_id", None)}}, status_code=500)

@app.get("/api/health", tags=["health"])
def health():
    return {"status": "ok", "version": "0.1.0", "mode": "single-workstation research prototype", "authentication_required": bool(settings.api_token), "quantum": availability(), "disclaimer": DISCLAIMER}

api = APIRouter(prefix="/api", dependencies=[Depends(authorize)])
from .api import calibration, threshold
for router in [ai.router, audit.router, datasets.router, pipeline.router, pipelines.router, protocols.router, training.router, jobs.router, models.router, model_cards.router, experiments.router, controlled_comparison.router, runs.router, quantum.router, alignment.router, studies.router, validation.router, shift.router, shift.dataset_shift_router, calibration.router, threshold.router, condition_tasks.router, ablation.router, quantum_diagnostics.router]:
    api.include_router(router)

@api.get("/summary", tags=["dashboard"])
def summary():
    with session_scope() as session:
        counts = {"datasets": session.scalar(select(func.count()).select_from(Dataset)),
                  "experiments": session.scalar(select(func.count()).select_from(Experiment).where(Experiment.deleted_at.is_(None))),
                  "ready_models": session.scalar(select(func.count()).select_from(ModelRecord).where(ModelRecord.status == "ready")),
                  "active_jobs": session.scalar(select(func.count()).select_from(Job).where(Job.status.in_(["queued", "running", "cancel_requested"])))}
        experiments_recent = [
            ExperimentOut.model_validate(e).model_dump(mode="json")
            for e in session.scalars(
                select(Experiment)
                .where(Experiment.deleted_at.is_(None))
                .order_by(Experiment.created_at.desc())
                .limit(5)
            )
        ]
    return {"counts": counts, "recent_experiments": experiments_recent, "disclaimer": DISCLAIMER}

@api.get("/system/status", tags=["dashboard"])
def system_status():
    """Expose safe, read-only runtime facts for the research workspace shell."""
    with session_scope() as session:
        jobs = list(session.scalars(select(Job)))
        database_available = True
    root = settings.root
    storage_available = all((root / name).is_dir() for name in ["data", "models", "experiments"])
    return {
        "status": "ok",
        "version": "0.1.0",
        "mode": "single-workstation research prototype",
        "database_available": database_available,
        "storage_available": storage_available,
        "quantum": availability(),
        "model_capabilities": alignment_contract()["models"],
        "supported_models": {
            "classical": ["logistic_regression", "svm", "random_forest"],
            "quantum": ["vqc", "qsvc", "qnn"],
            "qiskit_quantum": ["vqc", "qsvc", "qnn"],
            "pennylane_hybrid": ["hybrid_pennylane_torch"],
        },
        "jobs": {
            "queued": sum(job.status == "queued" for job in jobs),
            "running": sum(job.status == "running" for job in jobs),
            "active": sum(job.status in {"queued", "running", "cancel_requested"} for job in jobs),
        },
    }

app.include_router(api)