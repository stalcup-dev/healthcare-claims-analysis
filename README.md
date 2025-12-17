# Healthcare Claims Analysis Project

Python-based analysis of synthetic healthcare claims data using a reproducible, auditable pipeline.

## Quickstart

```bash
# Install dependencies
pip install pandas numpy matplotlib jupyter

# Run the full analysis end-to-end
python -m scripts.run_all
```

This generates:
- Clean dataset: `outputs/data/claims_clean.csv`
- Tables: `outputs/tables/*.csv` (KPIs, cost concentration, anomalies, missingness)
- Figures: `outputs/figures/*.png` (trends, diagnoses, Pareto)
- Report: `outputs/REPORT.md`
- Decision memo: `docs/decision_memo.md`
- Data dictionary: `docs/data_dictionary.md`

## Results (from pipeline outputs)

| Metric | Value |
|---|---|
| Total claims | 1,000 |
| Total billed | $297,191.00 |
| Unique patients | 1,000 |
| Average claim | $297.19 |
| Median claim | $297.00 |
| P95 claim | $480.00 |
| PMPM billed | $297.19 |
| Unique diagnoses | 100 |
| Top diagnosis | A05.4 ($5,872.00, 1.98%) |
| Date range | 2024-05-01 to 2024-09-20 |

## Cost Concentration (Pareto)

| % of Patients | % of Total Cost |
|---|---|
| Top 1% | 1.68% |
| Top 5% | 8.25% |
| Top 10% | 16.12% |

## Pipeline Architecture

The project uses a modular, reproducible architecture:

- **Data integrity**: `src/claims/quality.py` runs checks on ingestion (missingness, ranges, uniqueness).
- **Metrics & analysis**: `src/claims/metrics.py` computes KPIs, cost concentration, anomalies.
- **Orchestration**: `scripts/run_all.py` chains load → check → clean → analyze → render.
- **Documentation**: `scripts/render_readme.py`, `scripts/render_decision_memo.py`, `scripts/gen_data_dictionary.py`
  pull from output tables; docs always match outputs (no hand-typed numbers).

## Files & Folders

- `claim_data.csv` — Input synthetic dataset
- `src/claims/` — Core analysis modules (quality checks, metrics)
- `scripts/` — Orchestration & documentation rendering
- `outputs/` — Generated tables (CSV), figures (PNG), reports (MD)
- `docs/` — Rendered documentation (data dictionary, decision memo)
- `Healthcare_Claims_Analysis.ipynb` — Legacy exploratory notebook (for reference)

## Key Insights

- **Top 10% of patients** drive 16.1% of total cost; targeted interventions could yield high ROI.
- **Diagnosis A05.4** is the leading cost driver at 1.98% of total spend; consider prevention/management programs.
- **Synthetic data note**: This is balanced/uniform sample data; real claims typically show higher cost concentration.

## Approach & Methodology

See [docs/decision_memo.md](docs/decision_memo.md) for findings and recommendations.

See [docs/data_dictionary.md](docs/data_dictionary.md) for column definitions and assumptions.

Full KPI definitions are in README's Methodology section (or inspect `outputs/tables/kpis_summary.csv` directly).

## Technologies

- **Python 3.10+**
- **pandas** — Data manipulation
- **numpy** — Numerical computing
- **matplotlib** — Visualization

## Running Specific Steps

If you only want to regenerate docs (without re-running analysis):

```bash
python scripts/render_readme.py --kpis outputs/tables/kpis_summary.csv --cost-concentration outputs/tables/cost_concentration.csv --output README.md
python scripts/render_decision_memo.py --kpis outputs/tables/kpis_summary.csv --cost-concentration outputs/tables/cost_concentration.csv --anomalies outputs/tables/patient_anomalies.csv --output docs/decision_memo.md
python scripts/gen_data_dictionary.py --input outputs/data/claims_clean.csv --output docs/data_dictionary.md
```

## Limitations

- **Synthetic data**: Patterns may not reflect real-world healthcare claims distributions.
- **Scope**: No clinical outcomes, provider performance, or member demographics included.
- **Temporal**: Single fixed date range; seasonal/multi-year trends not visible.

