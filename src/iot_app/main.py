import os
from datetime import datetime, timezone
from enum import Enum
from http import HTTPStatus
from typing import Any, Dict, List, Optional

import psycopg
import requests
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from psycopg.rows import dict_row
from pydantic import BaseModel, Field


SERVICE_NAME = os.getenv("SERVICE_NAME", "iot-ingestion")
SERVICE_VERSION = os.getenv("SERVICE_VERSION", "0.5.0")
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "local-dev-token")
AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://ai-service:9000").rstrip("/")

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "db")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_USER = os.getenv("POSTGRES_USER", "lab05")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "lab05pass")
POSTGRES_DB = os.getenv("POSTGRES_DB", "iotdb")


app = FastAPI(
    title="FIT4110 Lab 05 - IoT Ingestion Service",
    version=SERVICE_VERSION,
    description=(
        "IoT Ingestion API running in a Docker Compose stack with PostgreSQL and "
        "a mock AI service for Lab 05 readiness verification."
    ),
)


class SensorMetric(str, Enum):
    temperature = "temperature"
    humidity = "humidity"
    motion = "motion"
    smoke = "smoke"


class SensorUnit(str, Enum):
    celsius = "celsius"
    percent = "percent"
    boolean = "boolean"
    ppm = "ppm"


class ProblemDetails(BaseModel):
    type: str = "about:blank"
    title: str
    status: int = Field(..., ge=400, le=599)
    detail: str
    instance: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


class DependencyStatus(BaseModel):
    ready: bool
    detail: str


class ReadinessResponse(BaseModel):
    status: str
    service: str
    version: str
    db: DependencyStatus
    ai: DependencyStatus


class SensorReadingCreate(BaseModel):
    device_id: str = Field(..., min_length=3, examples=["ESP32-LAB-A01"])
    metric: SensorMetric = Field(..., examples=["temperature"])
    value: float = Field(
        ...,
        ge=-40,
        le=80,
        description="Boundary range used in Lab 03, Lab 04 and Lab 05: -40 to 80.",
        examples=[31.5],
    )
    unit: Optional[SensorUnit] = Field(default=None, examples=["celsius"])
    timestamp: datetime = Field(..., examples=["2026-05-13T08:30:00+07:00"])


class SensorReading(BaseModel):
    reading_id: str
    device_id: str
    metric: SensorMetric
    value: float
    unit: Optional[SensorUnit] = None
    timestamp: str
    created_at: str


class SensorReadingCreated(BaseModel):
    reading_id: str
    device_id: str
    metric: SensorMetric
    accepted: bool
    created_at: str


READINGS: List[Dict[str, Any]] = []


def status_title(status_code: int) -> str:
    try:
        return HTTPStatus(status_code).phrase
    except ValueError:
        return "HTTP Error"


def build_problem(
    *,
    status_code: int,
    title: str,
    detail: str,
    instance: Optional[str] = None,
    problem_type: str = "about:blank",
) -> Dict[str, Any]:
    problem = {
        "type": problem_type,
        "title": title,
        "status": status_code,
        "detail": detail,
    }
    if instance:
        problem["instance"] = instance
    return problem


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict):
        problem = exc.detail
    else:
        problem = build_problem(
            status_code=exc.status_code,
            title=status_title(exc.status_code),
            detail=str(exc.detail),
            instance=str(request.url.path),
        )

    problem.setdefault("status", exc.status_code)
    problem.setdefault("title", status_title(exc.status_code))
    problem.setdefault("type", "about:blank")
    problem.setdefault("detail", "Request failed")
    problem.setdefault("instance", str(request.url.path))

    return JSONResponse(
        status_code=exc.status_code,
        content=problem,
        media_type="application/problem+json",
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    first_error = exc.errors()[0] if exc.errors() else {}
    location = ".".join(str(item) for item in first_error.get("loc", []))
    message = first_error.get("msg", "Request validation error")
    detail = f"{location}: {message}" if location else message

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=build_problem(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            title="Validation error",
            detail=detail,
            instance=str(request.url.path),
            problem_type="https://smart-campus.local/problems/validation-error",
        ),
        media_type="application/problem+json",
    )


def verify_bearer_token(authorization: Optional[str] = Header(default=None)) -> None:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=build_problem(
                status_code=status.HTTP_401_UNAUTHORIZED,
                title="Unauthorized",
                detail="Missing Authorization header",
                problem_type="https://smart-campus.local/problems/unauthorized",
            ),
        )

    expected = f"Bearer {AUTH_TOKEN}"
    if authorization != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=build_problem(
                status_code=status.HTTP_401_UNAUTHORIZED,
                title="Unauthorized",
                detail="Invalid bearer token",
                problem_type="https://smart-campus.local/problems/unauthorized",
            ),
        )


def db_connection():
    return psycopg.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        dbname=POSTGRES_DB,
        connect_timeout=3,
        row_factory=dict_row,
    )


def ensure_schema() -> None:
    with db_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sensor_readings (
                reading_id TEXT PRIMARY KEY,
                device_id TEXT NOT NULL,
                metric TEXT NOT NULL,
                value DOUBLE PRECISION NOT NULL,
                unit TEXT,
                timestamp TEXT NOT NULL,
                created_at TEXT NOT NULL,
                ai_summary TEXT
            )
            """
        )


def db_status() -> DependencyStatus:
    try:
        ensure_schema()
        return DependencyStatus(ready=True, detail="PostgreSQL is reachable")
    except Exception as exc:
        return DependencyStatus(ready=False, detail=str(exc))


def ai_status() -> DependencyStatus:
    try:
        response = requests.get(f"{AI_SERVICE_URL}/health", timeout=3)
        response.raise_for_status()
        return DependencyStatus(ready=True, detail="AI service is reachable")
    except Exception as exc:
        return DependencyStatus(ready=False, detail=str(exc))


def call_ai_prediction(payload: SensorReadingCreate) -> Dict[str, Any]:
    try:
        response = requests.post(
            f"{AI_SERVICE_URL}/predict",
            json={
                "device_id": payload.device_id,
                "metric": payload.metric.value,
                "value": payload.value,
                "unit": payload.unit.value if payload.unit else None,
                "timestamp": payload.timestamp.isoformat(),
            },
            timeout=3,
        )
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        return {"status": "unavailable", "detail": str(exc)}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def next_reading_id() -> str:
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"R-{today}-{len(READINGS) + 1:04d}"


def save_reading(item: Dict[str, Any], ai_summary: Dict[str, Any]) -> None:
    ensure_schema()
    with db_connection() as conn:
        conn.execute(
            """
            INSERT INTO sensor_readings (
                reading_id, device_id, metric, value, unit, timestamp, created_at, ai_summary
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (reading_id) DO NOTHING
            """,
            (
                item["reading_id"],
                item["device_id"],
                item["metric"],
                item["value"],
                item["unit"],
                item["timestamp"],
                item["created_at"],
                str(ai_summary),
            ),
        )


def load_latest(device_id: Optional[str], limit: int) -> List[Dict[str, Any]]:
    ensure_schema()
    query = """
        SELECT reading_id, device_id, metric, value, unit, timestamp, created_at
        FROM sensor_readings
    """
    params: List[Any] = []
    if device_id:
        query += " WHERE device_id = %s"
        params.append(device_id)
    query += " ORDER BY created_at DESC LIMIT %s"
    params.append(limit)

    with db_connection() as conn:
        rows = conn.execute(query, params).fetchall()

    return list(reversed(rows))


def load_reading(reading_id: str) -> Optional[Dict[str, Any]]:
    ensure_schema()
    with db_connection() as conn:
        return conn.execute(
            """
            SELECT reading_id, device_id, metric, value, unit, timestamp, created_at
            FROM sensor_readings
            WHERE reading_id = %s
            """,
            (reading_id,),
        ).fetchone()


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service=SERVICE_NAME,
        version=SERVICE_VERSION,
    )


@app.get("/readiness", response_model=ReadinessResponse)
def readiness() -> ReadinessResponse:
    db = db_status()
    ai = ai_status()
    return ReadinessResponse(
        status="ready" if db.ready and ai.ready else "degraded",
        service=SERVICE_NAME,
        version=SERVICE_VERSION,
        db=db,
        ai=ai,
    )


@app.post(
    "/readings",
    response_model=SensorReadingCreated,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_bearer_token)],
    responses={
        401: {"model": ProblemDetails},
        422: {"model": ProblemDetails},
        503: {"model": ProblemDetails},
    },
)
def create_reading(payload: SensorReadingCreate, response: Response) -> SensorReadingCreated:
    if payload.metric == SensorMetric.temperature and payload.value >= 70:
        response.headers["X-Warning"] = "high-temperature"

    reading_id = next_reading_id()
    created_at = now_iso()
    ai_summary = call_ai_prediction(payload)

    item = {
        "reading_id": reading_id,
        "device_id": payload.device_id,
        "metric": payload.metric.value,
        "value": payload.value,
        "unit": payload.unit.value if payload.unit else None,
        "timestamp": payload.timestamp.isoformat(),
        "created_at": created_at,
    }
    READINGS.append(item)

    try:
        save_reading(item, ai_summary)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=build_problem(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                title="Service Unavailable",
                detail=f"Database is not ready: {exc}",
                instance="/readings",
                problem_type="https://smart-campus.local/problems/dependency-unavailable",
            ),
        ) from exc

    return SensorReadingCreated(
        reading_id=reading_id,
        device_id=payload.device_id,
        metric=payload.metric,
        accepted=True,
        created_at=created_at,
    )


@app.get("/readings/latest", dependencies=[Depends(verify_bearer_token)])
def latest_readings(
    device_id: Optional[str] = Query(default=None),
    limit: int = Query(default=10, ge=1, le=100),
) -> Dict[str, List[Dict[str, Any]]]:
    try:
        items = load_latest(device_id, limit)
    except Exception:
        items = READINGS
        if device_id:
            items = [item for item in items if item["device_id"] == device_id]
        items = items[-limit:]

    return {"items": items}


@app.get("/readings/{reading_id}", dependencies=[Depends(verify_bearer_token)])
def get_reading(reading_id: str) -> Dict[str, Any]:
    try:
        item = load_reading(reading_id)
        if item:
            return item
    except Exception:
        pass

    for item in READINGS:
        if item["reading_id"] == reading_id:
            return item

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=build_problem(
            status_code=status.HTTP_404_NOT_FOUND,
            title="Not Found",
            detail=f"Reading {reading_id} does not exist",
            instance=f"/readings/{reading_id}",
            problem_type="https://smart-campus.local/problems/not-found",
        ),
    )
