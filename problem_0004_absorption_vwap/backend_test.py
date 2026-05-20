#!/usr/bin/env python3
"""
Backend test suite for Post-Absorption VWAP Reversal Engine V1
Tests CLI commands, data processing, and validation logic
"""

import subprocess
import sys
from pathlib import Path


class AbsorptionVWAPTester:
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.project_root = Path("/app/problem_0004_absorption_vwap")

    def run_test(self, name: str, test_func) -> bool:
        """Run a single test"""
        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        try:
            test_func()
            self.tests_passed += 1
            print("✅ Passed")
            return True
        except AssertionError as e:
            print(f"❌ Failed - {str(e)}")
            return False
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False

    def test_project_structure(self):
        """Verify project structure exists"""
        required_paths = [
            "research_engine/__init__.py",
            "research_engine/cli.py",
            "research_engine/data_loader.py",
            "research_engine/vwap.py",
            "research_engine/features.py",
            "research_engine/labels.py",
            "research_engine/backtest.py",
            "research_engine/validation.py",
            "research_engine/plateau.py",
            "research_engine/reports.py",
            "configs/default_config.yaml",
            "configs/grid.yaml",
            "pine/problem_0004_absorption_vwap_v1.pine",
            "tests/test_features.py",
            "tests/test_labels.py",
            "tests/test_validation.py",
            "data/examples/synthetic_ohlcv_1m.csv",
        ]
        for path in required_paths:
            full_path = self.project_root / path
            assert full_path.exists(), f"Missing required path: {path}"

    def test_pytest_suite(self):
        """Run pytest suite"""
        result = subprocess.run(
            ["python", "-m", "pytest", "-q"],
            cwd=self.project_root,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"pytest failed: {result.stderr}"
        assert "passed" in result.stdout, "No tests passed"

    def test_cli_validate(self):
        """Test validate CLI command"""
        result = subprocess.run(
            [
                "python",
                "-m",
                "research_engine",
                "validate",
                "--data",
                "data/examples/synthetic_ohlcv_1m.csv",
                "--config",
                "configs/default_config.yaml",
            ],
            cwd=self.project_root,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"validate command failed: {result.stderr}"
        assert "validation_status=INSUFFICIENT_DATA" in result.stdout
        assert "run_dir=" in result.stdout
        assert "reason=" in result.stdout

    def test_cli_backtest(self):
        """Test backtest CLI command"""
        result = subprocess.run(
            [
                "python",
                "-m",
                "research_engine",
                "backtest",
                "--data",
                "data/examples/synthetic_ohlcv_1m.csv",
                "--config",
                "configs/default_config.yaml",
            ],
            cwd=self.project_root,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"backtest command failed: {result.stderr}"
        assert "validation_status=INSUFFICIENT_DATA" in result.stdout
        assert "trades=" in result.stdout
        assert "expectancy_after_cost=" in result.stdout

    def test_cli_report(self):
        """Test report CLI command"""
        result = subprocess.run(
            ["python", "-m", "research_engine", "report", "--run", "latest"],
            cwd=self.project_root,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"report command failed: {result.stderr}"
        assert len(result.stdout) > 0, "Report output is empty"

    def test_report_files_generated(self):
        """Verify report files are generated"""
        latest_run_file = self.project_root / "reports" / "latest_run.txt"
        assert latest_run_file.exists(), "latest_run.txt not found"
        
        run_dir = Path(latest_run_file.read_text().strip())
        assert run_dir.exists(), f"Run directory not found: {run_dir}"
        
        required_files = [
            "summary.json",
            "summary.md",
            "report.html",
            "trades.csv",
            "labels.csv",
            "fold_metrics.csv",
            "baseline_compare.csv",
            "features.csv",
        ]
        for filename in required_files:
            file_path = run_dir / filename
            assert file_path.exists(), f"Missing report file: {filename}"

    def test_no_lookahead_bias(self):
        """Verify features don't contain label columns"""
        import pandas as pd
        from research_engine.features import compute_absorption_features
        from research_engine.schemas import LABEL_COLUMNS
        
        df = pd.DataFrame({
            "timestamp": pd.date_range("2024-01-01 09:30", periods=6, freq="min"),
            "open": [100, 101, 102, 103, 104, 105],
            "high": [101, 102, 103, 104, 105, 106],
            "low": [99, 100, 101, 102, 103, 104],
            "close": [101, 102, 103, 104, 105, 105.5],
            "volume": [10, 12, 11, 13, 14, 1000],
            "symbol": ["MNQ"] * 6,
            "timeframe": ["1m"] * 6,
            "session_date": ["2024-01-01"] * 6,
        })
        
        features = compute_absorption_features(df, {})
        leaked = LABEL_COLUMNS.intersection(features.columns)
        assert len(leaked) == 0, f"Label columns leaked into features: {leaked}"

    def test_pine_script_structure(self):
        """Verify Pine script has required elements"""
        pine_file = self.project_root / "pine" / "problem_0004_absorption_vwap_v1.pine"
        content = pine_file.read_text()
        
        # Check version
        assert "//@version=6" in content or "@version=6" in content, "Not Pine v6"
        
        # Check required elements
        required_elements = [
            "barstate.isconfirmed",  # Confirmed-bar logic
            "sessionVwap",  # Session VWAP
            "plotshape",  # Markers
            "alertcondition",  # Alerts
            "enablePaperStrategy",  # Optional paper strategy
            "table.new",  # Debug table
        ]
        for element in required_elements:
            assert element in content, f"Missing required element: {element}"
        
        # Check no live execution
        forbidden = ["webhook", "broker"]
        for word in forbidden:
            # Allow in comments but not in actual code
            lines = [line for line in content.split("\n") if not line.strip().startswith("//")]
            code_only = "\n".join(lines)
            assert word not in code_only.lower(), f"Found forbidden keyword: {word}"

    def print_summary(self):
        """Print test summary"""
        print(f"\n{'='*60}")
        print(f"📊 Tests passed: {self.tests_passed}/{self.tests_run}")
        print(f"{'='*60}")
        return 0 if self.tests_passed == self.tests_run else 1


def main():
    tester = AbsorptionVWAPTester()
    
    # Run all tests
    tester.run_test("Project structure", tester.test_project_structure)
    tester.run_test("Pytest suite", tester.test_pytest_suite)
    tester.run_test("CLI validate command", tester.test_cli_validate)
    tester.run_test("CLI backtest command", tester.test_cli_backtest)
    tester.run_test("CLI report command", tester.test_cli_report)
    tester.run_test("Report files generation", tester.test_report_files_generated)
    tester.run_test("No lookahead bias", tester.test_no_lookahead_bias)
    tester.run_test("Pine script structure", tester.test_pine_script_structure)
    
    return tester.print_summary()


if __name__ == "__main__":
    sys.exit(main())
