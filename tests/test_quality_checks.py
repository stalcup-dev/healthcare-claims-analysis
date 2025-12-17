"""Test that quality checks run successfully without raising exceptions."""
from pathlib import Path
import tempfile

import pandas as pd
import pytest

from src.claims.quality import run_integrity_checks


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
    raise FileNotFoundError("No test dataset found")


def test_quality_checks_pass():
    """Test that integrity checks run without raising an exception."""
    data_path = get_test_data_path()
    df = pd.read_csv(data_path)
    
    # Use a temporary directory for test outputs
    with tempfile.TemporaryDirectory() as tmpdir:
        outputs_dir = Path(tmpdir)
        
        # This should not raise an exception
        result = run_integrity_checks(df, outputs_dir=outputs_dir)
        
        assert result is not None, "Quality check result should not be None"
        assert isinstance(result, dict), "Result should be a dictionary"


def test_quality_checks_generate_missingness_report():
    """Test that quality checks produce the missingness CSV."""
    data_path = get_test_data_path()
    df = pd.read_csv(data_path)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        outputs_dir = Path(tmpdir)
        run_integrity_checks(df, outputs_dir=outputs_dir)
        
        missingness_csv = outputs_dir / "tables" / "missingness.csv"
        assert missingness_csv.exists(), f"Missingness CSV not found at {missingness_csv}"
        
        # Verify it's a valid CSV with expected columns
        missing = pd.read_csv(missingness_csv)
        assert "column" in missing.columns, "Missingness CSV should have 'column' column"
        assert "missing_count" in missing.columns, "Missingness CSV should have 'missing_count' column"
        assert len(missing) > 0, "Missingness report should have at least one row"


def test_quality_checks_generate_basic_profile():
    """Test that quality checks produce the basic profile CSV."""
    data_path = get_test_data_path()
    df = pd.read_csv(data_path)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        outputs_dir = Path(tmpdir)
        run_integrity_checks(df, outputs_dir=outputs_dir)
        
        profile_csv = outputs_dir / "tables" / "basic_profile.csv"
        assert profile_csv.exists(), f"Basic profile CSV not found at {profile_csv}"
        
        # Verify it's a valid CSV with expected structure
        profile = pd.read_csv(profile_csv)
        assert "metric" in profile.columns, "Profile CSV should have 'metric' column"
        assert "value" in profile.columns, "Profile CSV should have 'value' column"
        assert len(profile) > 0, "Profile should have at least one metric"
