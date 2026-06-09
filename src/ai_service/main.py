import os
from typing import List, Optional

from fastapi import FastAPI
from pydantic import BaseModel


SERVICE_NAME = os.getenv("AI_SERVICE_NAME", "ai-service")
SERVICE_VERSION = os.getenv("AI_SERVICE_VERSION", "0.5.0")

app = FastAPI(
    title="FIT4110 Lab 05 - AI Service",
    version=SERVICE_VERSION,
    description="Mock AI service used in the Docker Compose readiness stack.",
)


class PredictionRequest(BaseModel):
    device_id: Optional[str] = None
    metric: Optional[str] = None
    value: Optional[float] = None
    unit: Optional[str] = None
    timestamp: Optional[str] = None


class Prediction(BaseModel):
    status: str
    objects: List[str]
    confidence: List[float]
    model_version: str


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": SERVICE_NAME, "version": SERVICE_VERSION}


@app.post("/predict", response_model=Prediction)
def predict(_: Optional[PredictionRequest] = None) -> Prediction:
    return Prediction(
        status="ok",
        objects=["person", "bicycle"],
        confidence=[0.98, 0.85],
        model_version=SERVICE_VERSION,
    )
