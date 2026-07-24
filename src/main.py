import json
import os
import time
import uuid
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Paths & thresholds (all overridable via environment variables)
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(os.getenv("PROJECT_ROOT", str(Path(__file__).resolve().parent.parent))).expanduser().resolve()


def resolve_path(env_name: str, default: Path) -> Path:
    raw_value = os.getenv(env_name)
    if not raw_value:
        return default

    candidate = Path(raw_value).expanduser()
    return candidate if candidate.is_absolute() else (PROJECT_ROOT / candidate).resolve()


DATA_PATH = resolve_path("DATA_PATH", PROJECT_ROOT / "data" / "analytics_table.csv")
MODEL_PATH = resolve_path("MODEL_PATH", PROJECT_ROOT / "models" / "churn_rf.joblib")
SEG_MODEL_PATH = resolve_path("SEGMENTATION_MODEL_PATH", PROJECT_ROOT / "models" / "segmentation_kmeans.joblib")
FEATURE_MANIFEST_PATH = resolve_path(
    "FEATURE_MANIFEST_PATH", PROJECT_ROOT / "models" / "feature_columns.json"
)

DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
SEG_MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)

HIGH = float(os.getenv("HIGH_RISK_THRESHOLD", "0.60"))
MEDIUM = float(os.getenv("MEDIUM_RISK_THRESHOLD", "0.35"))


# ---------------------------------------------------------------------------
# Model loaders  (each file is loaded only once per process)
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def load_churn_bundle() -> dict:
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Churn model not found: {MODEL_PATH}")
    return joblib.load(MODEL_PATH)


@lru_cache(maxsize=1)
def load_seg_bundle():
    if not SEG_MODEL_PATH.exists():
        raise FileNotFoundError(f"Segmentation model not found: {SEG_MODEL_PATH}")
    return joblib.load(SEG_MODEL_PATH)


def load_feature_names() -> list[str]:
    if FEATURE_MANIFEST_PATH.exists():
        return json.loads(FEATURE_MANIFEST_PATH.read_text(encoding="utf-8"))
    return list(load_churn_bundle()["features"])


def load_segmentation_feature_names() -> list[str]:
    return list(load_seg_bundle()["features"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------
class PredictionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    features: dict[str, float] = Field(
        ..., description="Feature values keyed by training feature names"
    )

class PredictionResponse(BaseModel):
    request_id: str
    churn_probability: float
    risk_band: str
    model_name: str
    latency_ms: float

class SegmentationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    features: dict[str, float] = Field(
        ..., description="Feature values keyed by training feature names"
    )

class SegmentationResponse(BaseModel):
    request_id: str
    segment: int
    segment_name: str | None = None
    model_name: str
    latency_ms: float

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------
app = FastAPI(title="RideWise Churn Scoring API", version="1.0.0")


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------
def _score_row(
    bundle: dict,
    features: dict[str, float],
    start: float,
) -> PredictionResponse:
    """Validate features, run inference, and return a scored response."""
    missing = [f for f in bundle["features"] if f not in features]
    if missing:
        raise HTTPException(status_code=422, detail={"missing_features": missing})

    row = pd.DataFrame([{f: features[f] for f in bundle["features"]}])
    prob = float(bundle["model"].predict_proba(row)[0, 1])
    band = "High" if prob >= HIGH else ("Medium" if prob >= MEDIUM else "Low")

    return PredictionResponse(
        request_id=str(uuid.uuid4()),
        churn_probability=round(prob, 4),
        risk_band=band,
        model_name=bundle.get("model_name", MODEL_PATH.stem),
        latency_ms=round((time.perf_counter() - start) * 1000, 2),
    )


def _segment_row(
    bundle: dict,
    features: dict[str, float],
    start: float,
) -> SegmentationResponse:
    """Validate features, run segmentation inference, and return a segment response."""
    missing = [f for f in bundle["features"] if f not in features]
    if missing:
        raise HTTPException(status_code=422, detail={"missing_features": missing})

    row = pd.DataFrame([{f: features[f] for f in bundle["features"]}])
    prepared = np.log1p(row)
    if bundle.get("scaler") is not None:
        prepared = bundle["scaler"].transform(prepared)

    segment = int(bundle["model"].predict(prepared)[0])
    segment_names = bundle.get("segment_names") or DEFAULT_SEGMENT_NAMES
    segment_name = segment_names.get(segment)
    return SegmentationResponse(
        request_id=str(uuid.uuid4()),
        segment=segment,
        segment_name=segment_name,
        model_name=bundle.get("model_name", SEG_MODEL_PATH.stem),
        latency_ms=round((time.perf_counter() - start) * 1000, 2),
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/", tags=["ops"])
def root():
    """Root endpoint — returns a simple message."""
    return {"message": "RideWise Churn Scoring API is running. "
    "Status: OK."}

@app.get("/health", tags=["ops"])
def health():
    """Liveness probe — always returns 200 when the process is up."""
    return {"status": "ok"}


@app.get("/ready", tags=["ops"])
def ready():
    """Readiness probe — confirms the churn model is loaded."""
    try:
        b = load_churn_bundle()
        return {
            "status": "ready",
            "model_name": b.get("model_name", MODEL_PATH.stem),
            "n_features": len(b["features"]),
        }
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/model/info", tags=["model"])
def model_info():
    """Return metadata for the loaded churn model."""
    b = load_churn_bundle()
    return {
        "model_name": b.get("model_name", MODEL_PATH.stem),
        "metrics":    b.get("metrics"),
        "features":   b["features"],
    }

@app.get("/model/segmentation/info", tags=["model"])
def segmentation_model_info():
    """Return metadata for the loaded segmentation model."""
    b = load_seg_bundle()
    return {
        "model_name": b.get("model_name", SEG_MODEL_PATH.stem),
        "cluster_count": b.get("cluster_count"),
        "features":   b["features"],
    }

@app.post("/predict", response_model=PredictionResponse, tags=["inference"])
def predict(payload: PredictionRequest):
    """Score a single rider and return a churn probability + risk band."""
    return _score_row(load_churn_bundle(), payload.features, time.perf_counter())


@app.post("/predict/batch", response_model=list[PredictionResponse], tags=["inference"])
def predict_batch(payload: list[PredictionRequest]):
    """Score multiple riders in one request."""
    b = load_churn_bundle()
    return [_score_row(b, item.features, time.perf_counter()) for item in payload]


@app.post("/segment", response_model=SegmentationResponse, tags=["segmentation"])
def segment(payload: SegmentationRequest):
    """Assign a rider to a saved customer segment using the segmentation payload."""
    return _segment_row(load_seg_bundle(), payload.features, time.perf_counter())


DEFAULT_SEGMENT_NAMES = {
    0: "Cooling casual riders",
    1: "Low-value at-risk riders",
    2: "Power riders",
    3: "Recently active regulars",
}

