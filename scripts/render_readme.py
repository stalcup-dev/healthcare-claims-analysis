"""Render README.md from pipeline outputs."""
from __future__ import annotations

from pathlib import Path

import pandas as pd


def render_readme(
    kpis_csv: Path,
    cost_concentration_csv: Path,
    *,
    output_path: Path,
) -> Path:
    """Render README.md from pipeline KPI outputs."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    kpis = pd.read_csv(kpis_csv)
    if kpis.empty:
        raise ValueError(f"KPIs CSV is empty: {kpis_csv}")

    row = kpis.iloc[0].to_dict()
    cost_conc = pd.read_csv(cost_concentration_csv)

    # Extract all relevant values
    total_rows = int(row.get("row_count", 0))
    total_billed = float(row.get("total_billed_amount", 0))
    avg_claim = float(row.get("avg_claim_amount", 0))
    median_claim = float(row.get("median_claim_amount", 0))
    p95_claim = float(row.get("p95_claim_amount", 0))
    unique_patients = int(row.get("unique_patients", 0))
    unique_diagnoses = int(row.get("unique_diagnoses", 0))
    top_dx = str(row.get("top_diagnosis_code", ""))
    top_dx_billed = float(row.get("top_diagnosis_total_billed", 0))
    top_dx_pct = float(row.get("top_diagnosis_pct_of_total", 0))
    pmpm = float(row.get("pmpm_billed", 0))
    date_min = str(row.get("date_min", ""))
    date_max = str(row.get("date_max", ""))

    # Cost concentration
    top_1pct = cost_conc[cost_conc["top_pct_patients"] == 1]["cost_share_pct"].values
    top_5pct = cost_conc[cost_conc["top_pct_patients"] == 5]["cost_share_pct"].values
    top_10pct = cost_conc[cost_conc["top_pct_patients"] == 10]["cost_share_pct"].values

    top_1pct_val = float(top_1pct[0]) if len(top_1pct) > 0 else 0
    top_5pct_val = float(top_5pct[0]) if len(top_5pct) > 0 else 0
    top_10pct_val = float(top_10pct[0]) if len(top_10pct) > 0 else 0

    lines: list[str] = []
    lines.append("# Healthcare Claims Analysis Project")
    lines.append("")
    lines.append("Python-based analysis of synthetic healthcare claims data using a reproducible, auditable pipeline.")
    lines.append("")

    lines.append("## Quickstart")
    lines.append("")
    lines.append("```bash")
    lines.append("# Install dependencies")
    lines.append("pip install pandas numpy matplotlib jupyter")
    lines.append("")
    lines.append("# Run the full analysis end-to-end")
    lines.append("python -m scripts.run_all")
    lines.append("```")
    lines.append("")
    lines.append("This generates:")
    lines.append("- Clean dataset: `outputs/data/claims_clean.csv`")
    lines.append("- Tables: `outputs/tables/*.csv` (KPIs, cost concentration, anomalies, missingness)")
    lines.append("- Figures: `outputs/figures/*.png` (trends, diagnoses, Pareto)")
    lines.append("- Report: `outputs/REPORT.md`")
    lines.append("- Decision memo: `docs/decision_memo.md`")
    lines.append("- Data dictionary: `docs/data_dictionary.md`")
    lines.append("")

    lines.append("## Results (from pipeline outputs)")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---|")
    lines.append(f"| Total claims | {total_rows:,} |")
    lines.append(f"| Total billed | ${total_billed:,.2f} |")
    lines.append(f"| Unique patients | {unique_patients:,} |")
    lines.append(f"| Average claim | ${avg_claim:.2f} |")
    lines.append(f"| Median claim | ${median_claim:.2f} |")
    lines.append(f"| P95 claim | ${p95_claim:.2f} |")
    lines.append(f"| PMPM billed | ${pmpm:.2f} |")
    lines.append(f"| Unique diagnoses | {unique_diagnoses} |")
    lines.append(f"| Top diagnosis | {top_dx} (${top_dx_billed:,.2f}, {top_dx_pct:.2f}%) |")
    lines.append(f"| Date range | {date_min} to {date_max} |")
    lines.append("")

    lines.append("## Cost Concentration (Pareto)")
    lines.append("")
    lines.append("| % of Patients | % of Total Cost |")
    lines.append("|---|---|")
    lines.append(f"| Top 1% | {top_1pct_val:.2f}% |")
    lines.append(f"| Top 5% | {top_5pct_val:.2f}% |")
    lines.append(f"| Top 10% | {top_10pct_val:.2f}% |")
    lines.append("")

    lines.append("## Pipeline Architecture")
    lines.append("")
    lines.append("The project uses a modular, reproducible architecture:")
    lines.append("")
    lines.append("- **Data integrity**: `src/claims/quality.py` runs checks on ingestion (missingness, ranges, uniqueness).")
    lines.append("- **Metrics & analysis**: `src/claims/metrics.py` computes KPIs, cost concentration, anomalies.")
    lines.append("- **Orchestration**: `scripts/run_all.py` chains load → check → clean → analyze → render.")
    lines.append("- **Documentation**: `scripts/render_readme.py`, `scripts/render_decision_memo.py`, `scripts/gen_data_dictionary.py`")
    lines.append("  pull from output tables; docs always match outputs (no hand-typed numbers).")
    lines.append("")

    lines.append("## Files & Folders")
    lines.append("")
    lines.append("- `claim_data.csv` — Input synthetic dataset")
    lines.append("- `src/claims/` — Core analysis modules (quality checks, metrics)")
    lines.append("- `scripts/` — Orchestration & documentation rendering")
    lines.append("- `outputs/` — Generated tables (CSV), figures (PNG), reports (MD)")
    lines.append("- `docs/` — Rendered documentation (data dictionary, decision memo)")
    lines.append("- `Healthcare_Claims_Analysis.ipynb` — Legacy exploratory notebook (for reference)")
    lines.append("")

    lines.append("## Key Insights")
    lines.append("")
    lines.append(f"- **Top 10% of patients** drive {top_10pct_val:.1f}% of total cost; targeted interventions could yield high ROI.")
    lines.append(
        f"- **Diagnosis {top_dx}** is the leading cost driver at {top_dx_pct:.2f}% of total spend; "
        "consider prevention/management programs."
    )
    lines.append("- **Synthetic data note**: This is balanced/uniform sample data; real claims typically show higher cost concentration.")
    lines.append("")

    lines.append("## Approach & Methodology")
    lines.append("")
    lines.append("See [docs/decision_memo.md](docs/decision_memo.md) for findings and recommendations.")
    lines.append("")
    lines.append("See [docs/data_dictionary.md](docs/data_dictionary.md) for column definitions and assumptions.")
    lines.append("")
    lines.append("Full KPI definitions are in README's Methodology section (or inspect `outputs/tables/kpis_summary.csv` directly).")
    lines.append("")

    lines.append("## Technologies")
    lines.append("")
    lines.append("- **Python 3.10+**")
    lines.append("- **pandas** — Data manipulation")
    lines.append("- **numpy** — Numerical computing")
    lines.append("- **matplotlib** — Visualization")
    lines.append("")

    lines.append("## Running Specific Steps")
    lines.append("")
    lines.append("If you only want to regenerate docs (without re-running analysis):")
    lines.append("")
    lines.append("```bash")
    lines.append("python scripts/render_readme.py --kpis outputs/tables/kpis_summary.csv --cost-concentration outputs/tables/cost_concentration.csv --output README.md")
    lines.append("python scripts/render_decision_memo.py --kpis outputs/tables/kpis_summary.csv --cost-concentration outputs/tables/cost_concentration.csv --anomalies outputs/tables/patient_anomalies.csv --output docs/decision_memo.md")
    lines.append("python scripts/gen_data_dictionary.py --input outputs/data/claims_clean.csv --output docs/data_dictionary.md")
    lines.append("```")
    lines.append("")

    lines.append("## Limitations")
    lines.append("")
    lines.append("- **Synthetic data**: Patterns may not reflect real-world healthcare claims distributions.")
    lines.append("- **Scope**: No clinical outcomes, provider performance, or member demographics included.")
    lines.append("- **Temporal**: Single fixed date range; seasonal/multi-year trends not visible.")
    lines.append("")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--kpis", required=True, help="Path to kpis_summary.csv")
    parser.add_argument("--cost-concentration", required=True, help="Path to cost_concentration.csv")
    parser.add_argument("--output", required=True, help="Path to output README.md")
    args = parser.parse_args()

    render_readme(
        Path(args.kpis),
        Path(args.cost_concentration),
        output_path=Path(args.output),
    )
    print(f"✓ README: {args.output}")
