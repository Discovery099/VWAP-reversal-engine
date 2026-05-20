#!/usr/bin/env python3
"""
Backend test for recent-regime analysis feature
Tests all requirements from the review request
"""

import sys
from pathlib import Path
import pandas as pd
import subprocess

class RecentRegimeBackendTest:
    def __init__(self):
        self.root = Path("/app/problem_0004_absorption_vwap")
        self.reports_dir = self.root / "reports" / "recent_regime"
        self.tests_passed = 0
        self.tests_failed = 0
        self.failures = []

    def log_pass(self, test_name: str):
        """Log a passing test"""
        self.tests_passed += 1
        print(f"✅ PASS: {test_name}")

    def log_fail(self, test_name: str, reason: str):
        """Log a failing test"""
        self.tests_failed += 1
        self.failures.append(f"{test_name}: {reason}")
        print(f"❌ FAIL: {test_name}")
        print(f"   Reason: {reason}")

    def test_cli_command(self):
        """Test 1: Verify CLI command works"""
        try:
            result = subprocess.run(
                ["python", "-m", "research_engine", "recent-regime"],
                cwd=self.root,
                capture_output=True,
                text=True,
                timeout=300
            )
            if result.returncode == 0 and "run_dir=reports/recent_regime" in result.stdout:
                self.log_pass("CLI command 'python -m research_engine recent-regime' works")
            else:
                self.log_fail("CLI command", f"Exit code: {result.returncode}, stdout: {result.stdout[:200]}")
        except Exception as e:
            self.log_fail("CLI command", str(e))

    def test_output_files_exist(self):
        """Test 2: Verify all output files exist"""
        expected_files = [
            "recent_regime_all_results.csv",
            "recent_regime_summary.csv",
            "recent_regime_summary.md",
            "recent_regime_summary.html"
        ]
        
        for filename in expected_files:
            filepath = self.reports_dir / filename
            if filepath.exists():
                self.log_pass(f"Output file exists: {filename}")
            else:
                self.log_fail(f"Output file exists: {filename}", "File not found")

    def test_latest_html_exists(self):
        """Test 3: Verify reports/latest.html exists and links to recent_regime"""
        latest_html = self.root / "reports" / "latest.html"
        if latest_html.exists():
            content = latest_html.read_text()
            if "recent_regime/recent_regime_summary.html" in content:
                self.log_pass("reports/latest.html exists and links to recent_regime_summary.html")
            else:
                self.log_fail("reports/latest.html links", "Link to recent_regime_summary.html not found")
        else:
            self.log_fail("reports/latest.html exists", "File not found")

    def test_all_results_row_count(self):
        """Test 4: Verify all_results has 36 rows (9 symbols x 4 windows)"""
        try:
            df = pd.read_csv(self.reports_dir / "recent_regime_all_results.csv")
            if len(df) == 36:
                self.log_pass("all_results.csv has 36 rows (9 symbols x 4 windows)")
            else:
                self.log_fail("all_results row count", f"Expected 36 rows, got {len(df)}")
        except Exception as e:
            self.log_fail("all_results row count", str(e))

    def test_symbol_availability(self):
        """Test 5: Verify available vs unavailable symbols"""
        try:
            df = pd.read_csv(self.reports_dir / "recent_regime_all_results.csv")
            
            # Available symbols (should have data)
            available_symbols = ["MNQ", "RTY", "MYM", "ES", "MCL", "MGC"]
            for symbol in available_symbols:
                symbol_data = df[df["symbol"] == symbol]
                has_data = symbol_data["bars_loaded"].sum() > 0
                if has_data:
                    self.log_pass(f"Symbol {symbol} has data (available)")
                else:
                    self.log_fail(f"Symbol {symbol} availability", "Expected data but found none")
            
            # Unavailable symbols (should be marked as not available)
            unavailable_symbols = ["MES", "M2K", "GC"]
            for symbol in unavailable_symbols:
                symbol_data = df[df["symbol"] == symbol]
                all_unavailable = symbol_data["comments_failure_reason"].str.contains("not available").all()
                if all_unavailable:
                    self.log_pass(f"Symbol {symbol} marked as not available")
                else:
                    self.log_fail(f"Symbol {symbol} unavailability", "Expected 'not available' marker")
        except Exception as e:
            self.log_fail("symbol availability", str(e))

    def test_label_distribution(self):
        """Test 6: Verify label counts (26 INSUFFICIENT_RECENT_DATA, 10 WARNING_ONLY)"""
        try:
            df = pd.read_csv(self.reports_dir / "recent_regime_all_results.csv")
            label_counts = df["recent_regime_label"].value_counts().to_dict()
            
            insufficient_count = label_counts.get("INSUFFICIENT_RECENT_DATA", 0)
            warning_count = label_counts.get("WARNING_ONLY", 0)
            active_count = label_counts.get("RECENT_REGIME_ACTIVE", 0)
            weak_count = label_counts.get("RECENT_REGIME_WEAK", 0)
            inactive_count = label_counts.get("RECENT_REGIME_INACTIVE", 0)
            
            if insufficient_count == 26:
                self.log_pass("Label count: 26 INSUFFICIENT_RECENT_DATA")
            else:
                self.log_fail("INSUFFICIENT_RECENT_DATA count", f"Expected 26, got {insufficient_count}")
            
            if warning_count == 10:
                self.log_pass("Label count: 10 WARNING_ONLY")
            else:
                self.log_fail("WARNING_ONLY count", f"Expected 10, got {warning_count}")
            
            if active_count == 0:
                self.log_pass("Label count: 0 RECENT_REGIME_ACTIVE (as expected)")
            else:
                self.log_fail("RECENT_REGIME_ACTIVE count", f"Expected 0, got {active_count}")
            
            if weak_count == 0:
                self.log_pass("Label count: 0 RECENT_REGIME_WEAK (as expected)")
            else:
                self.log_fail("RECENT_REGIME_WEAK count", f"Expected 0, got {weak_count}")
            
            if inactive_count == 0:
                self.log_pass("Label count: 0 RECENT_REGIME_INACTIVE (as expected)")
            else:
                self.log_fail("RECENT_REGIME_INACTIVE count", f"Expected 0, got {inactive_count}")
        except Exception as e:
            self.log_fail("label distribution", str(e))

    def test_no_validation_language(self):
        """Test 7: Verify no VALIDATED labels and global verdict not changed"""
        try:
            # Check markdown file
            md_content = (self.reports_dir / "recent_regime_summary.md").read_text()
            if "NOT_VALIDATED" in md_content and "not full validation" in md_content:
                self.log_pass("Markdown confirms NOT_VALIDATED status maintained")
            else:
                self.log_fail("Validation language", "Expected NOT_VALIDATED confirmation in markdown")
            
            # Check latest.html
            latest_content = (self.root / "reports" / "latest.html").read_text()
            if "NOT_VALIDATED" in latest_content:
                self.log_pass("latest.html confirms NOT_VALIDATED status")
            else:
                self.log_fail("latest.html validation", "Expected NOT_VALIDATED in latest.html")
            
            # Verify no VALIDATED labels in all_results
            df = pd.read_csv(self.reports_dir / "recent_regime_all_results.csv")
            validated_labels = df[df["recent_regime_label"].str.contains("VALIDATED", na=False)]
            if len(validated_labels) == 0:
                self.log_pass("No VALIDATED labels in recent-regime results")
            else:
                self.log_fail("VALIDATED labels", f"Found {len(validated_labels)} VALIDATED labels")
        except Exception as e:
            self.log_fail("validation language check", str(e))

    def test_pytest_passes(self):
        """Test 8: Verify pytest passes with 17 tests"""
        try:
            result = subprocess.run(
                ["python", "-m", "pytest", "tests/", "-v", "--tb=short"],
                cwd=self.root,
                capture_output=True,
                text=True,
                timeout=60
            )
            if "17 passed" in result.stdout:
                self.log_pass("Pytest passes with 17 tests")
            else:
                self.log_fail("Pytest", f"Expected '17 passed', output: {result.stdout[-500:]}")
        except Exception as e:
            self.log_fail("Pytest", str(e))

    def test_no_live_execution_files(self):
        """Test 9: Verify no live execution/trading/UI files added"""
        forbidden_patterns = ["broker", "webhook", "trading", "dashboard", "live_execution"]
        
        for pattern in forbidden_patterns:
            matching_files = list(self.root.rglob(f"*{pattern}*.py"))
            if len(matching_files) == 0:
                self.log_pass(f"No {pattern} files found (as expected)")
            else:
                self.log_fail(f"No {pattern} files", f"Found: {[str(f) for f in matching_files]}")

    def run_all_tests(self):
        """Run all tests and print summary"""
        print("=" * 80)
        print("RECENT-REGIME BACKEND TEST SUITE")
        print("=" * 80)
        print()
        
        self.test_cli_command()
        self.test_output_files_exist()
        self.test_latest_html_exists()
        self.test_all_results_row_count()
        self.test_symbol_availability()
        self.test_label_distribution()
        self.test_no_validation_language()
        self.test_pytest_passes()
        self.test_no_live_execution_files()
        
        print()
        print("=" * 80)
        print(f"TEST SUMMARY: {self.tests_passed} passed, {self.tests_failed} failed")
        print("=" * 80)
        
        if self.tests_failed > 0:
            print("\nFAILURES:")
            for failure in self.failures:
                print(f"  - {failure}")
            return 1
        else:
            print("\n✅ ALL TESTS PASSED!")
            return 0

def main():
    tester = RecentRegimeBackendTest()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())
