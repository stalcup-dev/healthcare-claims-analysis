from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from src.claims.quality import DataQualityError, run_integrity_checks
from src.claims.metrics import (
    compute_cost_concentration,
    compute_kpis_summary,
    compute_patient_anomalies,
    save_monthly_trend_figure,
    save_pareto_figure,
    save_top_dx_figure,
)


def _pick_input_path(project_root: Path, input_arg: str | None) -> Path:
    if input_arg:
        p = Path(input_arg)
        return p if p.is_absolute() else (project_root / p)

    preferred = ["claim_data.csv", "MedicalClaimsSynthetic1M.csv"]
    for name in preferred:
        candidate = project_root / name
        if candidate.exists():
            return candidate

    raise FileNotFoundError(
        "No input CSV found. Expected claim_data.csv or MedicalClaimsSynthetic1M.csv in the project root. "
        "You can also pass --input PATH."
    )


def _first_existing(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for c in candidates:
        if c in df.columns:
            return c
    return None


def load_dataset(input_csv: Path) -> pd.DataFrame:
    return pd.read_csv(input_csv)


def clean_dataset(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    if "Date of Service" in out.columns:
        out["Date of Service"] = pd.to_datetime(out["Date of Service"], errors="coerce")

    # Coerce amounts to numeric
    for col in [c for c in out.columns if "amount" in c.lower()]:
        out[col] = pd.to_numeric(out[col], errors="coerce")

    # Minimal cleaning: drop rows missing critical fields
    critical = [c for c in ["Billed Amount"] if c in out.columns]
    if critical:
        out = out.dropna(subset=critical)
        out = out[out["Billed Amount"] > 0]

    return out


def compute_kpis(df: pd.DataFrame) -> pd.DataFrame:
    billed = pd.to_numeric(df.get("Billed Amount"), errors="coerce")

    patient_col = _first_existing(df, ["Patient ID", "patient_id"]) 
    diagnosis_col = _first_existing(df, ["Diagnosis Code", "ICD-10 Code", "ICD10", "icd10"]) 
    date_col = _first_existing(df, ["Date of Service", "date_of_service"]) 

    total_cost = float(billed.sum()) if billed is not None else 0.0

    kpis: list[tuple[str, str]] = [
        ("row_count", str(int(df.shape[0]))),
        ("column_count", str(int(df.shape[1]))),
        ("total_billed_amount", f"{total_cost:.2f}"),
    ]

    if billed is not None and billed.dropna().shape[0] > 0:
        kpis.extend(
            [
                ("avg_claim_amount", f"{float(billed.mean()):.2f}"),
                ("median_claim_amount", f"{float(billed.median()):.2f}"),
                ("p95_claim_amount", f"{float(billed.quantile(0.95)):.2f}"),
            ]
        )

    if patient_col:
        kpis.append(("unique_patients", str(int(df[patient_col].nunique(dropna=True)))))

    if diagnosis_col:
        kpis.append(("unique_diagnoses", str(int(df[diagnosis_col].nunique(dropna=True)))))
        if total_cost > 0:
            diag_summary = (
                df.groupby(diagnosis_col)["Billed Amount"].sum().sort_values(ascending=False)
            )
            top_code = str(diag_summary.index[0])
            top_total = float(diag_summary.iloc[0])
            top_pct = 100.0 * top_total / total_cost
            kpis.extend(
                [
                    ("top_diagnosis_code", top_code),
                    ("top_diagnosis_total_billed", f"{top_total:.2f}"),
                    ("top_diagnosis_pct_of_total", f"{top_pct:.2f}"),
                ]
            )

    if date_col and pd.api.types.is_datetime64_any_dtype(df[date_col]):
        dmin = df[date_col].min()
        dmax = df[date_col].max()
        kpis.extend(
            [
                ("date_min", "" if pd.isna(dmin) else str(dmin.date())),
                ("date_max", "" if pd.isna(dmax) else str(dmax.date())),
            ]
        )

    return pd.DataFrame(kpis, columns=["metric", "value"])


def _write_kpis_outputs(df_clean: pd.DataFrame, *, tables_dir: Path) -> tuple[Path, Path]:
    tables_dir.mkdir(parents=True, exist_ok=True)

    # Long-format KPIs (kept for compatibility)
    kpis_long_csv = tables_dir / "kpis.csv"
    compute_kpis(df_clean).to_csv(kpis_long_csv, index=False)

    # Required deliverable: wide, one-row KPI summary
    kpis_summary_csv = tables_dir / "kpis_summary.csv"
    compute_kpis_summary(df_clean).to_csv(kpis_summary_csv, index=False)

    return kpis_long_csv, kpis_summary_csv


def _write_claims_analyses(
    df_clean: pd.DataFrame,
    *,
    outputs_dir: Path,
) -> dict[str, object]:
    tables_dir = outputs_dir / "tables"
    figures_dir = outputs_dir / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    cost_concentration_csv = tables_dir / "cost_concentration.csv"
    cost_conc = compute_cost_concentration(df_clean)
    cost_conc.to_csv(cost_concentration_csv, index=False)

    anomalies_csv = tables_dir / "patient_anomalies.csv"
    anomalies = compute_patient_anomalies(df_clean)
    anomalies.to_csv(anomalies_csv, index=False)

    # Required-ish figure names (consistent, deterministic)
    top_dx_png = figures_dir / "top_dx.png"
    monthly_trend_png = figures_dir / "monthly_trend.png"
    pareto_png = figures_dir / "pareto.png"

    have_top_dx = save_top_dx_figure(df_clean, out_path=top_dx_png)
    have_monthly = save_monthly_trend_figure(df_clean, out_path=monthly_trend_png)
    have_pareto = save_pareto_figure(df_clean, out_path=pareto_png)

    return {
        "cost_concentration_csv": cost_concentration_csv,
        "anomalies_csv": anomalies_csv,
        "figures": [p for p, ok in [(top_dx_png, have_top_dx), (monthly_trend_png, have_monthly), (pareto_png, have_pareto)] if ok],
        "anomaly_count": int(anomalies.shape[0]),
    }


def save_figures(df: pd.DataFrame, *, figures_dir: Path) -> list[Path]:
    figures_dir.mkdir(parents=True, exist_ok=True)

    saved: list[Path] = []

    billed = pd.to_numeric(df.get("Billed Amount"), errors="coerce")
    diagnosis_col = _first_existing(df, ["Diagnosis Code", "ICD-10 Code", "ICD10", "icd10"]) 
    date_col = _first_existing(df, ["Date of Service", "date_of_service"]) 
    patient_col = _first_existing(df, ["Patient ID", "patient_id"]) 

    # 1) Claim amount distribution
    if billed is not None and billed.dropna().shape[0] > 0:
        plt.figure(figsize=(10, 5))
        plt.hist(billed.dropna(), bins=50, edgecolor="black")
        plt.title("Distribution of Claim Amounts")
        plt.xlabel("Billed Amount ($)")
        plt.ylabel("Frequency")
        plt.grid(axis="y", alpha=0.3)
        out = figures_dir / "claim_amount_distribution.png"
        plt.tight_layout()
        plt.savefig(out, dpi=120, bbox_inches="tight")
        plt.close()
        saved.append(out)

    # 2) Total cost per patient (boxplot)
    if patient_col and billed is not None and billed.dropna().shape[0] > 0:
        patient_total = df.groupby(patient_col)["Billed Amount"].sum()
        plt.figure(figsize=(7, 5))
        plt.boxplot([patient_total.values], tick_labels=["Total Cost per Patient"])
        plt.title("Total Cost per Patient")
        plt.ylabel("Total Cost ($)")
        plt.grid(alpha=0.3)
        out = figures_dir / "patient_total_cost_boxplot.png"
        plt.tight_layout()
        plt.savefig(out, dpi=120, bbox_inches="tight")
        plt.close()
        saved.append(out)

    # 3) Top diagnoses by total billed
    if diagnosis_col and billed is not None and billed.dropna().shape[0] > 0:
        diag = df.groupby(diagnosis_col)["Billed Amount"].sum().sort_values(ascending=False).head(5)
        plt.figure(figsize=(10, 5))
        diag.plot(kind="bar")
        plt.title("Top 5 Diagnoses by Total Billed Amount")
        plt.xlabel("Diagnosis Code")
        plt.ylabel("Total Billed Amount ($)")
        plt.grid(axis="y", alpha=0.3)
        out = figures_dir / "top5_diagnoses_total_billed.png"
        plt.tight_layout()
        plt.savefig(out, dpi=120, bbox_inches="tight")
        plt.close()
        saved.append(out)

    # 4) Monthly trend
    if date_col and date_col in df.columns:
        if not pd.api.types.is_datetime64_any_dtype(df[date_col]):
            parsed = pd.to_datetime(df[date_col], errors="coerce")
        else:
            parsed = df[date_col]

        if parsed.notna().sum() > 0 and billed is not None:
            tmp = df.copy()
            tmp["__month"] = parsed.dt.to_period("M").astype(str)
            monthly = tmp.groupby("__month")["Billed Amount"].sum()
            plt.figure(figsize=(12, 5))
            monthly.plot(kind="line", marker="o", linewidth=2)
            plt.title("Monthly Billed Amounts")
            plt.xlabel("Month")
            plt.ylabel("Total Billed Amount ($)")
            plt.grid(alpha=0.3)
            out = figures_dir / "monthly_billed_amounts.png"
            plt.tight_layout()
            plt.savefig(out, dpi=120, bbox_inches="tight")
            plt.close()
            saved.append(out)

    return saved


def write_report(
    *,
    outputs_dir: Path,
    input_csv: Path,
    clean_csv: Path,
    kpis_summary_csv: Path,
    cost_concentration_csv: Path,
    anomalies_csv: Path,
    figure_paths: list[Path],
    anomaly_count: int,
) -> Path:
    report_path = outputs_dir / "REPORT.md"

    kpis = pd.read_csv(kpis_summary_csv)
    row = kpis.iloc[0].to_dict() if not kpis.empty else {}

    def m(key: str) -> str:
        v = row.get(key, "")
        return "" if pd.isna(v) else str(v)

    lines: list[str] = []
    lines.append("# Healthcare Claims Pipeline Report")
    lines.append("")
    lines.append("Generated by: `python -m scripts.run_all`")
    lines.append("")
    lines.append("## Inputs")
    lines.append("")
    lines.append(f"- Input CSV: `{input_csv.name}`")
    lines.append(f"- Clean dataset: `data/{clean_csv.name}`")
    lines.append("")
    lines.append("## Key KPIs")
    lines.append("")
    lines.append(f"- Rows: {m('row_count')}")
    lines.append(f"- Total billed amount: ${m('total_billed_amount')}")
    lines.append(f"- Avg claim amount: ${m('avg_claim_amount')}")
    lines.append(f"- Median claim amount: ${m('median_claim_amount')}")
    lines.append(f"- P95 claim amount: ${m('p95_claim_amount')}")
    if m("unique_patients"):
        lines.append(f"- Unique patients: {m('unique_patients')}")
    if m("unique_diagnoses"):
        lines.append(f"- Unique diagnoses: {m('unique_diagnoses')}")
    if m("top_diagnosis_code"):
        lines.append(
            f"- Top diagnosis: {m('top_diagnosis_code')} (${m('top_diagnosis_total_billed')}, {m('top_diagnosis_pct_of_total')}% of total)"
        )
    if m("date_min") and m("date_max"):
        lines.append(f"- Date range: {m('date_min')} → {m('date_max')}")

    lines.append("")
    lines.append("## Outputs")
    lines.append("")
    lines.append("Tables:")
    lines.append("")
    lines.append("- `tables/missingness.csv`")
    lines.append("- `tables/basic_profile.csv`")
    lines.append(f"- `tables/{Path(kpis_summary_csv).name}`")
    lines.append(f"- `tables/{Path(cost_concentration_csv).name}`")
    lines.append(f"- `tables/{Path(anomalies_csv).name}`")
    lines.append("")

    lines.append("Anomaly detection:")
    lines.append("")
    lines.append(f"- Flagged patients (z-score ≥ 3.0 on patient total billed): {anomaly_count}")
    if anomaly_count == 0:
        lines.append(
            "- Note: In synthetic or tightly-bounded data, patient totals may not produce extreme z-scores; this is expected."
        )
    lines.append("")

    if figure_paths:
        lines.append("Figures:")
        lines.append("")
        for p in figure_paths:
            rel = f"figures/{p.name}"
            lines.append(f"- {rel}")
        lines.append("")
        for p in figure_paths:
            rel = f"figures/{p.name}"
            title = p.stem.replace("_", " ").title()
            lines.append(f"### {title}")
            lines.append("")
            lines.append(f"![{title}]({rel})")
            lines.append("")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run end-to-end healthcare claims pipeline.")
    parser.add_argument(
        "--input",
        help="Path to input CSV (default: claim_data.csv if present)",
        default=None,
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    outputs_dir = project_root / "outputs"

    input_csv = _pick_input_path(project_root, args.input)

    df_raw = load_dataset(input_csv)

    try:
        run_integrity_checks(df_raw, outputs_dir=outputs_dir)
    except DataQualityError as e:
        # Ensure the error is printed clearly for CI/console usage.
        raise

    df_clean = clean_dataset(df_raw)

    clean_csv = outputs_dir / "data" / "claims_clean.csv"
    clean_csv.parent.mkdir(parents=True, exist_ok=True)
    df_clean.to_csv(clean_csv, index=False)

    tables_dir = outputs_dir / "tables"
    _kpis_long_csv, kpis_summary_csv = _write_kpis_outputs(df_clean, tables_dir=tables_dir)
    analyses = _write_claims_analyses(df_clean, outputs_dir=outputs_dir)
    figure_paths = save_figures(df_clean, figures_dir=outputs_dir / "figures")

    # Prefer the Step-5 named figures in the report (if present)
    step5_figs = analyses.get("figures", [])
    if step5_figs:
        figure_paths = list(step5_figs)

    write_report(
        outputs_dir=outputs_dir,
        input_csv=input_csv,
        clean_csv=clean_csv,
        kpis_summary_csv=kpis_summary_csv,
        cost_concentration_csv=analyses["cost_concentration_csv"],
        anomalies_csv=analyses["anomalies_csv"],
        figure_paths=figure_paths,
        anomaly_count=int(analyses.get("anomaly_count", 0)),
    )

    print("Pipeline completed successfully.")
    print(f"- Report: {str((outputs_dir / 'REPORT.md').as_posix())}")
    print(f"- Clean dataset: {str(clean_csv.as_posix())}")
    print(f"- KPIs: {str(kpis_summary_csv.as_posix())}")
    print(f"- Figures: {str((outputs_dir / 'figures').as_posix())}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
