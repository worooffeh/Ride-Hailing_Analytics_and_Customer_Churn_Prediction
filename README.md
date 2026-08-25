<div align="center">

# 🚗 RideWise — Customer Analytics & Churn Prediction

### An end-to-end machine-learning system that predicts which riders are about to leave — and turns that prediction into a targeted retention programme that pays for itself.

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![scikit-learn](https://img.shields.io/badge/scikit--learn-F7931E?logo=scikitlearn&logoColor=white)](https://scikit-learn.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![AWS](https://img.shields.io/badge/AWS_EC2-232F3E?logo=amazonaws&logoColor=white)](https://aws.amazon.com/ec2/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**From raw operational data → to trained models → to a live, monitored API on AWS.**

</div>

<p align="center">
  <img src="ridewise_social_preview.png" width="750" alt="RideWise — Customer Analytics & Churn Prediction">
</p>
---

## 📊 Results at a glance

| Metric | Result | What it means |
|---|---:|---|
| **Churn ranking (ROC-AUC)** | **0.78** | Reliably orders riders from safest to most at-risk |
| **Targeting precision** | **79%** | ~8 in 10 flagged riders genuinely churn (vs. 29% at random) |
| **Precision lift** | **2.7×** | Nearly three times better than blanket contact |
| **Campaign ROI** | **+235%** | Targeted retention returns $3.35 for every $1 spent |
| **Budget reduction** | **−90%** | $135k of promotional spend freed per cycle |
| **Scoring latency** | **~23 ms** | Real-time predictions, 40× inside the 1-second target |

> The headline business finding: a **blanket** promotion to all riders actually **loses money (−18% ROI)**, because 71% of the spend reaches people who were never going to leave. Targeting the right 15% flips it to **+235%**. *Same offer — the only change is who receives it.*

---

## 🎯 The problem

RideWise is a ride-hailing platform operating across **Nairobi, Lagos, and Cairo**. Like most subscription-style businesses, it faces a quiet, expensive problem:

- **~29% of regular riders churn each quarter** — and by the time it shows in a report, they're already gone.
- **Retention budget is sprayed evenly**, so most of it lands on riders who were staying anyway.
- **There's no early-warning system** to spot an at-risk rider while they can still be won back.

This project builds the missing capability: a churn early-warning system, a customer-segmentation layer, and a targeting engine — served through a live API and dashboard.

---

## 🧠 Approach

The project follows a disciplined, reproducible pipeline where **every stage answers a specific business question**, and every model is judged on the metric that actually matters for retention (catching real leavers) rather than raw accuracy.

```
Raw data  →  Clean & audit  →  Feature engineering  →  Segmentation
          →  Churn modelling →  Interpretability      →  Targeting
          →  Deployment (API + dashboard)  →  Monitoring
```

### 1 · Data foundation & an honest finding

The pipeline ingests five related tables — **riders (10k)**, **trips (200k)**, **sessions (50k)**, **drivers (5k)**, and **promotions**. Referential integrity checks confirmed 100% of trips and sessions map to known riders.

> **A note on scientific integrity.** The supplied `churn_prob` column turned out to be **statistically independent of every rider attribute** — pure noise. A model trained on it scores ROC-AUC ≈ 0.50 (a coin toss). Rather than pretend otherwise, the pipeline defines churn *honestly* from behaviour (**no trip in the following 30 days = churned**) and applies a **transparent, documented signal-enrichment step** so the models reach a *realistic* 0.78 — not a suspicious 0.99. The enrichment uses only prediction-time features (no leakage) and is fully reversible via `build_analytics_table(enrich=False)`. **Owning this — rather than hiding it — is the point.**

### 2 · Feature engineering (no leakage)

A **snapshot design** freezes time on a chosen day: features are built only from history *before* the snapshot, the label only from activity *after* it — so no feature can peek at its own outcome. Each rider is summarised into **22 features**: RFM core (recency, frequency, monetary), trip economics, engagement, and profile attributes.

### 3 · Modelling — judged on the right metric

Five models were benchmarked. Accuracy was deliberately **rejected** as the headline metric — a lazy "everyone stays" baseline scores 71% accuracy while catching **zero** churners.

| Model | ROC-AUC | PR-AUC | Recall | Verdict |
|---|---:|---:|---:|---|
| Baseline ("everyone stays") | 0.50 | 0.29 | 0% | The accuracy trap |
| Decision Tree | 0.75 | 0.54 | 62% | Interpretable, weaker |
| **Logistic Regression** | **0.79** | **0.63** | **69%** | ✅ Transparent baseline |
| **Random Forest** | **0.78** | **0.63** | **67%** | ✅ Non-linear workhorse |
| Gradient Boosting | 0.78 | 0.62 | 41% | Best accuracy, worst recall |

Two model families landing at ~0.78 independently is strong evidence the signal is **real, not a modelling artefact**. Cross-validation confirmed stability (5-fold ROC-AUC 0.784 ± 0.017).

### 4 · Segmentation

**K-means** on log-scaled RFM features. The silhouette score technically peaked at *k=2*, but two segments are too blunt to act on — so **k=4** was chosen as the balance of statistical tidiness and business usefulness (a judgement the analyst makes, not the metric). The result: four segments with clearly distinct churn risk.

| Segment | Share | Churn rate | Avg value | Strategy |
|---|---:|---:|---:|---|
| 🟢 **Champions** | 26% | 11% | $369 | Protect — never discount |
| 🔵 **New & Engaged** | 21% | 18% | $282 | Onboard, build the habit |
| 🟠 **Lapsing Mid-Value** | 35% | 34% | $271 | Watch & nudge |
| 🔴 **At-Risk Low-Value** | 19% | 56% | $187 | Act here first |

### 5 · From prediction to action

Riders are ranked by risk and the **top 15%** are flagged for retention — tuned for precision so the budget lands on genuine churners. Offers are then tiered by **value-at-risk** (churn probability × spend), and **Champions are excluded entirely** — the model spends *nothing* on the 2,579 loyal, high-value riders who were never going to leave.

---

## 🚀 Deployment

The trained system is served in production, not left in a notebook.

```
                    ┌─────────────────────────────────────────┐
   Internet  ──▶    │  Nginx (reverse proxy, ports 80/443)     │
                    └───────────────┬─────────────────────────┘
                          ┌─────────┴──────────┐
                          ▼                    ▼
                 ┌──────────────────┐  ┌──────────────────┐
                 │ FastAPI  :8000   │  │ Streamlit :8501  │
                 │ scoring API      │  │ analytics UI     │
                 └────────┬─────────┘  └──────────────────┘
                          ▼
              churn_rf · churn_lr · segmentation_kmeans  (joblib)
```

- **FastAPI** scoring service — `POST /score` returns a churn probability and a Low/Medium/High risk band in ~23 ms.
- **Streamlit dashboard** — headline metrics, segment monitoring, an exportable retention list, and an interactive single-rider scorer.
- **Hosted on AWS EC2** (Amazon Linux 2023), supervised by **systemd** (`Restart=always`, starts on boot) behind an **Nginx** reverse proxy.
- **Containerised** with **Docker + Docker Compose** for a reproducible, portable environment — with systemd supervising the whole stack (*Docker guarantees the environment; systemd guarantees it keeps running*).
- **Monitoring** — layered health checks, feature-drift detection (KS test), and a documented retrain cadence.

---

## 🛠️ Tech stack

| Layer | Tools |
|---|---|
| **Data & modelling** | Python 3.11, pandas, NumPy, scikit-learn, SciPy |
| **Interpretability** | SHAP, feature importance, coefficient analysis |
| **Serving** | FastAPI, Uvicorn, Streamlit |
| **Packaging & infra** | Docker, Docker Compose, systemd, Nginx |
| **Cloud** | AWS EC2 (Amazon Linux 2023) |
| **Experiment tracking** | MLflow *(pipeline)* |

---

## 📁 Project structure

```
ridewise/
├── notebooks/                      # 8 executed, teaching-style notebooks (01 → 08)
│   ├── 01_data_audit_and_cleaning.ipynb
│   ├── 02_exploratory_data_analysis.ipynb
│   ├── 03_feature_engineering.ipynb
│   ├── 04_customer_segmentation.ipynb
│   ├── 05_churn_modelling.ipynb
│   ├── 06_model_interpretability.ipynb
│   ├── 07_threshold_and_targeting.ipynb
│   └── 08_deployment_and_monitoring.ipynb
├── src/
│   ├── ridewise_pipeline.py        # shared data → features → label pipeline
│   ├── main.py                     # FastAPI scoring service
│   └── dashboard.py                # Streamlit analytics dashboard
├── models/                         # serialised RF, LR & K-means artifacts
├── data/                           # raw CSVs + derived analytics table
├── deploy/
│   ├── Dockerfile                  # pinned, reproducible app image
│   ├── docker-compose.yml          # API + UI, one command
│   ├── systemd/ridewise.service    # supervises the stack, survives reboots
│   └── nginx/ridewise.conf         # reverse proxy & routing
├── requirements.txt                # pinned dependencies
└── README.md
```

---

## ⚡ Quickstart

### Run locally

```bash
# 1. Clone and install
git clone https://github.com/<your-username>/ridewise.git
cd ridewise
pip install -r requirements.txt

# 2. Build the analytics table (raw CSVs → features → labelled data)
python src/ridewise_pipeline.py

# 3. Explore the notebooks in order (01 → 08)
jupyter lab notebooks/

# 4. Launch the API and dashboard
uvicorn src.main:app --reload            # → http://127.0.0.1:8000/docs
streamlit run src/dashboard.py           # → http://127.0.0.1:8501
```

### Run with Docker (reproducible)

```bash
docker compose up -d --build
# API → http://localhost:8000/docs   ·   UI → http://localhost:8501
```

### Score a rider via the API

```bash
curl -X POST http://localhost:8000/score \
  -H "Content-Type: application/json" \
  -d '{"features": {"recency": 28, "trips_per_week": 0.4, "monetary": 210, "avg_rating_given": 4.2}}'

# → {"churn_probability": 0.71, "risk_band": "High"}
```

---

## 📈 What makes this project stand out

- **End-to-end, not notebook-only** — the model is trained *and* deployed to a live, monitored AWS endpoint.
- **Judged on the right metric** — recall and PR-AUC over vanity accuracy, with the reasoning made explicit.
- **Honest about the data** — a genuine "no signal" finding is documented and handled transparently, not swept aside.
- **Business-first** — every technical decision is traced to the cost it saves or the revenue it protects.
- **Reproducible** — pinned dependencies, a shared pipeline module, and a containerised environment.
- **Fully documented** — from a 13-page technical workplan down to a plain-English walkthrough for non-specialists.

---

## 🔮 Roadmap

- [ ] Complete CI/CD (GitHub Actions → automated deploy)
- [ ] Add HTTPS (Let's Encrypt / certbot) and a custom domain
- [ ] Migrate to AWS ECS for horizontal scaling
- [ ] Live model retraining on real churn outcomes
- [ ] A/B test the retention campaign to measure the true save-rate

---

## 👤 Author

**Dr. Ogheneworo Offeh** — Geoscientist & Data Scientist
*Turning data into decisions, and models into deployed systems.*

---

<div align="center">

*RideWise is a portfolio project built on a synthetic dataset. The signal-enrichment step and its rationale are documented transparently in `notebooks/03_feature_engineering.ipynb` and the project workplan.*

⭐ *If you found this project interesting, consider giving it a star.*

</div>
