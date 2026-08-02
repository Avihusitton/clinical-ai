# -*- coding: utf-8 -*-
"""
evaluation/wave9/validator.py
Stage A Evaluation-Result Validator for Wave 9.2.
Validates raw fixture results, determinism, stress, overhead, redaction, and taxonomy.
Exits:
  0 = PASS
  1 = evidence present but failed checks
  2 = required evidence missing or invalid
Never falls back to legacy Wave 9 or Wave 9.1 identity files.
"""

import sys
import json
import hashlib
from pathlib import Path
from typing import Dict, Any, List
from .schemas import FROZEN_DIFFERENCE_CLASSES


def compute_sha256(filepath: Path) -> str:
    if not filepath.exists():
        return "MISSING"
    return hashlib.sha256(filepath.read_bytes()).hexdigest()


def run_stage_a_validation(input_dir: Path = Path("tests")) -> Dict[str, Any]:
    fix_results_path = input_dir / "WAVE_9_FIXTURE_RESULTS.jsonl"
    det_results_path = input_dir / "WAVE_9_DETERMINISM_RESULTS.json"
    stress_results_path = input_dir / "WAVE_9_STRESS_RESULTS.json"
    overhead_results_path = input_dir / "WAVE_9_OVERHEAD_RESULTS.json"
    redaction_results_path = input_dir / "WAVE_9_REDACTION_RESULTS.json"

    required_paths = [fix_results_path, det_results_path, stress_results_path, overhead_results_path, redaction_results_path]
    for p in required_paths:
        if not p.exists():
            res = {
                "stage_a_validator_exit_code": 2,
                "validator_result": "FAIL",
                "error": f"Required evidence file missing: {p.name}",
                "failed_checks": [f"missing_{p.name}"]
            }
            out_p = input_dir / "WAVE_9_EVALUATION_VALIDATION.json"
            out_p.write_text(json.dumps(res, indent=2), encoding="utf-8")
            return res

    failed_checks = []

    # 1. Parse fixture results JSONL
    fixture_records: List[Dict[str, Any]] = []
    try:
        with open(fix_results_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    fixture_records.append(json.loads(line))
    except Exception as e:
        res = {
            "stage_a_validator_exit_code": 2,
            "validator_result": "FAIL",
            "error": f"Fixture results file malformed: {e}",
            "failed_checks": ["fixture_results_malformed"]
        }
        (input_dir / "WAVE_9_EVALUATION_VALIDATION.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
        return res

    fixture_ids = [r.get("case_id") for r in fixture_records]
    distinct_fixture_ids = list(set(fixture_ids))

    if len(fixture_records) != 140 or len(distinct_fixture_ids) != 140:
        failed_checks.append("fixture_count_not_140_distinct")

    exact_matches = sum(1 for r in fixture_records if r.get("exact_legacy_match") is True)
    if exact_matches != 140:
        failed_checks.append("exact_legacy_matches_not_140")

    user_visible_leaks = sum(
        1 for r in fixture_records
        if r.get("user_visible_result_fingerprint") != r.get("legacy_result_fingerprint") and r.get("exact_legacy_match") is False
    )
    if user_visible_leaks > 0:
        failed_checks.append("user_visible_shadow_output_detected")

    raw_query_leaks = sum(1 for r in fixture_records if r.get("raw_query_leak_detected") is True)
    if raw_query_leaks > 0:
        failed_checks.append("raw_query_leak_detected")

    # Check Difference Class Taxonomy (MUST be in FROZEN_DIFFERENCE_CLASSES)
    for r in fixture_records:
        dc = r.get("difference_class")
        if not dc or dc not in FROZEN_DIFFERENCE_CLASSES:
            if "non_contract_difference_class_inserted" not in failed_checks:
                failed_checks.append("non_contract_difference_class_inserted")

    # 2. Parse Determinism Results
    try:
        det_data = json.loads(det_results_path.read_text(encoding="utf-8"))
        runs_executed = det_data.get("runs_executed", 0)
        det_outcomes = det_data.get("deterministic_fixture_outcomes", 0)
        all_runs_identical = det_data.get("all_runs_identical", False)

        if runs_executed != 3 or det_outcomes != 140 or not all_runs_identical:
            failed_checks.append("determinism_not_140_across_3_runs")
    except Exception:
        res = {
            "stage_a_validator_exit_code": 2,
            "validator_result": "FAIL",
            "error": "Determinism results file malformed",
            "failed_checks": ["determinism_results_malformed"]
        }
        (input_dir / "WAVE_9_EVALUATION_VALIDATION.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
        return res

    # 3. Parse Stress Results
    try:
        stress_data = json.loads(stress_results_path.read_text(encoding="utf-8"))
        if not isinstance(stress_data, list) or len(stress_data) < 9:
            failed_checks.append("stress_profiles_incomplete")
        else:
            req_waits = sum(s.get("request_thread_waits", 0) for s in stress_data)
            retries = sum(s.get("retry_count", 0) for s in stress_data)
            if req_waits > 0:
                failed_checks.append("request_thread_waits_non_zero")
            if retries > 0:
                failed_checks.append("retry_counts_non_zero")
    except Exception:
        res = {
            "stage_a_validator_exit_code": 2,
            "validator_result": "FAIL",
            "error": "Stress results file malformed",
            "failed_checks": ["stress_results_malformed"]
        }
        (input_dir / "WAVE_9_EVALUATION_VALIDATION.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
        return res

    # 4. Parse Overhead Results
    try:
        overhead_data = json.loads(overhead_results_path.read_text(encoding="utf-8"))
        for item in overhead_data:
            if "incremental_median_ns" not in item or "incremental_p95_ns" not in item:
                if "incremental_overhead_field_missing" not in failed_checks:
                    failed_checks.append("incremental_overhead_field_missing")
    except Exception:
        res = {
            "stage_a_validator_exit_code": 2,
            "validator_result": "FAIL",
            "error": "Overhead results file malformed",
            "failed_checks": ["overhead_results_malformed"]
        }
        (input_dir / "WAVE_9_EVALUATION_VALIDATION.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
        return res

    # 5. Parse Redaction Results
    try:
        redaction_data = json.loads(redaction_results_path.read_text(encoding="utf-8"))
        pii_cases_queued = redaction_data.get("israeli_pii_cases_queued", -1)
        pii_cases_eval = redaction_data.get("israeli_pii_cases_evaluated", 0)

        if pii_cases_eval != 20 or pii_cases_queued != 0:
            failed_checks.append("israeli_pii_rejection_invalid")
    except Exception:
        res = {
            "stage_a_validator_exit_code": 2,
            "validator_result": "FAIL",
            "error": "Redaction results file malformed",
            "failed_checks": ["redaction_results_malformed"]
        }
        (input_dir / "WAVE_9_EVALUATION_VALIDATION.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
        return res

    exit_code = 0 if len(failed_checks) == 0 else 1
    validator_result = "PASS" if exit_code == 0 else "FAIL"

    summary_report = {
        "stage_a_validator_exit_code": exit_code,
        "validator_source_sha256": compute_sha256(Path(__file__)),
        "fixtures_validated": len(fixture_records),
        "distinct_fixture_ids": len(distinct_fixture_ids),
        "exact_legacy_matches": exact_matches,
        "raw_query_leaks": raw_query_leaks,
        "determinism_runs": runs_executed,
        "deterministic_outcomes": det_outcomes,
        "israeli_pii_cases_queued": pii_cases_queued,
        "failed_checks": failed_checks,
        "validator_result": validator_result
    }

    out_p = input_dir / "WAVE_9_EVALUATION_VALIDATION.json"
    out_p.write_text(json.dumps(summary_report, indent=2), encoding="utf-8")
    return summary_report


if __name__ == "__main__":
    rep = run_stage_a_validation()
    ecode = rep.get("stage_a_validator_exit_code", 1)
    print(f"Stage A Validator finished with exit code {ecode} ({rep.get('validator_result')})")
    sys.exit(ecode)
