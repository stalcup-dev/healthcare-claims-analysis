"""Test that the dataset loads successfully and contains required columns."""
from pathlib import Path

import pandas as pd
import pytest


def get_test_data_path() -> Path:
    """Locate the test dataset."""
    project_root = Path(__file__).resolve().parent.parent
    candidates = [
        project_root / "claim_data.csv",
        project_root / "MedicalClaimsSynthetic1M.csv",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError("No test dataset found (claim_data.csv or MedicalClaimsSynthetic1M.csv)")


def test_dataset_loads():
    """Test that the dataset can be loaded without error."""
    data_path = get_test_data_path()
    df = pd.read_csv(data_path)
    assert df is not None, "DataFrame should not be None"
    assert len(df) > 0, "DataFrame should have at least one row"


def test_required_columns_exist():
    """Test that all required columns are present in the dataset."""
    data_path = get_test_data_path()
    df = pd.read_csv(data_path)
    
    required_columns = [
        "Claim ID",
        "Patient ID",
        "Billed Amount",
        "Date of Service",
        "Diagnosis Code",
    ]
    
    missing_cols = [col for col in required_columns if col not in df.columns]
    assert not missing_cols, f"Missing required columns: {missing_cols}"


def test_dataset_has_reasonable_size():
    """Test that the dataset has a reasonable number of rows and columns."""
    data_path = get_test_data_path()
    df = pd.read_csv(data_path)
    
    # At least 100 rows for a meaningful analysis
    assert len(df) >= 100, f"Dataset should have at least 100 rows, got {len(df)}"
    
    # At least 10 columns for reasonable structure
    assert len(df.columns) >= 10, f"Dataset should have at least 10 columns, got {len(df.columns)}"
