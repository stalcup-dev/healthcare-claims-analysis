"""Generate data dictionary from the cleaned dataset."""
from __future__ import annotations

from pathlib import Path

import pandas as pd


def infer_column_type(series: pd.Series) -> str:
    """Infer a simple type label for display."""
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"
    if pd.api.types.is_numeric_dtype(series):
        dtype_name = str(series.dtype)
        if "int" in dtype_name:
            return "integer"
        return "numeric"
    if pd.api.types.is_bool_dtype(series):
        return "boolean"
    return "string"


def sample_values(series: pd.Series, n: int = 5) -> str:
    """Get up to n non-null example values."""
    vals = series.dropna().head(n).tolist()
    return "; ".join(str(v)[:50] for v in vals) if vals else "(all null)"


def generate_data_dictionary(clean_csv: Path, *, output_path: Path) -> Path:
    """Generate docs/data_dictionary.md from the cleaned dataset."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(clean_csv)
    rows = int(df.shape[0])
    cols = int(df.shape[1])

    # Infer grain
    claim_id_candidates = ["Claim ID", "claim_id"]
    claim_id_col = next((c for c in claim_id_candidates if c in df.columns), None)
    
    patient_id_candidates = ["Patient ID", "patient_id", "member_id"]
    patient_id_col = next((c for c in patient_id_candidates if c in df.columns), None)

    if claim_id_col and df[claim_id_col].is_unique:
        grain = "One row per claim (unique Claim ID)."
    elif patient_id_col and df[patient_id_col].is_unique:
        grain = "One row per patient (unique Patient ID)."
    elif patient_id_col:
        grain = "Multiple rows per patient; likely one row per claim/service date."
    else:
        grain = "Unable to determine; check raw data."

    # Build lines
    lines: list[str] = []
    lines.append("# Data Dictionary")
    lines.append("")
    lines.append("## Dataset Overview")
    lines.append("")
    lines.append(f"- **Source**: `outputs/data/claims_clean.csv`")
    lines.append(f"- **Rows**: {rows:,}")
    lines.append(f"- **Columns**: {cols}")
    lines.append(f"- **Grain**: {grain}")
    lines.append("")

    lines.append("## Column Details")
    lines.append("")
    lines.append("| Column | Type | % Missing | Example Values |")
    lines.append("|---|---|---:|---|")

    for col in df.columns:
        col_type = infer_column_type(df[col])
        pct_missing = float(df[col].isna().mean() * 100.0)
        examples = sample_values(df[col], n=3)
        lines.append(f"| {col} | {col_type} | {pct_missing:.1f}% | {examples} |")

    lines.append("")
    lines.append("## Assumptions & Notes")
    lines.append("")
    lines.append("- **Cleaning applied**: Rows with missing `Billed Amount` removed; records with `Billed Amount ≤ 0` removed.")
    lines.append("- **Date parsing**: `Date of Service` parsed to datetime; unparseable dates are dropped.")
    lines.append("- **Scope**: This is synthetic data from Kaggle (no PHI concerns).")
    lines.append("- **Real data considerations**: For production, add PII handling, HIPAA audit trails, and data lineage.")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Path to clean dataset CSV")
    parser.add_argument("--output", required=True, help="Path to output data_dictionary.md")
    args = parser.parse_args()
    
    generate_data_dictionary(Path(args.input), output_path=Path(args.output))
    print(f"✓ Data dictionary: {args.output}")
