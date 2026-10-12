from __future__ import annotations

from pathlib import Path

import plotly.express as px
import streamlit as st

from src.analysis import count_by_confidence, count_by_theme, filtered_csv_bytes, monthly_counts
from src.data_loader import filter_evidence, load_evidence_csv, summarize_evidence
from src.recommendations import get_recommendations

st.set_page_config(page_title="Commute Insights", page_icon="🚌", layout="wide")

DATA_PATH = Path(__file__).parent / "data" / "review_evidence.csv"

st.title("🚌 Commute Insights")
st.caption("Employee commute review intelligence for a MoveInSync FDE case study")
st.info(
    "This dashboard analyses a small curated sample of public review evidence. Counts describe only the current dataset and do not estimate prevalence among all users or establish technical causality."
)


@st.cache_data
def load_data(path: Path):
    return load_evidence_csv(path)


try:
    evidence_df = load_data(DATA_PATH)
except Exception as exc:
    st.error(f"Could not load the evidence CSV: {exc}")
    st.stop()

if evidence_df.empty:
    st.warning("No evidence rows are available yet. Add records to the CSV or validate the dataset path.")
    st.stop()

summary = summarize_evidence(evidence_df)

with st.sidebar:
    st.header("Filter evidence")
    st.caption("Counts below are for the curated sample only.")

    search_text = st.text_input("Search by evidence ID, summary, or theme", placeholder="e.g. MIS-004 or GPS")
    themes = sorted(evidence_df["theme"].dropna().astype(str).unique().tolist())
    selected_themes = st.multiselect("Theme", themes, default=themes)
    confidences = sorted(evidence_df["theme_coding_confidence"].dropna().astype(str).unique().tolist())
    selected_confidences = st.multiselect("Theme coding confidence", confidences, default=confidences)
    statuses = sorted(evidence_df["validation_status"].dropna().astype(str).unique().tolist())
    selected_statuses = st.multiselect("Validation status", statuses, default=statuses)

    if evidence_df["date_shown"].notna().any():
        min_date = evidence_df["date_shown"].min().date()
        max_date = evidence_df["date_shown"].max().date()
        date_range = st.slider("Date range", min_value=min_date, max_value=max_date, value=(min_date, max_date))
    else:
        date_range = None

filtered = filter_evidence(
    evidence_df,
    search_text=search_text,
    themes=selected_themes,
    confidences=selected_confidences,
    statuses=selected_statuses,
)

if date_range is not None:
    start_date, end_date = date_range
    filtered = filtered[
        filtered["date_shown"].notna()
        & filtered["date_shown"].dt.date.between(start_date, end_date)
    ].copy()

st.subheader("Executive overview")
metric_cols = st.columns(4)
metric_cols[0].metric("Evidence rows", summary["evidence_rows"])
metric_cols[1].metric("Distinct themes", summary["distinct_themes"])
metric_cols[2].metric("Rows needing verification", summary["rows_needing_verification"])
metric_cols[3].metric("Rows in current view", len(filtered))

st.caption(
    "Evidence quality notice: the dataset is a targeted desk-research sample, not a complete corpus. Recommendations are hypotheses requiring validation."
)

st.subheader("Evidence explorer")
if filtered.empty:
    st.warning("No records match the current filters. Try broadening the search or theme selections.")
else:
    display_df = filtered[[
        "evidence_id",
        "date_shown",
        "theme",
        "reported_signal_summary",
        "theme_coding_confidence",
        "limitations",
        "validation_status",
        "source_url",
    ]].copy()
    display_df["date_shown"] = display_df["date_shown"].dt.strftime("%Y-%m-%d").fillna("Not available")
    display_df = display_df.rename(
        columns={
            "reported_signal_summary": "Observed statement",
            "limitations": "Interpretation / caveat",
            "validation_status": "Validation status",
            "source_url": "Source URL",
        }
    )

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Source URL": st.column_config.LinkColumn("Source URL", display_text="Open source"),
        },
    )

    csv_bytes = filtered_csv_bytes(filtered)
    st.download_button(
        "Download filtered evidence as CSV",
        data=csv_bytes,
        file_name="filtered_commute_evidence.csv",
        mime="text/csv",
    )

st.subheader("Theme analysis")
if filtered.empty:
    st.info("Theme analysis is hidden until at least one record matches the selected filters.")
else:
    theme_counts = count_by_theme(filtered)
    fig_theme = px.bar(
        theme_counts,
        x="theme",
        y="evidence_rows",
        text="evidence_rows",
        title="Evidence rows by theme in the current sample (not prevalence)",
        color="theme",
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig_theme.update_layout(xaxis_title="", yaxis_title="Evidence rows", xaxis_tickangle=-25, showlegend=False)
    st.plotly_chart(fig_theme, use_container_width=True)

    confidence_counts = count_by_confidence(filtered)
    fig_conf = px.bar(
        confidence_counts,
        x="theme_coding_confidence",
        y="evidence_rows",
        text="evidence_rows",
        title="Confidence distribution in the current sample",
        color="theme_coding_confidence",
        color_discrete_sequence=px.colors.qualitative.Pastel,
    )
    fig_conf.update_layout(xaxis_title="Confidence label", yaxis_title="Evidence rows", showlegend=False)
    st.plotly_chart(fig_conf, use_container_width=True)

    monthly = monthly_counts(filtered)
    if not monthly.empty:
        fig_month = px.line(
            monthly,
            x="month",
            y="evidence_rows",
            title="Evidence rows by month in the curated sample",
        )
        fig_month.update_layout(xaxis_title="Month", yaxis_title="Evidence rows")
        st.plotly_chart(fig_month, use_container_width=True)

st.subheader("Product recommendations")
recommendations = get_recommendations(evidence_df)
for recommendation in recommendations:
    visible_matches = [evidence_id for evidence_id in recommendation["matched_evidence_ids"] if evidence_id in filtered["evidence_id"].astype(str).values]
    st.markdown(f"### {recommendation['title']}")
    st.markdown(f"**Confidence:** {recommendation['confidence']}  |  **Validation:** {recommendation['validation_status']}")
    st.markdown(f"**Supporting evidence IDs:** {', '.join(recommendation['matched_evidence_ids']) if recommendation['matched_evidence_ids'] else 'No evidence in loaded dataset'}")
    if visible_matches:
        st.caption(f"In current view: {', '.join(visible_matches)}")
    st.markdown(f"**Problem hypothesis:** {recommendation['problem_hypothesis']}")
    st.markdown(f"**Proposed intervention:** {recommendation['proposed_intervention']}")
    st.markdown("**Success metrics:**")
    for metric in recommendation["success_metrics"]:
        st.markdown(f"- {metric}")
    st.markdown(f"**Risks and guardrails:** {recommendation['risks_and_guardrails']}")
    st.markdown("---")

st.subheader("Methodology and limitations")
st.markdown(
    """
- Each row is a candidate public review signal, not a confirmed product defect.
- A confidence label describes how confidently the theme was coded in this sample, not whether the issue is widespread.
- Review counts cannot establish prevalence because the dataset is small and curated, and localized listings may duplicate or partially overlap with one another.
- A review alone cannot prove technical causality; internal telemetry, support tickets, and operational records are still required.
- Some entries are summaries or are marked for re-checking because the exact source text or app context could not be independently verified from the workspace.
- Before any product change, a team should validate the issue against booking funnel data, trip telemetry, notification logs, support themes, and employee usability testing.
"""
)

st.subheader("Useful next steps")
st.markdown(
    """
- Review booking funnel data and abandonment points across the employee flow.
- Compare ETA and driver-location timestamps against trip logs and dispatch data.
- Measure the age of location updates and identify when stale data is shown to employees.
- Audit notification delivery, timing, and any exception states tied to missed check-ins or service disruption.
- Map review themes to no-show incidents, support tickets, and operations records to confirm if they are connected.
- Run a small usability test to confirm whether employees can identify their trip and next action without confusion.
"""
)

st.caption("This project uses a defensible, evidence-first workflow and is intended to support validation, not to claim a rating or product fix.")
