from __future__ import annotations

import time
from typing import Any

import gradio as gr
from gradio.themes import Base, Soft

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
    "recency": {"label": "Recency (days since last trip)", "value": 21.0, "minimum": 0, "maximum": 365, "step": 1},
    "frequency": {"label": "Lifetime trip count", "value": 36.0, "minimum": 0, "maximum": 1000, "step": 1},
    "monetary": {"label": "Lifetime spend", "value": 540.0, "minimum": 0, "maximum": 20000, "step": 10},
    "avg_fare": {"label": "Average fare", "value": 15.0, "minimum": 0, "maximum": 250, "step": 0.5},
    "tenure": {"label": "Tenure (days)", "value": 240.0, "minimum": 0, "maximum": 3650, "step": 1},
    "avg_surge": {"label": "Average surge multiplier", "value": 1.15, "minimum": 1, "maximum": 5, "step": 0.01},
    "max_surge": {"label": "Maximum surge multiplier", "value": 1.8, "minimum": 1, "maximum": 8, "step": 0.1},
    "tip_rate": {"label": "Tip rate", "value": 0.08, "minimum": 0, "maximum": 1, "step": 0.01},
    "trips_per_week": {"label": "Trips per week", "value": 2.4, "minimum": 0, "maximum": 50, "step": 0.1},
    "avg_duration": {"label": "Average trip duration (minutes)", "value": 18.0, "minimum": 0, "maximum": 180, "step": 1},
    "distinct_drivers": {"label": "Distinct drivers", "value": 18.0, "minimum": 0, "maximum": 500, "step": 1},
    "weekend_ratio": {"label": "Weekend trip ratio", "value": 0.32, "minimum": 0, "maximum": 1, "step": 0.01},
    "night_ratio": {"label": "Night trip ratio", "value": 0.18, "minimum": 0, "maximum": 1, "step": 0.01},
    "card_ratio": {"label": "Card payment ratio", "value": 0.84, "minimum": 0, "maximum": 1, "step": 0.01},
    "sessions_count": {"label": "Sessions count", "value": 14.0, "minimum": 0, "maximum": 500, "step": 1},
    "avg_time_on_app": {"label": "Average time on app (minutes)", "value": 9.5, "minimum": 0, "maximum": 180, "step": 0.5},
    "avg_pages": {"label": "Average pages per session", "value": 6.0, "minimum": 0, "maximum": 100, "step": 0.5},
    "conversion_rate": {"label": "Session conversion rate", "value": 0.42, "minimum": 0, "maximum": 1, "step": 0.01},
    "age": {"label": "Rider age", "value": 34.0, "minimum": 18, "maximum": 100, "step": 1},
    "avg_rating_given": {"label": "Average rating given", "value": 4.6, "minimum": 1, "maximum": 5, "step": 0.1},
    "loyalty_rank": {"label": "Loyalty rank", "value": 3, "choices": [1, 2, 3, 4, 5]},
    "was_referred": {"label": "Referred rider", "value": True},
}

EXAMPLES = [
    [
        75, 8, 120, 15, 90,
        1.32, 2.4, 0.01, 0.6, 13, 7,
        0.11, 0.43, 0.22,
        3, 3.5, 2.0, 0.08,
        24, 4.1, 1, False,
    ],
    [
        6, 84, 1650, 19, 540,
        1.05, 1.4, 0.14, 4.8, 22, 49,
        0.39, 0.14, 0.93,
        32, 12.0, 7.5, 0.68,
        38, 4.8, 5, True,
    ],
]

SEGMENTATION_EXAMPLES = [
    [75, 8, 120],
    [6, 84, 1650],
]

GRADIO_CSS = """
.gradio-container {
    background: linear-gradient(180deg, #f6f8fb 0%, #eef3f8 100%);
}

.gradio-container h1 {
    letter-spacing: -0.02em;
}

.gradio-container .block {
    border-radius: 16px;
}

.gradio-container button.primary {
    background: #0f766e;
    border: none;
}
"""


def _build_feature_component(feature_name: str):
    spec = FEATURE_SPECS[feature_name]
    if feature_name == "was_referred":
        return gr.Checkbox(label=spec["label"], value=spec["value"])
    if feature_name == "loyalty_rank":
        return gr.Dropdown(
            choices=spec["choices"],
            value=spec["value"],
            label=spec["label"],
        )
    return gr.Number(
        label=spec["label"],
        value=spec["value"],
        minimum=spec["minimum"],
        maximum=spec["maximum"],
        step=spec["step"],
    )


def _risk_summary(probability: float, risk_band: str) -> str:
    if risk_band == "High":
        guidance = "Immediate retention action recommended. Trigger an incentive or outreach workflow."
    elif risk_band == "Medium":
        guidance = "Monitor closely. A targeted nudge or promotion is likely worthwhile."
    else:
        guidance = "Healthy rider profile. Continue standard engagement and loyalty treatment."
    return (
        f"### Churn outlook: {risk_band} risk\n\n"
        f"Churn probability: **{probability:.1%}**\n\n"
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
    return f"### Segment assignment: {label}\n\nCluster ID: **{segment}**\n\n{guidance}"


def _coerce_features(feature_names: list[str], values: tuple) -> dict[str, float]:
    return {
        name: float(raw_value)
        for name, raw_value in zip(feature_names, values, strict=True)
    }


def _resolve_theme(theme_name: str | None) -> Any:
    if theme_name == "accent":
        return Soft(
            primary_hue="teal",
            secondary_hue="cyan",
            neutral_hue="slate",
        )
    if theme_name == "soft":
        return Soft()
    if theme_name == "base":
        return Base()
    return None


def gradio_predict(*values):
    feature_names = load_feature_names()
    features = _coerce_features(feature_names, values)
    result = _score_row(load_churn_bundle(), features, time.perf_counter())
    probability_map = {
        "Retained": round(1 - result.churn_probability, 4),
        "Churn": result.churn_probability,
    }
    raw_response = result.model_dump()
    raw_response["features"] = features

    return (
        _risk_summary(result.churn_probability, result.risk_band),
        probability_map,
        result.churn_probability,
        result.risk_band,
        result.model_name,
        raw_response,
    )


def gradio_segment(*values):
    feature_names = load_segmentation_feature_names()
    features = _coerce_features(feature_names, values)
    result = _segment_row(load_seg_bundle(), features, time.perf_counter())
    raw_response = result.model_dump()
    raw_response["features"] = features
    segment_label = result.segment_name or DEFAULT_SEGMENT_NAMES.get(result.segment, f"Segment {result.segment}")

    return (
        _segment_summary(result.segment, result.segment_name),
        segment_label,
        result.segment,
        result.model_name,
        raw_response,
    )


def gradio_profile(*values):
    feature_names = load_feature_names()
    segmentation_feature_names = load_segmentation_feature_names()
    features = _coerce_features(feature_names, values)
    churn_result = _score_row(load_churn_bundle(), features, time.perf_counter())
    segmentation_features = {
        name: features[name]
        for name in segmentation_feature_names
    }
    segment_result = _segment_row(load_seg_bundle(), segmentation_features, time.perf_counter())
    profile_payload = {
        "churn": churn_result.model_dump(),
        "segment": segment_result.model_dump(),
        "features": features,
    }

    return (
        _risk_summary(churn_result.churn_probability, churn_result.risk_band),
        churn_result.churn_probability,
        churn_result.risk_band,
        segment_result.segment_name or DEFAULT_SEGMENT_NAMES.get(segment_result.segment, f"Segment {segment_result.segment}"),
        _segment_summary(segment_result.segment, segment_result.segment_name),
        profile_payload,
    )


def build_gradio_app(theme: str | None = None) -> gr.Blocks:
    feature_names = load_feature_names()
    segmentation_feature_names = load_segmentation_feature_names()
    churn_components = []
    segmentation_components = []
    profile_components = []
    resolved_theme = _resolve_theme(theme)

    with gr.Blocks(title="RideWise Rider Intelligence") as demo:
        gr.HTML(f"<style>{GRADIO_CSS}</style>")
        gr.Markdown(
            """
            # RideWise Rider Intelligence
            Use the churn tab for supervised risk scoring and the segmentation tab for fast behavioral clustering.
            """
        )

        with gr.Tabs():
            with gr.Tab("Churn scoring"):
                with gr.Row():
                    with gr.Column(scale=3):
                        for section_name, section_features in FEATURE_SECTIONS.items():
                            with gr.Accordion(section_name, open=True):
                                for feature_name in section_features:
                                    if feature_name not in feature_names:
                                        continue
                                    component = _build_feature_component(feature_name)
                                    churn_components.append(component)

                        with gr.Row():
                            score_button = gr.Button("Score rider", variant="primary")
                            gr.ClearButton(churn_components, value="Reset inputs")

                    with gr.Column(scale=2):
                        summary_output = gr.Markdown()
                        distribution_output = gr.Label(label="Outcome probabilities")
                        churn_probability_output = gr.Number(label="Churn probability", precision=4)
                        risk_band_output = gr.Textbox(label="Risk band")
                        model_name_output = gr.Textbox(label="Model")
                        raw_output = gr.JSON(label="Raw prediction payload")

                gr.Examples(
                    examples=EXAMPLES,
                    inputs=churn_components,
                    label="Starter churn scenarios",
                )

                score_button.click(
                    fn=gradio_predict,
                    inputs=churn_components,
                    outputs=[
                        summary_output,
                        distribution_output,
                        churn_probability_output,
                        risk_band_output,
                        model_name_output,
                        raw_output,
                    ],
                )

            with gr.Tab("Segmentation"):
                gr.Markdown(
                    """
                    Cluster a rider into one of the saved behavioral segments using the features expected by the K-Means model.
                    """
                )
                with gr.Row():
                    with gr.Column(scale=3):
                        with gr.Accordion("Segmentation inputs", open=True):
                            for feature_name in segmentation_feature_names:
                                segmentation_components.append(_build_feature_component(feature_name))

                        with gr.Row():
                            segment_button = gr.Button("Assign segment", variant="primary")
                            gr.ClearButton(segmentation_components, value="Reset inputs")

                    with gr.Column(scale=2):
                        segment_summary_output = gr.Markdown()
                        segment_name_output = gr.Textbox(label="Segment label")
                        segment_id_output = gr.Number(label="Segment ID", precision=0)
                        segmentation_model_output = gr.Textbox(label="Model")
                        segment_raw_output = gr.JSON(label="Raw segmentation payload")

                gr.Examples(
                    examples=SEGMENTATION_EXAMPLES,
                    inputs=segmentation_components,
                    label="Starter segmentation scenarios",
                )

                segment_button.click(
                    fn=gradio_segment,
                    inputs=segmentation_components,
                    outputs=[
                        segment_summary_output,
                        segment_name_output,
                        segment_id_output,
                        segmentation_model_output,
                        segment_raw_output,
                    ],
                )

            with gr.Tab("Rider profile"):
                gr.Markdown(
                    """
                    Score churn risk and assign a behavioral segment from one shared rider profile.
                    """
                )
                with gr.Row():
                    with gr.Column(scale=3):
                        for section_name, section_features in FEATURE_SECTIONS.items():
                            with gr.Accordion(section_name, open=True):
                                for feature_name in section_features:
                                    if feature_name not in feature_names:
                                        continue
                                    component = _build_feature_component(feature_name)
                                    profile_components.append(component)

                        with gr.Row():
                            profile_button = gr.Button("Analyze rider", variant="primary")
                            gr.ClearButton(profile_components, value="Reset inputs")

                    with gr.Column(scale=2):
                        profile_churn_summary = gr.Markdown()
                        profile_probability = gr.Number(label="Churn probability", precision=4)
                        profile_risk_band = gr.Textbox(label="Risk band")
                        profile_segment_label = gr.Textbox(label="Segment label")
                        profile_segment_summary = gr.Markdown()
                        profile_raw_output = gr.JSON(label="Combined rider payload")

                gr.Examples(
                    examples=EXAMPLES,
                    inputs=profile_components,
                    label="Starter rider profiles",
                )

                profile_button.click(
                    fn=gradio_profile,
                    inputs=profile_components,
                    outputs=[
                        profile_churn_summary,
                        profile_probability,
                        profile_risk_band,
                        profile_segment_label,
                        profile_segment_summary,
                        profile_raw_output,
                    ],
                )

    return demo


APP_THEME = _resolve_theme("accent")
demo = build_gradio_app()
# give the app an 'accent' theme to match the RideWise brand colors

if __name__ == "__main__":
    demo.launch(share=True, theme=APP_THEME)