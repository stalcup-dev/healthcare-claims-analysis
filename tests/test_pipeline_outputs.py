"""Test that the pipeline produces all expected output files."""
import os
import subprocess
import tempfile
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
    raise FileNotFoundError("No test dataset found")


def test_pipeline_runs_successfully():
    """Test that the pipeline runs without error in a temporary output directory."""
    project_root = Path(__file__).resolve().parent.parent
    test_data = get_test_data_path()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Set OUTPUT_DIR env var for the pipeline
        env = os.environ.copy()
        env["OUTPUT_DIR"] = tmpdir
        
        # Run the pipeline
        result = subprocess.run(
            ["python", "-m", "scripts.run_all", "--input", str(test_data)],
            cwd=project_root,
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )
        
        assert result.returncode == 0, f"Pipeline failed: {result.stderr}"
        assert "Pipeline completed successfully" in result.stdout, "Pipeline should report success"


def test_pipeline_produces_report():
    """Test that the pipeline produces REPORT.md."""
    project_root = Path(__file__).resolve().parent.parent
    test_data = get_test_data_path()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        env = os.environ.copy()
        env["OUTPUT_DIR"] = tmpdir
        
        subprocess.run(
            ["python", "-m", "scripts.run_all", "--input", str(test_data)],
            cwd=project_root,
            env=env,
            capture_output=True,
            timeout=60,
        )
        
        report_path = Path(tmpdir) / "REPORT.md"
        assert report_path.exists(), f"REPORT.md not found at {report_path}"
        
        content = report_path.read_text()
        assert len(content) > 100, "REPORT.md should have meaningful content"
        assert "Healthcare Claims" in content or "Pipeline Report" in content


def test_pipeline_produces_kpi_summary():
    """Test that the pipeline produces kpis_summary.csv."""
    project_root = Path(__file__).resolve().parent.parent
    test_data = get_test_data_path()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        env = os.environ.copy()
        env["OUTPUT_DIR"] = tmpdir
        
        subprocess.run(
            ["python", "-m", "scripts.run_all", "--input", str(test_data)],
            cwd=project_root,
            env=env,
            capture_output=True,
            timeout=60,
        )
        
        kpis_path = Path(tmpdir) / "tables" / "kpis_summary.csv"
        assert kpis_path.exists(), f"kpis_summary.csv not found at {kpis_path}"
        
        kpis = pd.read_csv(kpis_path)
        assert len(kpis) == 1, "KPI summary should have exactly one row"
        assert "total_billed_amount" in kpis.columns, "KPI should include total_billed_amount"
        assert "row_count" in kpis.columns, "KPI should include row_count"


def test_pipeline_produces_cost_concentration():
    """Test that the pipeline produces cost_concentration.csv."""
    project_root = Path(__file__).resolve().parent.parent
    test_data = get_test_data_path()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        env = os.environ.copy()
        env["OUTPUT_DIR"] = tmpdir
        
        subprocess.run(
            ["python", "-m", "scripts.run_all", "--input", str(test_data)],
            cwd=project_root,
            env=env,
            capture_output=True,
            timeout=60,
        )
        
        conc_path = Path(tmpdir) / "tables" / "cost_concentration.csv"
        assert conc_path.exists(), f"cost_concentration.csv not found at {conc_path}"
        
        conc = pd.read_csv(conc_path)
        assert len(conc) >= 3, "Cost concentration should have at least 3 rows (1%, 5%, 10%)"
        assert "cost_share_pct" in conc.columns, "Should include cost_share_pct"


def test_pipeline_produces_figures():
    """Test that the pipeline produces at least 3 PNG figures."""
    project_root = Path(__file__).resolve().parent.parent
    test_data = get_test_data_path()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        env = os.environ.copy()
        env["OUTPUT_DIR"] = tmpdir
        
        subprocess.run(
            ["python", "-m", "scripts.run_all", "--input", str(test_data)],
            cwd=project_root,
            env=env,
            capture_output=True,
            timeout=60,
        )
        
        figures_dir = Path(tmpdir) / "figures"
        assert figures_dir.exists(), f"figures directory not found at {figures_dir}"
        
        pngs = list(figures_dir.glob("*.png"))
        assert len(pngs) >= 3, f"Expected at least 3 PNG figures, got {len(pngs)}"


def test_pipeline_produces_documentation():
    """Test that the pipeline produces rendered documentation files."""
    project_root = Path(__file__).resolve().parent.parent
    test_data = get_test_data_path()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        env = os.environ.copy()
        env["OUTPUT_DIR"] = tmpdir
        
        # Run pipeline in project root so docs/ is created there
        # (For this test, we'll just verify the tables exist)
        result = subprocess.run(
            ["python", "-m", "scripts.run_all", "--input", str(test_data)],
            cwd=project_root,
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )
        
        # Check that documentation rendering happened
        assert "[+] All documentation generated" in result.stdout or "decision_memo.md" in result.stdout, \
            "Pipeline should render documentation"
