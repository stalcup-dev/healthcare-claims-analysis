from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable

import pandas as pd


@dataclass(frozen=True)
class QualityConfig:
    required_columns: tuple[str, ...] = ("Billed Amount",)
    date_columns: tuple[str, ...] = ("Date of Service",)
    claim_id_columns: tuple[str, ...] = ("Claim ID", "claim_id")


class DataQualityError(ValueError):
    pass


def _first_existing_column(df: pd.DataFrame, candidates: Iterable[str]) -> str | None:
    for col in candidates:
        if col in df.columns:
            return col
    return None


def write_missingness_table(df: pd.DataFrame, output_csv: Path) -> pd.DataFrame:
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    missing = pd.DataFrame(
        {
            "column": df.columns,
            "missing_count": [int(df[col].isna().sum()) for col in df.columns],
            "missing_pct": [float(df[col].isna().mean() * 100.0) for col in df.columns],
        }
    ).sort_values(["missing_count", "column"], ascending=[False, True])

    missing.to_csv(output_csv, index=False)
    return missing


def write_basic_profile_table(
    *,
    df: pd.DataFrame,
    output_csv: Path,
    date_col: str | None,
    claim_id_col: str | None,
    grain_guess: str,
) -> pd.DataFrame:
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    rows = int(df.shape[0])
    cols = int(df.shape[1])

    items: list[tuple[str, str]] = [("row_count", str(rows)), ("column_count", str(cols))]

    if date_col and date_col in df.columns:
        parsed = pd.to_datetime(df[date_col], errors="coerce")
        nat_count = int(parsed.isna().sum())
        date_min = parsed.min()
        date_max = parsed.max()
        items.extend(
            [
                ("date_column", date_col),
                ("date_parse_failures", str(nat_count)),
                ("date_min", "" if pd.isna(date_min) else str(date_min.date())),
                ("date_max", "" if pd.isna(date_max) else str(date_max.date())),
            ]
        )

    amount_cols = [c for c in df.columns if "amount" in c.lower()]
    for col in amount_cols:
        numeric = pd.to_numeric(df[col], errors="coerce")
        items.extend(
            [
                (f"{col}__min", "" if numeric.dropna().empty else f"{float(numeric.min()):.6g}"),
                (f"{col}__max", "" if numeric.dropna().empty else f"{float(numeric.max()):.6g}"),
                (f"{col}__mean", "" if numeric.dropna().empty else f"{float(numeric.mean()):.6g}"),
            ]
        )

    if claim_id_col and claim_id_col in df.columns:
        dupe_count = int(df[claim_id_col].duplicated().sum())
        items.extend(
            [
                ("claim_id_column", claim_id_col),
                ("duplicate_claim_id_count", str(dupe_count)),
            ]
        )

    items.append(("grain_guess", grain_guess))

    profile = pd.DataFrame(items, columns=["metric", "value"])
    profile.to_csv(output_csv, index=False)
    return profile


def infer_grain(df: pd.DataFrame) -> str:
    # Best-effort heuristic for auditability.
    if "Claim ID" in df.columns:
        if df["Claim ID"].is_unique:
            return "One row per claim (unique Claim ID)."
        return "Claim ID present but not unique; grain unclear."

    if "Patient ID" in df.columns:
        unique_patients = int(df["Patient ID"].nunique(dropna=True))
        if unique_patients == int(df.shape[0]):
            return "One row per patient (Patient ID unique across rows)."
        return "Multiple rows per patient (Patient ID repeats); likely one row per claim/service."

    return "Unable to infer grain (no Claim ID or Patient ID)."


def run_integrity_checks(
    df: pd.DataFrame,
    *,
    outputs_dir: Path,
    config: QualityConfig | None = None,
) -> dict[str, str]:
    """Run audit-style integrity checks.

    Always writes:
    - outputs/tables/missingness.csv
    - outputs/tables/basic_profile.csv

    Raises DataQualityError on failures with next steps.
    """

    cfg = config or QualityConfig()

    tables_dir = outputs_dir / "tables"
    missingness_path = tables_dir / "missingness.csv"
    profile_path = tables_dir / "basic_profile.csv"

    date_col = _first_existing_column(df, cfg.date_columns)
    claim_id_col = _first_existing_column(df, cfg.claim_id_columns)
    grain_guess = infer_grain(df)

    write_missingness_table(df, missingness_path)
    write_basic_profile_table(
        df=df,
        output_csv=profile_path,
        date_col=date_col,
        claim_id_col=claim_id_col,
        grain_guess=grain_guess,
    )

    failures: list[str] = []

    if int(df.shape[0]) <= 0:
        failures.append("Row count is 0. The input dataset appears empty.")

    missing_required = [c for c in cfg.required_columns if c not in df.columns]
    if missing_required:
        failures.append(
            "Missing required columns: " + ", ".join(missing_required) + "."
        )

    # Date sanity (if present)
    if date_col:
        parsed = pd.to_datetime(df[date_col], errors="coerce")
        if parsed.notna().sum() == 0:
            failures.append(
                f"Column '{date_col}' exists but none of the values could be parsed as dates."
            )
        else:
            date_min = parsed.min()
            date_max = parsed.max()
            if pd.notna(date_max):
                latest_allowed = datetime.now() + timedelta(days=1)
                if date_max.to_pydatetime() > latest_allowed:
                    failures.append(
                        f"Date max ({date_max.date()}) is in the future; check '{date_col}' parsing/format."
                    )
            if pd.notna(date_min) and pd.notna(date_max) and date_min > date_max:
                failures.append(
                    f"Date min ({date_min.date()}) is after date max ({date_max.date()}); check '{date_col}'."
                )

    # Numeric range sanity
    if "Billed Amount" in df.columns:
        billed = pd.to_numeric(df["Billed Amount"], errors="coerce")
        invalid = int((billed.isna() | (billed <= 0)).sum())
        if invalid > 0:
            failures.append(
                f"Found {invalid} rows with missing or non-positive 'Billed Amount'."
            )

    for col in [c for c in df.columns if c != "Billed Amount" and "amount" in c.lower()]:
        numeric = pd.to_numeric(df[col], errors="coerce")
        negative = int((numeric < 0).sum())
        if negative > 0:
            failures.append(f"Found {negative} rows with negative values in '{col}'.")

    # Grain sanity: Claim ID uniqueness if present
    if claim_id_col and claim_id_col in df.columns:
        dupes = int(df[claim_id_col].duplicated().sum())
        if dupes > 0:
            failures.append(
                f"Column '{claim_id_col}' should be unique but has {dupes} duplicate values."
            )

    if failures:
        next_steps = (
            "Next steps:\n"
            f"- Review {missingness_path.as_posix()} for missing fields\n"
            f"- Review {profile_path.as_posix()} for basic stats\n"
            "- Fix the input file (or update required columns) and re-run `python -m scripts.run_all`"
        )
        message = "Integrity checks failed:\n- " + "\n- ".join(failures) + "\n\n" + next_steps
        raise DataQualityError(message)

    return {
        "missingness_csv": str(missingness_path),
        "basic_profile_csv": str(profile_path),
        "grain_guess": grain_guess,
        "date_column": date_col or "",
        "claim_id_column": claim_id_col or "",
    }
