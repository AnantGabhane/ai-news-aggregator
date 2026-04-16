import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from secrets import compare_digest
from threading import Lock
from typing import Any

from dotenv import load_dotenv
from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field

from app.daily_runner import run_daily_pipeline
from app.database.connection import get_database_info
from app.database.models import Base
from app.database.connection import engine

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class RunRequest(BaseModel):
    hours: int = Field(default=24, ge=1, le=168)
    top_n: int = Field(default=10, ge=1, le=25)


class PipelineRunState:
    def __init__(self) -> None:
        self._lock = Lock()
        self._running = False
        self._started_at: str | None = None
        self._finished_at: str | None = None
        self._requested_hours: int | None = None
        self._requested_top_n: int | None = None
        self._latest_result: dict[str, Any] | None = None
        self._latest_error: str | None = None

    def start(self, hours: int, top_n: int) -> bool:
        with self._lock:
            if self._running:
                return False
            self._running = True
            self._started_at = datetime.now(timezone.utc).isoformat()
            self._finished_at = None
            self._requested_hours = hours
            self._requested_top_n = top_n
            self._latest_result = None
            self._latest_error = None
            return True

    def finish(self, result: dict[str, Any]) -> None:
        with self._lock:
            self._running = False
            self._finished_at = datetime.now(timezone.utc).isoformat()
            self._latest_result = result
            self._latest_error = result.get("error")

    def fail(self, error: str) -> None:
        with self._lock:
            self._running = False
            self._finished_at = datetime.now(timezone.utc).isoformat()
            self._latest_result = None
            self._latest_error = error

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "running": self._running,
                "started_at": self._started_at,
                "finished_at": self._finished_at,
                "requested_hours": self._requested_hours,
                "requested_top_n": self._requested_top_n,
                "latest_result": self._latest_result,
                "latest_error": self._latest_error,
            }


run_state = PipelineRunState()


def _ensure_tables() -> None:
    Base.metadata.create_all(bind=engine)


def _require_run_token(
    authorization: str | None = Header(default=None),
    x_run_token: str | None = Header(default=None),
) -> None:
    expected_token = os.getenv("RUN_API_TOKEN")
    if not expected_token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="RUN_API_TOKEN is not configured.",
        )

    provided_token = x_run_token.strip() if x_run_token else None
    if authorization and authorization.lower().startswith("bearer "):
        provided_token = authorization[7:].strip()

    if not provided_token or not compare_digest(provided_token, expected_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid run token.",
        )


def _execute_pipeline(hours: int, top_n: int) -> None:
    try:
        logger.info("Starting background pipeline execution")
        result = run_daily_pipeline(hours=hours, top_n=top_n)
        run_state.finish(result)
        logger.info("Background pipeline execution finished")
    except Exception as exc:
        logger.exception("Background pipeline execution failed")
        run_state.fail(str(exc))


@asynccontextmanager
async def lifespan(_: FastAPI):
    _ensure_tables()
    yield


app = FastAPI(
    title="AI News Aggregator",
    description="Render-friendly trigger service for the AI news aggregation pipeline.",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/")
def root() -> dict[str, Any]:
    return {
        "service": "ai-news-aggregator",
        "status": "ok",
        "endpoints": {
            "health": "/health",
            "run": "/run",
            "run_status": "/run/status",
        },
    }


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "healthy",
        "database": get_database_info(),
        "pipeline": run_state.snapshot(),
    }


@app.get("/run/status")
def get_run_status(_: None = Depends(_require_run_token)) -> dict[str, Any]:
    return run_state.snapshot()


@app.post("/run", status_code=status.HTTP_202_ACCEPTED)
def trigger_run(
    payload: RunRequest,
    background_tasks: BackgroundTasks,
    _: None = Depends(_require_run_token),
) -> dict[str, Any]:
    if not run_state.start(hours=payload.hours, top_n=payload.top_n):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A pipeline run is already in progress.",
        )

    background_tasks.add_task(_execute_pipeline, payload.hours, payload.top_n)
    return {
        "accepted": True,
        "message": "Pipeline run started in the background.",
        "hours": payload.hours,
        "top_n": payload.top_n,
    }
