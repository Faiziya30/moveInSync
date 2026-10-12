from __future__ import annotations

import tempfile

import pandas as pd

from src.analysis import count_by_confidence, count_by_theme, filtered_csv_bytes
from src.data_loader import filter_evidence, load_evidence_csv
from src.recommendations import get_recommendations


def _sample_data() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "evidence_id": "MIS-001",
                "date_shown": "2026-06-29",
                "source_locale": "English listing",
                "theme": "Check-in / no-show clarity",
                "reported_signal_summary": "Vehicle may arrive late and employee is marked no-show.",
                "theme_coding_confidence": "Medium",
                "limitations": "Does not prove a flaw exists globally.",
                "source_url": "https://example.com/review-1",
                "validation_status": "Needs internal validation",
            },
            {
                "evidence_id": "MIS-002",
                "date_shown": "2026-07-07",
                "source_locale": "English listing",
                "theme": "Booking confirmation / flow clarity",
                "reported_signal_summary": "Changed two-step flow made booking seem unconfirmed.",
                "theme_coding_confidence": "Medium",
                "limitations": "Does not establish frequency.",
                "source_url": "https://example.com/review-2",
                "validation_status": "Needs internal validation",
            },
            {
                "evidence_id": "MIS-003",
                "date_shown": "",
                "source_locale": "English listing",
                "theme": "Assigned-trip / vehicle visibility",
                "reported_signal_summary": "Could not tell the relevant cab from nearby cabs.",
                "theme_coding_confidence": "Low",
                "limitations": "May be a UX issue rather than a data issue.",
                "source_url": "",
                "validation_status": "Needs clarification",
            },
            {
                "evidence_id": "MIS-004",
                "date_shown": "2026-07-01",
                "source_locale": "English listing",
                "theme": "GPS / ETA reliability",
                "reported_signal_summary": "Slow GPS and incorrect timings.",
                "theme_coding_confidence": "High",
                "limitations": "Could be app, GPS or operations.",
                "source_url": "https://example.com/review-4",
                "validation_status": "Needs internal validation",
            },
        ]
    )


def test_load_valid_evidence_csv(tmp_path):
    csv_path = tmp_path / "evidence.csv"
    _sample_data().to_csv(csv_path, index=False)

    df = load_evidence_csv(csv_path)

    assert len(df) == 4
    assert pd.notna(df.at[0, "date_shown"])
    assert df.at[0, "theme"] == "Check-in / no-show clarity"
    assert df.at[2, "source_url"] == ""


def test_missing_required_columns(tmp_path):
    csv_path = tmp_path / "missing_columns.csv"
    pd.DataFrame({"evidence_id": ["MIS-001"]}).to_csv(csv_path, index=False)

    try:
        load_evidence_csv(csv_path)
        assert False, "Expected ValueError for missing required columns"
    except ValueError as exc:
        assert "Missing required columns" in str(exc)


def test_empty_or_malformed_input(tmp_path):
    empty_path = tmp_path / "empty.csv"
    empty_path.write_text("", encoding="utf-8")
    try:
        load_evidence_csv(empty_path)
        assert False, "Expected ValueError for empty file"
    except ValueError as exc:
        assert "empty" in str(exc).lower()

    malformed_path = tmp_path / "bad.csv"
    malformed_path.write_text("evidence_id,date_shown\nMIS-001,not-a-date\n", encoding="utf-8")
    try:
        load_evidence_csv(malformed_path)
        assert False, "Expected validation failure for malformed schema"
    except ValueError:
        pass


def test_filter_by_theme_and_confidence():
    df = _sample_data()
    filtered = filter_evidence(df, themes=["GPS / ETA reliability"], confidences=["High"])

    assert list(filtered["evidence_id"]) == ["MIS-004"]


def test_theme_and_confidence_aggregation():
    df = _sample_data()

    theme_counts = count_by_theme(df)
    confidence_counts = count_by_confidence(df)

    assert theme_counts["evidence_rows"].sum() == len(df)
    assert confidence_counts["evidence_rows"].sum() == len(df)
    assert theme_counts["theme"].str.contains("Check-in / no-show clarity").any()


def test_missing_dates_and_urls_are_handled():
    df = _sample_data()
    with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", encoding="utf-8", delete=False) as handle:
        handle.write(df.to_csv(index=False))
        path = handle.name

    loaded = load_evidence_csv(path)
    assert pd.isna(loaded.at[2, "date_shown"])
    assert loaded.at[2, "source_url"] == ""


def test_filtered_csv_export_only_includes_filtered_rows():
    df = _sample_data()
    filtered = filter_evidence(df, themes=["GPS / ETA reliability"])
    exported = filtered_csv_bytes(filtered)
    text = exported.decode("utf-8")

    assert "MIS-004" in text
    assert "MIS-001" not in text


def test_recommendations_reference_known_ids_or_are_pending():
    df = _sample_data()
    recs = get_recommendations(df)
    for rec in recs:
        for evidence_id in rec["evidence_ids"]:
            assert evidence_id in df["evidence_id"].values or bool(rec["pending_evidence_ids"])

    assert any(rec["evidence_status"] == "Pending verification" for rec in recs)
