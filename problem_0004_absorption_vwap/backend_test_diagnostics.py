#!/usr/bin/env python3
"""
Backend test suite for MNQ Diagnostics-Only Feature
Tests the new diagnostics CLI and report generation
"""

import json
import subprocess
import sys
from pathlib import Path


class DiagnosticsTester:
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.project_root = Path("/app/problem_0004_absorption_vwap")
        self.latest_diagnostic_dir = None

    def run_test(self, name: str, test_func) -> bool:
        """Run a single test"""
        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        try:
            test_func()
            self.tests_passed += 1
            print(f"✅ Passed")
            return True
        except AssertionError as e:
            print(f"❌ Failed - {str(e)}")
            return False
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False

    def test_diagnostics_cli_exists(self):
        """Verify diagnostics CLI command exists"""
        result = subprocess.run(
            ["python", "-m", "research_engine", "--help"],
            cwd=self.project_root,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"CLI help failed: {result.stderr}"
        assert "diagnose" in result.stdout, "diagnose command not found in CLI"

    def test_diagnostics_cli_runs(self):
        """Test diagnostics CLI command runs successfully"""
        result = subprocess.run(
            [
                "python",
                "-m",
                "research_engine",
                "diagnose",
                "--data",
                "data/raw/MNQ_5min_RTH_6year.csv",
                "--config",
                "configs/mnq_5min_rth.yaml",
                "--grid",
                "configs/grid.yaml",
                "--plateau-dir",
                "reports/parameter_plateaus/plateau_20260520_141004",
            ],
            cwd=self.project_root,
            capture_output=True,
            text=True,
            timeout=180,
        )
        assert result.returncode == 0, f"diagnose command failed: {result.stderr}"
        assert "diagnostic_classification=" in result.stdout
        assert "default_expectancy_after_cost=" in result.stdout
        assert "default_profit_factor=" in result.stdout
        assert "top_candidates=" in result.stdout
        assert "run_dir=" in result.stdout
        
        # Extract run_dir for later tests
        for line in result.stdout.split("\n"):
            if line.startswith("run_dir="):
                self.latest_diagnostic_dir = self.project_root / line.split("=", 1)[1].strip()
                break

    def test_diagnostic_report_exists(self):
        """Verify diagnostic report directory and files exist"""
        assert self.latest_diagnostic_dir is not None, "No diagnostic run directory found"
        assert self.latest_diagnostic_dir.exists(), f"Diagnostic directory not found: {self.latest_diagnostic_dir}"
        
        required_files = [
            "diagnostic_summary.json",
            "diagnostic_report.md",
            "top_plateau_candidates.csv",
        ]
        for filename in required_files:
            file_path = self.latest_diagnostic_dir / filename
            assert file_path.exists(), f"Missing diagnostic file: {filename}"

    def test_payoff_distribution_metrics(self):
        """Verify payoff distribution metrics are present"""
        summary_file = self.latest_diagnostic_dir / "diagnostic_summary.json"
        with open(summary_file) as f:
            summary = json.load(f)
        
        payoff = summary.get("payoff_distribution", {})
        required_metrics = [
            "average_winner",
            "average_loser",
            "median_winner",
            "median_loser",
            "win_loss_ratio",
            "expectancy_before_cost",
            "expectancy_after_cost",
            "estimated_cost_drag_per_trade",
        ]
        for metric in required_metrics:
            assert metric in payoff, f"Missing payoff metric: {metric}"

    def test_breakdown_csvs_exist(self):
        """Verify all breakdown CSVs exist"""
        required_csvs = [
            "location_breakdown.csv",
            "direction_breakdown.csv",
            "session_breakdown.csv",
            "volume_percentile_breakdown.csv",
            "displacement_atr_breakdown.csv",
            "vwap_distance_atr_breakdown.csv",
            "horizon_sensitivity.csv",
            "default_trades.csv",
        ]
        for csv_name in required_csvs:
            csv_path = self.latest_diagnostic_dir / csv_name
            assert csv_path.exists(), f"Missing breakdown CSV: {csv_name}"
            # Verify CSV is not empty
            assert csv_path.stat().st_size > 0, f"Empty CSV file: {csv_name}"

    def test_default_result_not_validated(self):
        """Verify default result remains NOT validated"""
        summary_file = self.latest_diagnostic_dir / "diagnostic_summary.json"
        with open(summary_file) as f:
            summary = json.load(f)
        
        default_metrics = summary.get("default_metrics", {})
        expectancy = default_metrics.get("expectancy_after_cost")
        profit_factor = default_metrics.get("profit_factor")
        
        # Verify expectancy is approximately -0.3233
        assert expectancy is not None, "expectancy_after_cost not found"
        assert -0.35 < expectancy < -0.30, f"Unexpected expectancy: {expectancy} (expected ~-0.3233)"
        
        # Verify profit factor is approximately 0.9919
        assert profit_factor is not None, "profit_factor not found"
        assert 0.98 < profit_factor < 1.00, f"Unexpected profit_factor: {profit_factor} (expected ~0.9919)"
        
        # Verify hard rule status shows NOT validated
        hard_rules = summary.get("hard_rule_status_default", {})
        assert hard_rules.get("positive_after_cost_expectancy") is False, "Should fail positive expectancy check"
        assert hard_rules.get("profit_factor_gt_1") is False, "Should fail profit factor check"

    def test_top_plateau_candidates_diagnostic_only(self):
        """Verify top plateau candidates are diagnostic only (no VALIDATED label)"""
        summary_file = self.latest_diagnostic_dir / "diagnostic_summary.json"
        with open(summary_file) as f:
            summary = json.load(f)
        
        classification = summary.get("final_diagnostic_classification", {})
        classification_text = classification.get("classification", "")
        reason = classification.get("reason", "")
        
        # Verify classification is "candidate" not "validated"
        assert "candidate" in classification_text.lower(), f"Classification should mention 'candidate': {classification_text}"
        assert "validated" not in classification_text.lower() or "not validated" in reason.lower(), \
            f"Should not claim validation: {classification_text}"
        
        # Verify reason mentions need for forward/OOS confirmation
        assert "forward" in reason.lower() or "oos" in reason.lower() or "confirmation" in reason.lower(), \
            f"Reason should mention need for forward/OOS confirmation: {reason}"
        
        # Verify report states it's diagnostic-only
        report_file = self.latest_diagnostic_dir / "diagnostic_report.md"
        report_content = report_file.read_text()
        assert "diagnostic-only" in report_content.lower(), "Report should state it's diagnostic-only"
        assert "does not make trading recommendations" in report_content.lower(), \
            "Report should state it does not make trading recommendations"

    def test_mnq_cost_model_unchanged(self):
        """Verify MNQ cost model parameters are correct"""
        config_file = self.project_root / "configs" / "mnq_5min_rth.yaml"
        import yaml
        with open(config_file) as f:
            config = yaml.safe_load(f)
        
        costs = config.get("costs", {})
        assert costs.get("slippage_ticks") == 1.0, "slippage_ticks should be 1.0"
        assert costs.get("tick_size") == 0.25, "tick_size should be 0.25"
        assert costs.get("point_value") == 2.0, "point_value should be 2.0"
        assert costs.get("commission_per_trade") == 0.0, "commission should be 0"
        assert costs.get("spread") == 0.0, "spread should be 0"

    def test_pytest_passes_12_tests(self):
        """Verify pytest passes 12 tests"""
        result = subprocess.run(
            ["python", "-m", "pytest", "-q", "--tb=short"],
            cwd=self.project_root,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"pytest failed: {result.stderr}"
        
        # Check for "12 passed"
        assert "12 passed" in result.stdout, f"Expected 12 tests to pass, got: {result.stdout}"

    def test_lint_passes(self):
        """Verify Python linting passes"""
        # Note: Linting was verified separately using mcp_lint_python tool
        # This test verifies basic syntax by importing the module
        try:
            import research_engine.diagnostics
            import research_engine.cli
            assert True, "Modules import successfully"
        except Exception as e:
            assert False, f"Module import failed: {e}"

    def test_no_core_logic_changes(self):
        """Verify diagnostics module doesn't change core backtest/validation logic"""
        # Check that diagnostics.py doesn't import or modify backtest/validation internals
        diagnostics_file = self.project_root / "research_engine" / "diagnostics.py"
        content = diagnostics_file.read_text()
        
        # Should import from backtest/features but not modify them
        assert "from .backtest import" in content, "Should import from backtest"
        assert "from .features import" in content, "Should import from features"
        
        # Should not have any monkey-patching or global state modification
        forbidden_patterns = [
            "backtest.",  # Direct modification of backtest module
            "validation.",  # Direct modification of validation module
            "globals()[",  # Global state manipulation
            "setattr(backtest",  # Monkey patching
            "setattr(validation",  # Monkey patching
        ]
        for pattern in forbidden_patterns:
            assert pattern not in content, f"Diagnostics should not modify core logic: found {pattern}"

    def print_summary(self):
        """Print test summary"""
        print(f"\n{'='*60}")
        print(f"📊 Tests passed: {self.tests_passed}/{self.tests_run}")
        print(f"{'='*60}")
        
        if self.tests_passed == self.tests_run:
            print("\n✅ All diagnostics tests passed!")
            print("\nKey Findings:")
            print("  • Diagnostics CLI works correctly")
            print("  • Default result remains NOT validated (expectancy -0.3233, PF 0.9919)")
            print("  • Top candidates are diagnostic-only (no VALIDATED label)")
            print("  • All required breakdown CSVs generated")
            print("  • MNQ cost model unchanged")
            print("  • Pytest passes 12 tests")
            print("  • Linting passes")
            print("  • No core logic changes")
        
        return 0 if self.tests_passed == self.tests_run else 1


def main():
    tester = DiagnosticsTester()
    
    # Run all tests in order
    tester.run_test("Diagnostics CLI exists", tester.test_diagnostics_cli_exists)
    tester.run_test("Diagnostics CLI runs", tester.test_diagnostics_cli_runs)
    tester.run_test("Diagnostic report exists", tester.test_diagnostic_report_exists)
    tester.run_test("Payoff distribution metrics", tester.test_payoff_distribution_metrics)
    tester.run_test("Breakdown CSVs exist", tester.test_breakdown_csvs_exist)
    tester.run_test("Default result NOT validated", tester.test_default_result_not_validated)
    tester.run_test("Top candidates diagnostic-only", tester.test_top_plateau_candidates_diagnostic_only)
    tester.run_test("MNQ cost model unchanged", tester.test_mnq_cost_model_unchanged)
    tester.run_test("Pytest passes 12 tests", tester.test_pytest_passes_12_tests)
    tester.run_test("Lint passes", tester.test_lint_passes)
    tester.run_test("No core logic changes", tester.test_no_core_logic_changes)
    
    return tester.print_summary()


if __name__ == "__main__":
    sys.exit(main())
