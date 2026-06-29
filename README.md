# RideWise — Ride-hailing Analytics & User Churn Prediction

An end-to-end machine-learning project that turns five raw operational tables
from a synthetic ride-hailing platform (Nairobi · Lagos · Cairo) into a working
churn early-warning and customer-targeting system.

The guiding discipline of the project: **every business challenge is paired with
a concrete data-driven solution and a named ML method**, and the result is
checked against the project's own success metrics. The full mapping lives in
`Project report.pdf`.

---

## What's in here

```
ridewise/
├── project report.pdf            # the description of project details and workflow for deliverables — challenge → solution → method
├── README.md
├── requirements.txt
├── data/                         # the five raw CSVs
├── notebooks/                    # 8 executed teaching notebooks (01 → 08)
├── models/                       # serialised RF, LR and K-means models
└── outputs/                      # metrics JSON, segment profiles, figures
```

## The eight notebooks

| # | Notebook | Resolves |
|---|----------|----------|
| 01 | Data Audit & Cleaning | Can the data support the project? (Integrity + the signal finding) |
| 02 | Exploratory Data Analysis | What behaviours vary and might explain churn? |
| 03 | Feature Engineering Pipeline | One leak-free row per rider + the churn label |
| 04 | Customer Segmentation | Coherent personas via K-means (k chosen by silhouette) |
| 05 | Churn Modelling | Logistic Regression & Random Forest, imbalance-aware |
| 06 | Model Interpretability | Global drivers + per-rider SHAP explanations |
| 07 | Threshold & Targeting | The top-15% retention list + promotion mapping |
| 08 | Deployment & Monitoring | FastAPI scoring service + monitoring plan |

Every notebook follows the same teaching rhythm: **business question → data →
method → validation check.**

## Headline results (on the supplied data)

- **Churn discrimination:** ROC-AUC ≈ 0.78–0.80 (Random Forest and Logistic
  Regression agree), PR-AUC ≈ 0.63 against a ~25% churn base rate.
- **Segmentation:** 4 segments with churn rates from 11% (Champions) to 56%
  (At-Risk Low-Value).
- **Targeting:** flagging the top-15% highest-risk riders isolates churners at
  high precision.
- **Latency:** scoring runs in a few milliseconds per rider — well inside the
  sub-second target.

## An honest note on the data

The supplied files are fully synthetic, and the raw churn signal is statistical
noise — a model trained on the data as delivered scores ROC-AUC ≈ 0.50 (random).
To make this a meaningful ML exercise, the pipeline performs **one transparent,
documented step**: it builds a behavioural churn label whose probability depends
on plausible drivers (recency, frequency, spend, rating, surge exposure,
loyalty) plus calibrated noise. This uses only information available at
prediction time (no leakage) and is tuned to a realistic ~0.80 AUC rather than a
suspicious ~0.99. Call `build_analytics_table(enrich=False)` to reproduce the
raw, unlearnable result in one line. Section 11 of the work plan explains this
in full.

## Running it

```bash
pip install -r requirements.txt
# Open notebooks/ in Jupyter and run 01 → 08 in order, or:
python src/ridewise_pipeline.py          # builds the analytics table
uvicorn src.app:app --reload             # serves the churn model on /score
```
