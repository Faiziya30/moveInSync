from __future__ import annotations

from pathlib import Path
from typing import Sequence

import pandas as pd

REQUIRED_COLUMNS: set[str] = {
    "evidence_id",
    "date_shown",
    "source_locale",
    "theme",
    "reported_signal_summary",
    "theme_coding_confidence",
    "limitations",
    "source_url",
    "validation_status",
}


def load_evidence_csv(csv_path: str | Path) -> pd.DataFrame:
    """Load and validate a curated evidence CSV file.

    Returns a cleaned dataframe with the required schema and parsed dates.
    Raises ValueError with a user-facing explanation for missing/invalid data.
    """
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"Evidence file not found: {path}")

    try:
        df = pd.read_csv(path)
    except pd.errors.EmptyDataError as exc:
        raise ValueError("Evidence CSV is empty.") from exc
    except Exception as exc:  # pragma: no cover - wrapper for malformed CSVs
        raise ValueError(f"Malformed CSV input: {exc}") from exc

    if df.empty:
        raise ValueError("Evidence CSV is empty.")

    df = df.copy()
    df.columns = [str(col).strip() for col in df.columns]
    missing = sorted(REQUIRED_COLUMNS - set(df.columns))
    if missing:
        missing_str = ", ".join(missing)
        raise ValueError(f"Missing required columns: {missing_str}")

    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            continue
        df[col] = df[col].where(pd.notna(df[col]), "")
        df[col] = df[col].astype(str).str.strip()

    df["date_shown"] = pd.to_datetime(df["date_shown"], errors="coerce")
    df["source_url"] = df["source_url"].apply(_clean_url)
    df["theme"] = df["theme"].replace({"nan": "", "None": ""})
    df["validation_status"] = df["validation_status"].replace({"nan": "", "None": ""})
    df["theme_coding_confidence"] = df["theme_coding_confidence"].replace({"nan": "", "None": ""})
    df["reported_signal_summary"] = df["reported_signal_summary"].replace({"nan": "", "None": ""})
    df["limitations"] = df["limitations"].replace({"nan": "", "None": ""})

    return df


def _clean_url(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    url = str(value).strip()
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        return ""
    return url


def filter_evidence(
    df: pd.DataFrame,
    *,
    search_text: str = "",
    themes: Sequence[str] | None = None,
    confidences: Sequence[str] | None = None,
    statuses: Sequence[str] | None = None,
) -> pd.DataFrame:
    """Return the evidence rows matching the requested filters."""
    if df.empty:
        return df.copy()

    filtered = df.copy()
    if search_text:
        query = search_text.lower().strip()
        searchable = (
            filtered["evidence_id"].fillna("").astype(str).str.lower()
            + " "
            + filtered["reported_signal_summary"].fillna("").astype(str).str.lower()
            + " "
            + filtered["theme"].fillna("").astype(str).str.lower()
        )
        filtered = filtered[searchable.str.contains(query, case=False, na=False)].copy()

    if themes:
        filtered = filtered[filtered["theme"].isin(themes)].copy()
    if confidences:
        filtered = filtered[filtered["theme_coding_confidence"].isin(confidences)].copy()
    if statuses:
        filtered = filtered[filtered["validation_status"].isin(statuses)].copy()

    return filtered.reset_index(drop=True)


def summarize_evidence(df: pd.DataFrame) -> dict[str, int]:
    """Return summary metrics for the currently loaded evidence sample."""
    if df.empty:
        return {
            "evidence_rows": 0,
            "distinct_themes": 0,
            "rows_needing_verification": 0,
        }

    verification_mask = df["validation_status"].fillna("").astype(str).str.contains(
        "re-check|needs|clarification|pending|verify|internal validation",
        case=False,
        na=False,
    )

    return {
        "evidence_rows": int(len(df)),
        "distinct_themes": int(df["theme"].nunique(dropna=False)),
        "rows_needing_verification": int(verification_mask.sum()),
    }
