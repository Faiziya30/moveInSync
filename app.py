from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from src.analysis import count_by_confidence, count_by_theme, filtered_csv_bytes, monthly_counts
from src.data_loader import filter_evidence, load_evidence_csv, summarize_evidence
from src.recommendations import get_recommendations

st.set_page_config(page_title="Commute Insights", page_icon="CI", layout="wide")

DATA_PATH = Path(__file__).parent / "data" / "review_evidence.csv"

st.markdown(
    """
    <style>
    .block-container { max-width: 1380px; padding-top: 2rem; padding-bottom: 3rem; }
    [data-testid="stMetric"] {
        background: #f7f9fc;
        border: 1px solid #e3e8ef;
        border-radius: 10px;
        padding: 0.85rem 1rem;
    }
    [data-testid="stMetricLabel"] { color: #526173; }
    .section-kicker {
        color: #4169a1;
        font-size: 0.76rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin-bottom: 0.25rem;
    }
    .evidence-note {
        background: #f3f7fb;
        border-left: 4px solid #4169a1;
        border-radius: 4px;
        padding: 0.9rem 1rem;
        color: #30435b;
        margin: 0.75rem 0 1.5rem;
    }
    .detail-card {
        background: #fbfcfe;
        border: 1px solid #e3e8ef;
        border-radius: 10px;
        padding: 1rem 1.1rem;
        margin-top: 0.75rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def load_data(path: Path):
    return load_evidence_csv(path)


st.title("Commute Insights")
st.caption("Employee commute review intelligence for a MoveInSync FDE case study")
st.markdown(
    """
    <div class="evidence-note">
    <strong>Evidence quality notice.</strong> This dashboard analyses a small, curated sample of public
    review signals. Counts describe only the loaded sample; they do not estimate how widespread a problem
    is among MoveInSync users or establish technical causality.
    </div>
    """,
    unsafe_allow_html=True,
)

try:
    evidence_df = load_data(DATA_PATH)
except Exception as exc:
    st.error(f"Could not load the evidence CSV: {exc}")
    st.stop()

if evidence_df.empty:
    st.warning("No evidence rows are available yet. Add records to the evidence CSV.")
    st.stop()

with st.sidebar:
    st.header("Explore evidence")
    st.caption("Filters apply to the table, details, charts, and current-view metric.")
    search_text = st.text_input(
        "Search",
        placeholder="Evidence ID, theme, or reported summary",
        help="Searches evidence IDs, themes, and reported signal summaries.",
    )

    themes = sorted(evidence_df["theme"].dropna().astype(str).unique().tolist())
    selected_themes = st.multiselect("Theme", themes, default=themes)
    confidences = sorted(evidence_df["theme_coding_confidence"].dropna().astype(str).unique().tolist())
    selected_confidences = st.multiselect("Theme classification confidence", confidences, default=confidences)
    statuses = sorted(evidence_df["validation_status"].dropna().astype(str).unique().tolist())
    selected_statuses = st.multiselect("Source / validation status", statuses, default=statuses)

    if evidence_df["date_shown"].notna().any():
        min_date = evidence_df["date_shown"].min().date()
        max_date = evidence_df["date_shown"].max().date()
        date_range = st.slider("Date shown", min_value=min_date, max_value=max_date, value=(min_date, max_date))
        include_undated = st.checkbox("Include records without a date", value=True)
    else:
        date_range = None
        include_undated = True

filtered = filter_evidence(
    evidence_df,
    search_text=search_text,
    themes=selected_themes,
    confidences=selected_confidences,
    statuses=selected_statuses,
)

if date_range is not None:
    start_date, end_date = date_range
    in_range = filtered["date_shown"].notna() & filtered["date_shown"].dt.date.between(start_date, end_date)
    if include_undated:
        in_range = in_range | filtered["date_shown"].isna()
    filtered = filtered[in_range].copy()

current_summary = summarize_evidence(filtered)

st.markdown('<div class="section-kicker">Overview</div>', unsafe_allow_html=True)
st.header("What is in the current evidence view?")
metric_cols = st.columns(4)
metric_cols[0].metric("Evidence rows in view", current_summary["evidence_rows"])
metric_cols[1].metric("Themes in view", current_summary["distinct_themes"])
metric_cols[2].metric("Rows needing verification", current_summary["rows_needing_verification"])
metric_cols[3].metric("Loaded rows", len(evidence_df))
st.caption(
    "Classification confidence describes confidence in the theme label, not confidence that the issue is widespread. "
    "Validation status describes source or issue follow-up separately."
)

st.markdown('<div class="section-kicker">Evidence explorer</div>', unsafe_allow_html=True)
st.header("Review the evidence without losing the context")

if filtered.empty:
    st.warning("No records match the current filters. Broaden the search or filter selections.")
else:
    compact_table = filtered[[
        "evidence_id",
        "date_shown",
        "theme",
        "theme_coding_confidence",
        "validation_status",
    ]].copy()
    compact_table["date_shown"] = compact_table["date_shown"].dt.strftime("%Y-%m-%d").fillna("Not available")
    compact_table = compact_table.rename(
        columns={
            "evidence_id": "Evidence ID",
            "date_shown": "Date shown",
            "theme": "Theme",
            "theme_coding_confidence": "Confidence",
            "validation_status": "Validation status",
        }
    )
    st.dataframe(
        compact_table,
        use_container_width=True,
        hide_index=True,
        height=min(360, 74 + (len(compact_table) * 35)),
        column_config={
            "Evidence ID": st.column_config.TextColumn(width="small"),
            "Date shown": st.column_config.TextColumn(width="small"),
            "Theme": st.column_config.TextColumn(width="medium"),
            "Confidence": st.column_config.TextColumn(width="small"),
            "Validation status": st.column_config.TextColumn(width="medium"),
        },
    )

    selected_id = st.selectbox(
        "Select an evidence record for full details",
        options=filtered["evidence_id"].astype(str).tolist(),
        format_func=lambda evidence_id: f"{evidence_id} — {filtered.loc[filtered['evidence_id'].astype(str).eq(evidence_id), 'theme'].iloc[0]}",
    )
    selected_record = filtered.loc[filtered["evidence_id"].astype(str).eq(selected_id)].iloc[0]
    detail_left, detail_right = st.columns([1.4, 1])
    with detail_left:
        st.markdown(f"#### {selected_record['evidence_id']} · {selected_record['theme']}")
        st.markdown("**Reported signal summary**")
        st.write(selected_record["reported_signal_summary"] or "Not provided.")
        st.markdown("**Interpretation and limitations**")
        st.write(selected_record["limitations"] or "No limitation recorded.")
        st.markdown("**Follow-up data required**")
        st.write(
            "Validate against booking funnel data, trip and location timestamps, notification delivery, "
            "no-show event timelines, support tickets, and employee usability research."
        )
    with detail_right:
        st.markdown('<div class="detail-card">', unsafe_allow_html=True)
        st.markdown("**Evidence metadata**")
        date_shown = selected_record["date_shown"]
        st.write(f"**Date shown:** {date_shown.strftime('%Y-%m-%d') if pd.notna(date_shown) else 'Not available'}")
        st.write(f"**Source locale:** {selected_record['source_locale'] or 'Not provided'}")
        st.write(f"**Theme classification confidence:** {selected_record['theme_coding_confidence'] or 'Not provided'}")
        st.write(f"**Validation status:** {selected_record['validation_status'] or 'Not provided'}")
        st.markdown("**Source URL**")
        if selected_record["source_url"]:
            st.link_button("Open source listing", selected_record["source_url"])
        else:
            st.caption("No valid source URL is available in this record.")
        st.markdown("</div>", unsafe_allow_html=True)

    st.download_button(
        "Download filtered evidence as CSV",
        data=filtered_csv_bytes(filtered),
        file_name="filtered_commute_evidence.csv",
        mime="text/csv",
    )

st.markdown('<div class="section-kicker">Analysis</div>', unsafe_allow_html=True)
st.header("What themes appear in this curated sample?")
if filtered.empty:
    st.info("Charts appear when at least one record matches the selected filters.")
else:
    theme_counts = count_by_theme(filtered)
    confidence_counts = count_by_confidence(filtered)
    chart_left, chart_right = st.columns(2)
    with chart_left:
        fig_theme = px.bar(
            theme_counts,
            x="evidence_rows",
            y="theme",
            orientation="h",
            text="evidence_rows",
            title="Records by theme",
            color_discrete_sequence=["#4169a1"],
        )
        fig_theme.update_layout(
            xaxis_title="Records in curated sample",
            yaxis_title="",
            yaxis_categoryorder="total ascending",
            margin=dict(l=10, r=10, t=55, b=10),
        )
        st.plotly_chart(fig_theme, use_container_width=True)
        st.caption("Counts are records in the current curated sample, not population prevalence.")
    with chart_right:
        fig_confidence = px.bar(
            confidence_counts,
            x="theme_coding_confidence",
            y="evidence_rows",
            text="evidence_rows",
            title="Theme classification confidence",
            color="theme_coding_confidence",
            color_discrete_sequence=["#7b9fc9", "#4169a1", "#243b5a", "#aab7c4"],
        )
        fig_confidence.update_layout(
            xaxis_title="Classification confidence",
            yaxis_title="Records in curated sample",
            showlegend=False,
            margin=dict(l=10, r=10, t=55, b=10),
        )
        st.plotly_chart(fig_confidence, use_container_width=True)
        st.caption("Confidence is about theme coding, not issue frequency or severity.")

    monthly = monthly_counts(filtered)
    if not monthly.empty:
        fig_month = px.line(
            monthly,
            x="calendar_month",
            y="evidence_rows",
            markers=True,
            title="Records by calendar month shown in the curated sample",
        )
        fig_month.update_layout(
            xaxis_title="Calendar month",
            yaxis_title="Records in curated sample",
            margin=dict(l=10, r=10, t=55, b=10),
        )
        st.plotly_chart(fig_month, use_container_width=True)
        st.caption("Only records with an available date are included in this view.")

st.markdown('<div class="section-kicker">Product analysis</div>', unsafe_allow_html=True)
st.header("Evidence-linked recommendations to validate")
st.caption("These are candidate interventions, not implemented MoveInSync features or confirmed root-cause fixes.")

for recommendation in get_recommendations(evidence_df):
    with st.expander(recommendation["title"], expanded=False):
        status_col, evidence_col = st.columns([1, 2])
        with status_col:
            st.write(f"**Validation:** {recommendation['validation_status']}")
            st.write(f"**Classification confidence:** {recommendation['confidence']}")
        with evidence_col:
            st.write(
                f"**Supporting evidence IDs:** "
                f"{', '.join(recommendation['matched_evidence_ids']) or 'No matching records loaded'}"
            )
            if recommendation["pending_evidence_ids"]:
                st.caption(f"Evidence IDs not present in the loaded dataset: {', '.join(recommendation['pending_evidence_ids'])}")
        st.markdown(f"**Hypothesis:** {recommendation['problem_hypothesis']}")
        st.markdown(f"**Proposed intervention:** {recommendation['proposed_intervention']}")
        st.markdown("**Success metrics:**")
        st.markdown("\n".join(f"- {metric}" for metric in recommendation["success_metrics"]))
        st.markdown(f"**Risks and guardrails:** {recommendation['risks_and_guardrails']}")

st.markdown('<div class="section-kicker">Method and next steps</div>', unsafe_allow_html=True)
st.header("How to interpret this dashboard")
st.markdown(
    """
- A record is a candidate public review signal, not a confirmed product defect.
- Theme classification confidence and source verification are separate: a theme can be coded clearly even when its source still needs re-checking.
- Localized listings may duplicate or partially overlap with other records; counts should not be read as unique-user counts.
- Reviews can describe symptoms, but they cannot establish whether the cause is app code, GPS, network, backend, vehicle hardware, or operations.
- Next validation inputs include booking funnel data, ETA error, location-update age, notification delivery, no-show timelines, support-ticket themes, and usability testing.
"""
)

st.caption("Independent research prototype. It does not connect to MoveInSync systems or claim a rating increase.")
