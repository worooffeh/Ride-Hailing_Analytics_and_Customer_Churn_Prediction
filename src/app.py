
from fastapi import FastAPI
from pydantic import BaseModel
import joblib, pandas as pd
from pathlib import Path

app = FastAPI(title="RideWise Churn Scoring API")
bundle = joblib.load(Path(__file__).parent.parent / "models" / "churn_rf.joblib")
model, FEATS = bundle["model"], bundle["features"]

class RiderFeatures(BaseModel):
    features: dict

@app.get("/health")
def health():
    return {"status": "ok", "n_features": len(FEATS)}

@app.post("/score")
def score(payload: RiderFeatures):
    row = pd.DataFrame([{f: payload.features.get(f, 0) for f in FEATS}])
    prob = float(model.predict_proba(row)[0, 1])
    band = "High" if prob >= 0.6 else "Medium" if prob >= 0.35 else "Low"
    return {"churn_probability": round(prob, 4), "risk_band": band}
