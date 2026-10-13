from __future__ import annotations

import pandas as pd


def count_by_theme(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["theme", "evidence_rows"])
    counts = (
        df["theme"].fillna("Unclassified").astype(str).value_counts().rename_axis("theme").reset_index(name="evidence_rows")
    )
    return counts.sort_values("evidence_rows", ascending=False).reset_index(drop=True)


def count_by_confidence(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["theme_coding_confidence", "evidence_rows"])
    counts = (
        df["theme_coding_confidence"]
        .fillna("Unknown")
        .astype(str)
        .value_counts()
        .rename_axis("theme_coding_confidence")
        .reset_index(name="evidence_rows")
    )
    return counts.sort_values("evidence_rows", ascending=False).reset_index(drop=True)


def monthly_counts(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or df["date_shown"].notna().sum() == 0:
        return pd.DataFrame(columns=["calendar_month", "evidence_rows"])
    calendar_months = df.loc[df["date_shown"].notna(), "date_shown"].dt.to_period("M")
    counts = calendar_months.value_counts().sort_index().reset_index()
    counts.columns = ["calendar_month", "evidence_rows"]
    counts["calendar_month"] = counts["calendar_month"].astype(str)
    return counts


def filtered_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")
