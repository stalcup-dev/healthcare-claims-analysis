from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


@dataclass(frozen=True)
class ColumnSpec:
    billed_amount: str = "Billed Amount"
    date_of_service: str = "Date of Service"
    patient_id_candidates: tuple[str, ...] = ("Patient ID", "patient_id", "member_id")
    diagnosis_candidates: tuple[str, ...] = ("Diagnosis Code", "ICD-10 Code", "ICD10", "icd10")


def _first_existing(df: pd.DataFrame, candidates: tuple[str, ...]) -> str | None:
    for c in candidates:
        if c in df.columns:
            return c
    return None


def ensure_parsed_dates(df: pd.DataFrame, date_col: str) -> pd.Series:
    if date_col not in df.columns:
        return pd.Series([pd.NaT] * len(df))
    if pd.api.types.is_datetime64_any_dtype(df[date_col]):
        return df[date_col]
    return pd.to_datetime(df[date_col], errors="coerce")


def compute_kpis_summary(df: pd.DataFrame, *, spec: ColumnSpec | None = None) -> pd.DataFrame:
    s = spec or ColumnSpec()

    billed = pd.to_numeric(df.get(s.billed_amount), errors="coerce")
    total_cost = float(billed.sum()) if billed is not None else 0.0

    patient_col = _first_existing(df, s.patient_id_candidates)
    diagnosis_col = _first_existing(df, s.diagnosis_candidates)

    out: dict[str, object] = {
        "row_count": int(df.shape[0]),
        "column_count": int(df.shape[1]),
        "total_billed_amount": round(total_cost, 2),
    }

    if billed is not None and billed.dropna().shape[0] > 0:
        out.update(
            {
                "avg_claim_amount": round(float(billed.mean()), 2),
                "median_claim_amount": round(float(billed.median()), 2),
                "p95_claim_amount": round(float(billed.quantile(0.95)), 2),
                "min_claim_amount": round(float(billed.min()), 2),
                "max_claim_amount": round(float(billed.max()), 2),
            }
        )

    if patient_col:
        out["unique_patients"] = int(df[patient_col].nunique(dropna=True))

    if diagnosis_col:
        out["unique_diagnoses"] = int(df[diagnosis_col].nunique(dropna=True))
        if total_cost > 0:
            diag_cost = df.groupby(diagnosis_col)[s.billed_amount].sum().sort_values(ascending=False)
            top_code = str(diag_cost.index[0])
            top_total = float(diag_cost.iloc[0])
            out.update(
                {
                    "top_diagnosis_code": top_code,
                    "top_diagnosis_total_billed": round(top_total, 2),
                    "top_diagnosis_pct_of_total": round(100.0 * top_total / total_cost, 2),
                }
            )

    # Date range + member-months (if date + patient exist)
    if s.date_of_service in df.columns:
        parsed = ensure_parsed_dates(df, s.date_of_service)
        dmin = parsed.min()
        dmax = parsed.max()
        out["date_min"] = "" if pd.isna(dmin) else str(dmin.date())
        out["date_max"] = "" if pd.isna(dmax) else str(dmax.date())

        if patient_col and parsed.notna().sum() > 0:
            month = parsed.dt.to_period("M")
            member_months = int(pd.DataFrame({"member": df[patient_col], "month": month}).dropna().drop_duplicates().shape[0])
            out["member_months"] = member_months
            out["pmpm_billed"] = round((total_cost / member_months), 4) if member_months > 0 else ""

    return pd.DataFrame([out])


def compute_cost_concentration(df: pd.DataFrame, *, spec: ColumnSpec | None = None) -> pd.DataFrame:
    s = spec or ColumnSpec()
    patient_col = _first_existing(df, s.patient_id_candidates)
    if not patient_col:
        return pd.DataFrame(
            [{"note": "No patient/member id column available; cost concentration not computed."}]
        )

    totals = df.groupby(patient_col)[s.billed_amount].sum().sort_values(ascending=False)
    n = int(totals.shape[0])
    grand_total = float(totals.sum())
    if n == 0 or grand_total <= 0:
        return pd.DataFrame(
            [{"note": "No patient totals available or total cost is 0; cost concentration not computed."}]
        )

    rows = []
    for pct in (0.01, 0.05, 0.10):
        k = max(1, int(ceil(n * pct)))
        share = float(totals.iloc[:k].sum()) / grand_total
        rows.append(
            {
                "top_pct_patients": int(round(pct * 100)),
                "patient_count": k,
                "total_patients": n,
                "cost_share_pct": round(share * 100.0, 2),
            }
        )

    return pd.DataFrame(rows)


def compute_patient_anomalies(df: pd.DataFrame, *, spec: ColumnSpec | None = None, z_threshold: float = 3.0) -> pd.DataFrame:
    s = spec or ColumnSpec()
    patient_col = _first_existing(df, s.patient_id_candidates)
    if not patient_col:
        return pd.DataFrame(columns=["patient_id", "total_billed", "z_score"])  # empty

    totals = df.groupby(patient_col)[s.billed_amount].sum().sort_values(ascending=False)
    if totals.empty:
        return pd.DataFrame(columns=["patient_id", "total_billed", "z_score"])  # empty

    mean = float(totals.mean())
    std = float(totals.std(ddof=0))
    if std == 0:
        return pd.DataFrame(columns=["patient_id", "total_billed", "z_score"])  # uniform

    z = (totals - mean) / std
    flagged = pd.DataFrame(
        {
            "patient_id": z.index.astype(str),
            "total_billed": totals.values.astype(float),
            "z_score": z.values.astype(float),
        }
    )
    flagged = flagged[flagged["z_score"] >= z_threshold].sort_values("z_score", ascending=False)
    return flagged.reset_index(drop=True)


def save_top_dx_figure(df: pd.DataFrame, *, out_path: Path, spec: ColumnSpec | None = None, top_n: int = 10) -> bool:
    s = spec or ColumnSpec()
    dx_col = _first_existing(df, s.diagnosis_candidates)
    if not dx_col or s.billed_amount not in df.columns:
        return False

    diag = df.groupby(dx_col)[s.billed_amount].sum().sort_values(ascending=False).head(top_n)
    if diag.empty:
        return False

    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(10, 5))
    diag.plot(kind="bar")
    plt.title(f"Top {top_n} Diagnoses by Total Billed Amount")
    plt.xlabel("Diagnosis Code")
    plt.ylabel("Total Billed Amount ($)")
    plt.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_path, dpi=140, bbox_inches="tight")
    plt.close()
    return True


def save_monthly_trend_figure(df: pd.DataFrame, *, out_path: Path, spec: ColumnSpec | None = None, rolling_months: int = 3) -> bool:
    s = spec or ColumnSpec()
    if s.date_of_service not in df.columns or s.billed_amount not in df.columns:
        return False

    parsed = ensure_parsed_dates(df, s.date_of_service)
    if parsed.notna().sum() == 0:
        return False

    tmp = df.copy()
    tmp["__month"] = parsed.dt.to_period("M").astype(str)
    monthly = tmp.groupby("__month")[s.billed_amount].sum()
    if monthly.empty:
        return False

    roll = monthly.rolling(rolling_months, min_periods=1).mean()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(12, 5))
    plt.plot(monthly.index, monthly.values, marker="o", linewidth=2, label="Monthly total")
    plt.plot(roll.index, roll.values, linewidth=2, label=f"{rolling_months}-month rolling avg")
    plt.title("Monthly Billed Amounts")
    plt.xlabel("Month")
    plt.ylabel("Total Billed Amount ($)")
    plt.grid(alpha=0.3)
    plt.xticks(rotation=45, ha="right")
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_path, dpi=140, bbox_inches="tight")
    plt.close()
    return True


def save_pareto_figure(df: pd.DataFrame, *, out_path: Path, spec: ColumnSpec | None = None) -> bool:
    s = spec or ColumnSpec()
    patient_col = _first_existing(df, s.patient_id_candidates)
    if not patient_col or s.billed_amount not in df.columns:
        return False

    totals = df.groupby(patient_col)[s.billed_amount].sum().sort_values(ascending=False)
    if totals.empty:
        return False

    cum_patients = np.arange(1, len(totals) + 1) / len(totals)
    cum_cost = totals.cumsum() / totals.sum()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(7, 5))
    plt.plot(cum_patients * 100.0, cum_cost * 100.0, linewidth=2)
    plt.title("Cost Concentration (Pareto)")
    plt.xlabel("Cumulative % of patients")
    plt.ylabel("Cumulative % of billed amount")
    plt.grid(alpha=0.3)

    for pct in (1, 5, 10):
        plt.axvline(pct, color="gray", linestyle="--", linewidth=1)

    plt.tight_layout()
    plt.savefig(out_path, dpi=140, bbox_inches="tight")
    plt.close()
    return True
