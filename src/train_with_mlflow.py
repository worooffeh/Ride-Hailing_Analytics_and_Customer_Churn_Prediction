from __future__ import annotations

import json
import os
from pathlib import Path

import joblib
import mlflow
import mlflow.sklearn
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

PROJECT_ROOT = Path(os.getenv("PROJECT_ROOT", str(Path(__file__).resolve().parent.parent))).expanduser().resolve()


def resolve_path(env_name: str, default: Path) -> Path:
    raw_value = os.getenv(env_name)
    if not raw_value:
        return default

    candidate = Path(raw_value).expanduser()
    return candidate if candidate.is_absolute() else (PROJECT_ROOT / candidate).resolve()


DATA_PATH = resolve_path("DATA_PATH", PROJECT_ROOT / "data" / "analytics_table.csv")
MODEL_DIR = resolve_path("MODEL_DIR", PROJECT_ROOT / "models")
MLRUNS_DIR = resolve_path("MLRUNS_DIR", PROJECT_ROOT / "mlruns")
DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
MODEL_DIR.mkdir(parents=True, exist_ok=True)
MLRUNS_DIR.mkdir(parents=True, exist_ok=True)

RANDOM_STATE = 42
TEST_SIZE = 0.25
FEATURE_COLUMNS = [
    "recency",
    "frequency",
    "monetary",
    "avg_fare",
    "tenure",
    "avg_surge",
    "max_surge",
    "tip_rate",
    "trips_per_week",
    "avg_duration",
    "distinct_drivers",
    "weekend_ratio",
    "night_ratio",
    "card_ratio",
    "sessions_count",
    "avg_time_on_app",
    "avg_pages",
    "conversion_rate",
    "age",
    "avg_rating_given",
    "loyalty_rank",
    "was_referred",
]


def evaluate_model(model, X_eval: pd.DataFrame, y_eval: pd.Series) -> dict[str, float]:
    probabilities = model.predict_proba(X_eval)[:, 1]
    predictions = (probabilities >= 0.5).astype(int)
    return {
        "roc_auc": round(roc_auc_score(y_eval, probabilities), 3),
        "pr_auc": round(average_precision_score(y_eval, probabilities), 3),
        "precision": round(precision_score(y_eval, predictions), 3),
        "recall": round(recall_score(y_eval, predictions), 3),
        "f1": round(f1_score(y_eval, predictions), 3),
        "brier_score": round(brier_score_loss(y_eval, probabilities), 3),
    }


def save_feature_manifest(features: list[str]) -> None:
    manifest_path = ROOT / "models" / "feature_columns.json"
    manifest_path.write_text(json.dumps(features, indent=2), encoding="utf-8")
    mlflow.log_artifact(str(manifest_path), artifact_path="artifacts")


def train_and_log() -> None:
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", f"sqlite:///{MLRUNS_DIR / 'mlflow.db'}")
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment("ridewise-churn-prediction")

    df = pd.read_csv(DATA_PATH)
    X = df[FEATURE_COLUMNS].fillna(0)
    y = df["churn"]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=TEST_SIZE,
        stratify=y,
        random_state=RANDOM_STATE,
    )

    with mlflow.start_run(run_name="ridewise-churn-training") as parent_run:
        mlflow.log_params(
            {
                "random_state": RANDOM_STATE,
                "test_size": TEST_SIZE,
                "train_rows": len(X_train),
                "test_rows": len(X_test),
                "target_rate": round(float(y.mean()), 4),
                "feature_count": len(FEATURE_COLUMNS),
                "data_path": str(DATA_PATH),
            }
        )
        mlflow.set_tag("project", "RideWise")
        mlflow.set_tag("model_type", "classification")

        save_feature_manifest(FEATURE_COLUMNS)

        with mlflow.start_run(run_name="LogisticRegression", nested=True) as lr_run:
            lr_model = make_pipeline(
                StandardScaler(),
                LogisticRegression(max_iter=2000, class_weight="balanced", C=0.5),  # MLflow does not support logging pipelines, so we log the model separately after fitting
            )
            lr_model.fit(X_train, y_train)
            lr_metrics = evaluate_model(lr_model, X_test, y_test)
            mlflow.log_params(
                {
                    "model_family": "logistic_regression",
                    "scaler": "StandardScaler",
                    "class_weight": "balanced",
                    "C": 0.5,                                           # Regularization strength 
                    "max_iter": 2000,
                }
            )
            mlflow.log_metrics(lr_metrics)
            mlflow.sklearn.log_model(lr_model, artifact_path="model")
            joblib.dump(
                {"model": lr_model, "features": FEATURE_COLUMNS},
                MODEL_DIR / "churn_lr.joblib",
            )

        with mlflow.start_run(run_name="RandomForest", nested=True) as rf_run:      # Nested run for Random Forest model training and logging
            rf_model = RandomForestClassifier(
                n_estimators=400,                       # Number of trees in the forest, meaning the number of decision trees to be built in the ensemble, ensemble consists of multiple decision trees, and the final prediction is made by aggregating the predictions of all the individual trees
                max_depth=10,                           # Maximum depth of the tree, means the maximum number of levels in each decision tree, deeper trees can capture more complex patterns but may also lead to overfitting, so we limit the depth to 10 to prevent overfitting and improve generalization
                min_samples_leaf=20,                    # Minimum number of samples required to be at a leaf node, means the minimum number of samples that must be present in a leaf node for it to be considered a valid split, setting this parameter helps prevent overfitting by ensuring that each leaf node has enough samples to make reliable predictions, we set it to 20 to ensure that each leaf node has at least 20 samples
                class_weight="balanced",
                random_state=RANDOM_STATE,
                n_jobs=-1,
            )
            rf_model.fit(X_train, y_train)
            rf_metrics = evaluate_model(rf_model, X_test, y_test)
            mlflow.log_params(
                {
                    "model_family": "random_forest",
                    "n_estimators": 400,
                    "max_depth": 10,
                    "min_samples_leaf": 20,
                    "class_weight": "balanced",
                }
            )
            mlflow.log_metrics(rf_metrics)
            mlflow.sklearn.log_model(rf_model, artifact_path="model")
            joblib.dump(
                {"model": rf_model, "features": FEATURE_COLUMNS},
                MODEL_DIR / "churn_rf.joblib",
            )

        print(f"MLflow run completed: {parent_run.info.run_id}")
        print(f"Tracking URI: {tracking_uri}")


if __name__ == "__main__":
    train_and_log()
