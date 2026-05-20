#!/usr/bin/env python3
"""
Backend test for cross-instrument holdout protocol verification.
Tests RTY, MYM, ES, MCL, MGC holdout results.
"""
import json
import os
import sys
from pathlib import Path
import csv

class CrossInstrumentHoldoutTester:
    def __init__(self):
        self.base_dir = Path("/app/problem_0004_absorption_vwap")
        self.tests_run = 0
        self.tests_passed = 0
        self.errors = []

    def run_test(self, name, test_func):
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
            self.errors.append(f"{name}: {str(e)}")
            return False
        except Exception as e:
            print(f"❌ Error - {str(e)}")
            self.errors.append(f"{name}: {str(e)}")
            return False

    def test_raw_files_exist(self):
        """Verify raw data files exist for all 5 symbols"""
        symbols = ["RTY", "MYM", "ES", "MCL", "MGC"]
        raw_dir = self.base_dir / "data" / "raw"
        
        for symbol in symbols:
            file_path = raw_dir / f"{symbol}_5min_RTH_6year.csv"
            assert file_path.exists(), f"Raw file missing for {symbol}: {file_path}"
            assert file_path.stat().st_size > 0, f"Raw file empty for {symbol}"

    def test_configs_exist_with_correct_mapping(self):
        """Verify per-symbol configs exist with ts_event mapping and correct RTH windows"""
        expected_configs = {
            "rty_5min_rth.yaml": {"symbol": "RTY.v.0", "rth_start": "09:30", "rth_end": "16:00"},
            "mym_5min_rth.yaml": {"symbol": "MYM.v.0", "rth_start": "09:30", "rth_end": "16:00"},
            "es_5min_rth.yaml": {"symbol": "ES.v.0", "rth_start": "09:30", "rth_end": "16:00"},
            "mcl_5min_rth.yaml": {"symbol": "MCL.v.0", "rth_start": "09:00", "rth_end": "14:30"},
            "mgc_5min_rth.yaml": {"symbol": "MGC.v.0", "rth_start": "08:20", "rth_end": "13:30"},
        }
        
        configs_dir = self.base_dir / "configs"
        
        for config_file, expected in expected_configs.items():
            config_path = configs_dir / config_file
            assert config_path.exists(), f"Config missing: {config_file}"
            
            # Read and verify content
            with open(config_path) as f:
                content = f.read()
                assert "timestamp: ts_event" in content, f"{config_file}: Missing ts_event mapping"
                assert f"default_symbol: {expected['symbol']}" in content, f"{config_file}: Wrong symbol"
                assert f'rth_start: "{expected["rth_start"]}"' in content, f"{config_file}: Wrong RTH start"
                assert f'rth_end: "{expected["rth_end"]}"' in content, f"{config_file}: Wrong RTH end"

    def test_holdout_reports_exist(self):
        """Verify holdout reports exist with correct timestamps"""
        expected_reports = [
            "holdout_20260520_151731",  # RTY
            "holdout_20260520_152057",  # MYM
            "holdout_20260520_152416",  # ES
            "holdout_20260520_152618",  # MCL
            "holdout_20260520_152912",  # MGC
        ]
        
        holdout_dir = self.base_dir / "reports" / "holdout"
        
        for report_name in expected_reports:
            report_path = holdout_dir / report_name
            assert report_path.exists(), f"Holdout report missing: {report_name}"
            assert report_path.is_dir(), f"Holdout report not a directory: {report_name}"
            
            # Verify key files exist
            summary_json = report_path / "holdout_summary.json"
            assert summary_json.exists(), f"Missing holdout_summary.json in {report_name}"

    def test_all_symbols_not_validated(self):
        """Verify each symbol's final verdict is NOT_VALIDATED with zero pass count"""
        holdout_reports = {
            "RTY": "holdout_20260520_151731",
            "MYM": "holdout_20260520_152057",
            "ES": "holdout_20260520_152416",
            "MCL": "holdout_20260520_152618",
            "MGC": "holdout_20260520_152912",
        }
        
        holdout_dir = self.base_dir / "reports" / "holdout"
        
        for symbol, report_name in holdout_reports.items():
            summary_path = holdout_dir / report_name / "holdout_summary.json"
            
            with open(summary_path) as f:
                summary = json.load(f)
            
            verdict = summary["final_verdict"]["verdict"]
            assert verdict == "NOT_VALIDATED", f"{symbol}: Expected NOT_VALIDATED, got {verdict}"
            
            reason = summary["final_verdict"]["reason"]
            assert "No frozen training-selected candidate passed all holdout hard gates" in reason, \
                f"{symbol}: Unexpected reason: {reason}"

    def test_cross_instrument_report_exists(self):
        """Verify cross-instrument report exists with all required files"""
        cross_report_dir = self.base_dir / "reports" / "holdout" / "cross_instrument_20260520_152935"
        
        assert cross_report_dir.exists(), "Cross-instrument report directory missing"
        
        required_files = [
            "cross_instrument_all_candidates.csv",
            "cross_instrument_best_summary.csv",
            "cross_instrument_summary.md",
        ]
        
        for file_name in required_files:
            file_path = cross_report_dir / file_name
            assert file_path.exists(), f"Missing file: {file_name}"
            assert file_path.stat().st_size > 0, f"Empty file: {file_name}"

    def test_best_summary_rows_match(self):
        """Verify best-summary rows match expected values"""
        best_summary_path = self.base_dir / "reports" / "holdout" / "cross_instrument_20260520_152935" / "cross_instrument_best_summary.csv"
        
        expected_rows = {
            "RTY": {
                "candidate_id": "default_above_vwap_shorts_only",
                "exit_style": "fixed_horizon",
                "trades": 85,
                "expectancy_after_cost": 43.94,
                "profit_factor": 1.196,
                "final_verdict": "NOT_VALIDATED",
            },
            "MYM": {
                "candidate_id": "default_below_vwap_longs_only",
                "exit_style": "fixed_horizon",
                "trades": 103,
                "expectancy_after_cost": 9.65,
                "profit_factor": 1.359,
                "largest_month_profit_share": 0.5126,  # ~51.26%
                "final_verdict": "NOT_VALIDATED",
            },
            "ES": {
                "candidate_id": "train_plateau_05",
                "exit_style": "target_or_horizon",
                "trades": 57,
                "expectancy_after_cost": 121.22,
                "final_verdict": "NOT_VALIDATED",
            },
            "MCL": {
                "candidate_id": "train_plateau_07",
                "exit_style": "target_or_horizon",
                "trades": 153,
                "expectancy_after_cost": -0.086,
                "final_verdict": "NOT_VALIDATED",
            },
            "MGC": {
                "candidate_id": "default_above_vwap_shorts_only",
                "exit_style": "fixed_horizon",
                "trades": 138,
                "expectancy_after_cost": 18.19,
                "profit_factor": 1.494,
                "lift_pp": 2.90,
                "final_verdict": "NOT_VALIDATED",
            },
        }
        
        with open(best_summary_path) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        assert len(rows) == 5, f"Expected 5 rows, got {len(rows)}"
        
        for row in rows:
            symbol = row["symbol"]
            assert symbol in expected_rows, f"Unexpected symbol: {symbol}"
            
            expected = expected_rows[symbol]
            
            # Verify candidate_id and exit_style
            assert row["candidate_id"] == expected["candidate_id"], \
                f"{symbol}: Expected candidate {expected['candidate_id']}, got {row['candidate_id']}"
            assert row["exit_style"] == expected["exit_style"], \
                f"{symbol}: Expected exit {expected['exit_style']}, got {row['exit_style']}"
            
            # Verify trades
            assert int(row["trades"]) == expected["trades"], \
                f"{symbol}: Expected {expected['trades']} trades, got {row['trades']}"
            
            # Verify expectancy (with tolerance)
            exp_actual = float(row["expectancy_after_cost"])
            exp_expected = expected["expectancy_after_cost"]
            assert abs(exp_actual - exp_expected) < 0.01, \
                f"{symbol}: Expected expectancy ~{exp_expected}, got {exp_actual}"
            
            # Verify profit_factor if specified
            if "profit_factor" in expected:
                pf_actual = float(row["profit_factor"])
                pf_expected = expected["profit_factor"]
                assert abs(pf_actual - pf_expected) < 0.001, \
                    f"{symbol}: Expected PF ~{pf_expected}, got {pf_actual}"
            
            # Verify lift_pp if specified
            if "lift_pp" in expected:
                lift_actual = float(row["lift_pp"])
                lift_expected = expected["lift_pp"]
                assert abs(lift_actual - lift_expected) < 0.01, \
                    f"{symbol}: Expected lift ~{lift_expected}, got {lift_actual}"
            
            # Verify largest_month_profit_share if specified
            if "largest_month_profit_share" in expected:
                conc_actual = float(row["largest_month_profit_share"])
                conc_expected = expected["largest_month_profit_share"]
                assert abs(conc_actual - conc_expected) < 0.01, \
                    f"{symbol}: Expected concentration ~{conc_expected}, got {conc_actual}"
            
            # Verify final verdict
            assert row["final_verdict"] == expected["final_verdict"], \
                f"{symbol}: Expected {expected['final_verdict']}, got {row['final_verdict']}"

    def test_no_live_execution_added(self):
        """Verify no live execution, broker integration, or webhook was added"""
        forbidden_patterns = [
            "broker",
            "webhook",
            "live.*trad",
            "execute.*order",
            "place.*order",
        ]
        
        # Search Python files
        py_files = list(self.base_dir.glob("**/*.py"))
        py_files = [f for f in py_files if "__pycache__" not in str(f) and "venv" not in str(f)]
        
        violations = []
        for py_file in py_files:
            # Skip test files
            if "test" in py_file.name.lower():
                continue
            
            with open(py_file) as f:
                content = f.read().lower()
                
                for pattern in forbidden_patterns:
                    if pattern in content:
                        # Check if it's in a disclaimer/comment
                        if "does not make trading recommendations" in content or \
                           "does not provide live-trading recommendations" in content:
                            continue
                        violations.append(f"{py_file.name}: contains '{pattern}'")
        
        assert len(violations) == 0, f"Found forbidden patterns: {violations}"

    def run_all_tests(self):
        """Run all tests"""
        print("=" * 60)
        print("Cross-Instrument Holdout Protocol Verification")
        print("=" * 60)
        
        self.run_test("Raw files exist for all symbols", self.test_raw_files_exist)
        self.run_test("Configs exist with correct ts_event mapping and RTH windows", 
                     self.test_configs_exist_with_correct_mapping)
        self.run_test("Holdout reports exist with correct timestamps", 
                     self.test_holdout_reports_exist)
        self.run_test("All symbols show NOT_VALIDATED verdict", 
                     self.test_all_symbols_not_validated)
        self.run_test("Cross-instrument report exists with all files", 
                     self.test_cross_instrument_report_exists)
        self.run_test("Best-summary rows match expected values", 
                     self.test_best_summary_rows_match)
        self.run_test("No live execution or broker integration added", 
                     self.test_no_live_execution_added)
        
        # Print summary
        print("\n" + "=" * 60)
        print(f"📊 Tests passed: {self.tests_passed}/{self.tests_run}")
        
        if self.errors:
            print("\n❌ Errors:")
            for error in self.errors:
                print(f"  - {error}")
        
        print("=" * 60)
        
        return 0 if self.tests_passed == self.tests_run else 1

def main():
    tester = CrossInstrumentHoldoutTester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())
