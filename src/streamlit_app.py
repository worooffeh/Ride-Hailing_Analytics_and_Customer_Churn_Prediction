from __future__ import annotations

import time

import streamlit as st

try:
    from src.main import (
        DEFAULT_SEGMENT_NAMES,
        _score_row,
        _segment_row,
        load_churn_bundle,
        load_feature_names,
        load_seg_bundle,
        load_segmentation_feature_names,
    )
except ImportError:
    from main import (
        DEFAULT_SEGMENT_NAMES,
        _score_row,
        _segment_row,
        load_churn_bundle,
        load_feature_names,
        load_seg_bundle,
        load_segmentation_feature_names,
    )


FEATURE_SECTIONS = {
    "Rider value": ["recency", "frequency", "monetary", "avg_fare", "tenure"],
    "Trip behavior": [
        "avg_surge",
        "max_surge",
        "tip_rate",
        "trips_per_week",
        "avg_duration",
        "distinct_drivers",
    ],
    "Usage mix": ["weekend_ratio", "night_ratio", "card_ratio"],
    "App engagement": [
        "sessions_count",
        "avg_time_on_app",
        "avg_pages",
        "conversion_rate",
    ],
    "Profile": ["age", "avg_rating_given", "loyalty_rank", "was_referred"],
}

FEATURE_SPECS = {
    "recency": {"label": "Recency (days since last trip)", "value": 21.0, "minimum": 0.0, "maximum": 365.0, "step": 1.0},
    "frequency": {"label": "Lifetime trip count", "value": 36.0, "minimum": 0.0, "maximum": 1000.0, "step": 1.0},
    "monetary": {"label": "Lifetime spend", "value": 540.0, "minimum": 0.0, "maximum": 20000.0, "step": 10.0},
    "avg_fare": {"label": "Average fare", "value": 15.0, "minimum": 0.0, "maximum": 250.0, "step": 0.5},
    "tenure": {"label": "Tenure (days)", "value": 240.0, "minimum": 0.0, "maximum": 3650.0, "step": 1.0},
    "avg_surge": {"label": "Average surge multiplier", "value": 1.15, "minimum": 1.0, "maximum": 5.0, "step": 0.01},
    "max_surge": {"label": "Maximum surge multiplier", "value": 1.8, "minimum": 1.0, "maximum": 8.0, "step": 0.1},
    "tip_rate": {"label": "Tip rate", "value": 0.08, "minimum": 0.0, "maximum": 1.0, "step": 0.01},
    "trips_per_week": {"label": "Trips per week", "value": 2.4, "minimum": 0.0, "maximum": 50.0, "step": 0.1},
    "avg_duration": {"label": "Average trip duration (minutes)", "value": 18.0, "minimum": 0.0, "maximum": 180.0, "step": 1.0},
    "distinct_drivers": {"label": "Distinct drivers", "value": 18.0, "minimum": 0.0, "maximum": 500.0, "step": 1.0},
    "weekend_ratio": {"label": "Weekend trip ratio", "value": 0.32, "minimum": 0.0, "maximum": 1.0, "step": 0.01},
    "night_ratio": {"label": "Night trip ratio", "value": 0.18, "minimum": 0.0, "maximum": 1.0, "step": 0.01},
    "card_ratio": {"label": "Card payment ratio", "value": 0.84, "minimum": 0.0, "maximum": 1.0, "step": 0.01},
    "sessions_count": {"label": "Sessions count", "value": 14.0, "minimum": 0.0, "maximum": 500.0, "step": 1.0},
    "avg_time_on_app": {"label": "Average time on app (minutes)", "value": 9.5, "minimum": 0.0, "maximum": 180.0, "step": 0.5},
    "avg_pages": {"label": "Average pages per session", "value": 6.0, "minimum": 0.0, "maximum": 100.0, "step": 0.5},
    "conversion_rate": {"label": "Session conversion rate", "value": 0.42, "minimum": 0.0, "maximum": 1.0, "step": 0.01},
    "age": {"label": "Rider age", "value": 34.0, "minimum": 18.0, "maximum": 100.0, "step": 1.0},
    "avg_rating_given": {"label": "Average rating given", "value": 4.6, "minimum": 1.0, "maximum": 5.0, "step": 0.1},
    "loyalty_rank": {"label": "Loyalty rank", "value": 3, "choices": [1, 2, 3, 4, 5]},
    "was_referred": {"label": "Referred rider", "value": True},
}


def _render_feature_fields(feature_names: list[str], key_prefix: str) -> dict[str, float]:
    columns = st.columns(2)
    values: dict[str, float] = {}
    for index, feature_name in enumerate(feature_names):
        spec = FEATURE_SPECS[feature_name]
        with columns[index % 2]:
            if feature_name == "was_referred":
                raw_value = st.checkbox(spec["label"], value=spec["value"], key=f"{key_prefix}_{feature_name}")
            elif feature_name == "loyalty_rank":
                raw_value = st.selectbox(
                    spec["label"],
                    options=spec["choices"],
                    index=spec["choices"].index(spec["value"]),
                    key=f"{key_prefix}_{feature_name}",
                )
            else:
                raw_value = st.number_input(
                    spec["label"],
                    min_value=spec["minimum"],
                    max_value=spec["maximum"],
                    value=spec["value"],
                    step=spec["step"],
                    key=f"{key_prefix}_{feature_name}",
                )
            values[feature_name] = float(raw_value)
    return values


def _risk_summary(probability: float, risk_band: str) -> str:
    if risk_band == "High":
        guidance = "Immediate retention action recommended. Trigger an incentive or outreach workflow."
    elif risk_band == "Medium":
        guidance = "Monitor closely. A targeted nudge or promotion is likely worthwhile."
    else:
        guidance = "Healthy rider profile. Continue standard engagement and loyalty treatment."
    return (
        f"**Churn outlook:** {risk_band} risk\n\n"
        f"**Churn probability:** {probability:.1%}\n\n"
        f"{guidance}"
    )


def _segment_summary(segment: int, segment_name: str | None) -> str:
    label = segment_name or DEFAULT_SEGMENT_NAMES.get(segment, f"Segment {segment}")
    guidance = {
        0: "These riders are cooling on recency and value. Re-engagement offers fit this group.",
        1: "This is the weakest value segment. Use lightweight win-back or low-cost nudges before spending heavily.",
        2: "These riders show the strongest frequency and spend signals. Prioritize loyalty, premium perks, and upsell paths.",
        3: "These riders are recently active with steady baseline value. Keep engagement consistent and protect habit formation.",
    }.get(segment, "Review the segment alongside churn probability for the best intervention choice.")
    return f"**Segment assignment:** {label}\n\n**Cluster ID:** {segment}\n\n{guidance}"


def render_churn_tab() -> None:
    st.subheader("Churn scoring")
    st.caption("Score a rider with the same saved feature schema used by the churn model.")

    with st.form("churn_form"):
        features = _render_feature_fields(load_feature_names(), "churn")
        submitted = st.form_submit_button("Score rider", use_container_width=True)

    if not submitted:
        return

    result = _score_row(load_churn_bundle(), features, time.perf_counter())
    col1, col2, col3 = st.columns(3)
    col1.metric("Churn probability", f"{result.churn_probability:.1%}")
    col2.metric("Risk band", result.risk_band)
    col3.metric("Model", result.model_name)
    st.markdown(_risk_summary(result.churn_probability, result.risk_band))
    st.json({
        "retained_probability": round(1 - result.churn_probability, 4),
        "churn_probability": result.churn_probability,
        "raw": result.model_dump() | {"features": features},
    })


def render_segmentation_tab() -> None:
    st.subheader("Segmentation")
    st.caption("Assign a rider to the saved behavioral cluster model.")

    with st.form("segmentation_form"):
        features = _render_feature_fields(load_segmentation_feature_names(), "segment")
        submitted = st.form_submit_button("Assign segment", use_container_width=True)

    if not submitted:
        return

    result = _segment_row(load_seg_bundle(), features, time.perf_counter())
    col1, col2, col3 = st.columns(3)
    col1.metric("Segment", result.segment_name or f"Segment {result.segment}")
    col2.metric("Cluster ID", str(result.segment))
    col3.metric("Model", result.model_name)
    st.markdown(_segment_summary(result.segment, result.segment_name))
    st.json(result.model_dump() | {"features": features})


def render_profile_tab() -> None:
    st.subheader("Rider profile")
    st.caption("See churn and segmentation outputs from one shared rider profile.")

    with st.form("profile_form"):
        features = _render_feature_fields(load_feature_names(), "profile")
        submitted = st.form_submit_button("Analyze rider", use_container_width=True)

    if not submitted:
        return

    churn_result = _score_row(load_churn_bundle(), features, time.perf_counter())
    segmentation_features = {
        name: features[name]
        for name in load_segmentation_feature_names()
    }
    segment_result = _segment_row(load_seg_bundle(), segmentation_features, time.perf_counter())
    left, right = st.columns(2)
    with left:
        st.metric("Churn probability", f"{churn_result.churn_probability:.1%}")
        st.metric("Risk band", churn_result.risk_band)
        st.markdown(_risk_summary(churn_result.churn_probability, churn_result.risk_band))
    with right:
        st.metric("Segment", segment_result.segment_name or f"Segment {segment_result.segment}")
        st.metric("Cluster ID", str(segment_result.segment))
        st.markdown(_segment_summary(segment_result.segment, segment_result.segment_name))

    st.json(
        {
            "churn": churn_result.model_dump(),
            "segment": segment_result.model_dump(),
            "features": features,
        }
    )


def main() -> None:
    st.set_page_config(page_title="RideWise Rider Intelligence", layout="wide")
    st.title("RideWise Rider Intelligence")
    st.caption("Streamlit frontend for churn scoring and rider segmentation.")

    churn_tab, segment_tab, profile_tab = st.tabs(
        ["Churn scoring", "Segmentation", "Rider profile"]
    )
    with churn_tab:
        render_churn_tab()
    with segment_tab:
        render_segmentation_tab()
    with profile_tab:
        render_profile_tab()


main()