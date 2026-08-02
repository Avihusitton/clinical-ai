# -*- coding: utf-8 -*-
"""
evaluation/wave9/source_attestation.py
Mechanically discovers, hashes, and validates exact source code inventory for Wave 9.4R.
Supports --validate CLI command for Stage B attestation validation.
"""

import os
import sys
import json
import hashlib
import argparse
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Tuple


def get_expected_source_inventory() -> List[Dict[str, Any]]:
    root_dir = Path(__file__).resolve().parent.parent.parent
    paths: List[Path] = []

    scan_dirs = [
        root_dir / "evaluation" / "wave9",
        root_dir / "shadow_wiring",
        root_dir / "controlled_integration"
    ]

    for sdir in scan_dirs:
        if sdir.exists():
            for p in sdir.rglob("*"):
                if p.is_file():
                    rel_p = str(p.relative_to(root_dir)).replace("\\", "/")
                    if "__pycache__" in rel_p or rel_p.endswith(".pyc") or rel_p.endswith(".pyo"):
                        continue
                    if "scratch" in rel_p or rel_p.endswith(".tmp"):
                        continue
                    paths.append(p)

    single_files = [
        root_dir / "retrieval.py",
        root_dir / "tests" / "fixtures" / "shadow_wiring" / "shadow_cases.jsonl",
        root_dir / "tests" / "fixtures" / "shadow_wiring" / "redaction_negative_cases.jsonl"
    ]

    for sf in single_files:
        if sf.exists():
            paths.append(sf)

    paths = sorted(list(set(paths)), key=lambda p: str(p.relative_to(root_dir)).replace("\\", "/"))

    inventory = []
    for p in paths:
        rel_path = str(p.relative_to(root_dir)).replace("\\", "/")
        bdata = p.read_bytes()
        inventory.append({
            "normalized_path": rel_path,
            "byte_length": len(bdata),
            "sha256": hashlib.sha256(bdata).hexdigest()
        })
    return inventory


def validate_attestation(input_dir: Path = Path("tests")) -> Dict[str, Any]:
    """Validate the Wave 9.4R attestation evidence.

    Args:
        input_dir: Directory containing WAVE_9_4R_* evidence files.
                   Defaults to 'tests/' for production, but can be overridden
                   for isolated test environments.
    """
    input_dir = Path(input_dir)

    attest_path = input_dir / "WAVE_9_4R_EXECUTION_ATTESTATION.json"
    gate_identity_path = input_dir / "WAVE_9_4R_BASELINE_TEST_IDENTITY.json"
    attestation_validation_path = input_dir / "WAVE_9_4R_ATTESTATION_VALIDATION.json"

    # Check for prohibited test environment contamination files
    root_dir = input_dir.parent
    pytest_ini_path = root_dir / "pytest.ini"
    root_conftest_path = root_dir / "conftest.py"

    failed_checks = []

    if pytest_ini_path.exists():
        failed_checks.append("pytest_ini_present")
    if root_conftest_path.exists():
        failed_checks.append("root_conftest_present")

    if not attest_path.exists():
        res = {
            "attestation_validator_exit_code": 2,
            "validator_result": "FAIL",
            "error": "Required attestation file missing: WAVE_9_4R_EXECUTION_ATTESTATION.json",
            "failed_checks": ["attestation_file_missing"] + failed_checks
        }
        attestation_validation_path.write_text(json.dumps(res, indent=2), encoding="utf-8")
        return res

    try:
        attest_data = json.loads(attest_path.read_text(encoding="utf-8"))
    except Exception as e:
        res = {
            "attestation_validator_exit_code": 2,
            "validator_result": "FAIL",
            "error": f"Attestation file malformed: {e}",
            "failed_checks": ["attestation_file_malformed"] + failed_checks
        }
        attestation_validation_path.write_text(json.dumps(res, indent=2), encoding="utf-8")
        return res

    # 1. Timestamps — runtime UTC start and finish
    start_ts = attest_data.get("execution_started_at_utc")
    finish_ts = attest_data.get("execution_finished_at_utc")

    if not start_ts or not isinstance(start_ts, str):
        failed_checks.append("execution_start_timestamp_missing")
    if not finish_ts or not isinstance(finish_ts, str):
        failed_checks.append("execution_finish_timestamp_missing")

    # 2. Subprocess exit codes — actual subprocess exit codes
    eval_code = attest_data.get("evaluation_exit_code")
    stress_code = attest_data.get("stress_exit_code")
    val_code = attest_data.get("validator_exit_code")

    if eval_code != 0:
        failed_checks.append("evaluation_exit_code_nonzero")
    if stress_code != 0:
        failed_checks.append("stress_exit_code_nonzero")
    if val_code != 0:
        failed_checks.append("validator_exit_code_nonzero")

    # 3. Source inventory coverage & exact expected/before/after source-path equality
    expected_inv = get_expected_source_inventory()
    expected_paths = sorted([item["normalized_path"] for item in expected_inv])
    expected_map = {item["normalized_path"]: item["sha256"] for item in expected_inv}

    before_paths = attest_data.get("source_paths_before", [])
    after_paths = attest_data.get("source_paths_after", [])

    before_hashes = attest_data.get("source_hashes_before", {})
    after_hashes = attest_data.get("source_hashes_after", {})

    # Exact expected/before/after source-path equality
    missing_from_before = sorted(list(set(expected_paths) - set(before_paths)))
    unexpected_in_before = sorted(list(set(before_paths) - set(expected_paths)))

    missing_from_after = sorted(list(set(expected_paths) - set(after_paths)))
    unexpected_in_after = sorted(list(set(after_paths) - set(expected_paths)))

    expected_equals_before = (set(expected_paths) == set(before_paths))
    expected_equals_after = (set(expected_paths) == set(after_paths))
    before_equals_after = (set(before_paths) == set(after_paths))

    if not expected_equals_before or not expected_equals_after or not before_equals_after:
        failed_checks.append("source_inventory_set_inequality")

    if len(expected_paths) != len(before_paths) or len(before_paths) != len(after_paths):
        failed_checks.append("source_inventory_count_mismatch")

    # Count breakdown
    eval_wave9_count = sum(1 for p in before_paths if p.startswith("evaluation/wave9/"))
    shadow_wiring_count = sum(1 for p in before_paths if p.startswith("shadow_wiring/"))
    controlled_integration_count = sum(1 for p in before_paths if p.startswith("controlled_integration/"))
    other_count = len(before_paths) - (eval_wave9_count + shadow_wiring_count + controlled_integration_count)

    # 4. Exact before/after hash equality — independent recalculation
    calc_unchanged = (before_paths == after_paths and before_hashes == after_hashes and before_hashes == expected_map)

    if not calc_unchanged or attest_data.get("source_unchanged_during_evaluation") is not True:
        failed_checks.append("source_hashes_changed_during_evaluation")

    added_during = attest_data.get("added_during_execution", [])
    missing_after = attest_data.get("missing_after_execution", [])
    modified_during = attest_data.get("modified_during_execution", [])

    if added_during or missing_after or modified_during:
        failed_checks.append("unexpected_file_modifications_during_execution")

    # 5. Raw stdout and stderr hashes — verify WAVE_9_4R_ files
    raw_files = [
        ("evaluation_stdout", input_dir / "WAVE_9_4R_EVALUATION_STDOUT.txt", attest_data.get("evaluation_stdout_sha256")),
        ("evaluation_stderr", input_dir / "WAVE_9_4R_EVALUATION_STDERR.txt", attest_data.get("evaluation_stderr_sha256")),
        ("stress_stdout", input_dir / "WAVE_9_4R_STRESS_STDOUT.txt", attest_data.get("stress_stdout_sha256")),
        ("stress_stderr", input_dir / "WAVE_9_4R_STRESS_STDERR.txt", attest_data.get("stress_stderr_sha256")),
        ("validator_stdout", input_dir / "WAVE_9_4R_VALIDATOR_STDOUT.txt", attest_data.get("validator_stdout_sha256")),
        ("validator_stderr", input_dir / "WAVE_9_4R_VALIDATOR_STDERR.txt", attest_data.get("validator_stderr_sha256")),
    ]

    for label, rpath, exp_sha in raw_files:
        if not rpath.exists():
            failed_checks.append(f"raw_output_missing_{label}")
        else:
            act_sha = hashlib.sha256(rpath.read_bytes()).hexdigest()
            if act_sha != exp_sha:
                failed_checks.append(f"raw_output_sha256_mismatch_{label}")

    # 6. Baseline test identity verification
    hex64_pattern = re.compile(r"^[a-fA-F0-9]{64}$")
    if not gate_identity_path.exists():
        failed_checks.append("baseline_test_identity_missing")
    else:
        try:
            bt_data = json.loads(gate_identity_path.read_text(encoding="utf-8"))
            if isinstance(bt_data, list):
                if len(bt_data) == 0:
                    failed_checks.append("baseline_test_identity_mismatched")
                for entry in bt_data:
                    if not isinstance(entry, dict):
                        failed_checks.append("baseline_test_identity_mismatched")
                        break
                    if entry.get("baseline_extraction_success") is not True:
                        failed_checks.append("baseline_test_identity_mismatched")
                    if entry.get("match") is not True:
                        failed_checks.append("baseline_test_identity_mismatched")
                    if entry.get("working_file_used_as_baseline") is not False:
                        failed_checks.append("baseline_test_identity_mismatched")

                    b_sha = entry.get("baseline_sha256")
                    w_sha = entry.get("working_sha256")
                    if not b_sha or not isinstance(b_sha, str) or not hex64_pattern.match(b_sha):
                        failed_checks.append("baseline_test_identity_mismatched")
                    if not w_sha or not isinstance(w_sha, str) or not hex64_pattern.match(w_sha):
                        failed_checks.append("baseline_test_identity_mismatched")

                    b_len = entry.get("baseline_byte_length", 0)
                    w_len = entry.get("working_byte_length", 0)
                    if not isinstance(b_len, int) or b_len <= 0:
                        failed_checks.append("baseline_test_identity_mismatched")
                    if not isinstance(w_len, int) or w_len <= 0:
                        failed_checks.append("baseline_test_identity_mismatched")

                    comp_type = entry.get("comparison_type")
                    if comp_type == "EXACT_BYTE_MATCH":
                        if b_sha != w_sha or b_len != w_len:
                            failed_checks.append("baseline_test_identity_mismatched")
                    elif comp_type == "NORMALIZED_TEXT_MATCH":
                        bn_sha = entry.get("baseline_normalized_sha256")
                        wn_sha = entry.get("working_normalized_sha256")
                        if not bn_sha or not isinstance(bn_sha, str) or not hex64_pattern.match(bn_sha):
                            failed_checks.append("baseline_test_identity_mismatched")
                        if not wn_sha or not isinstance(wn_sha, str) or not hex64_pattern.match(wn_sha):
                            failed_checks.append("baseline_test_identity_mismatched")
                        if bn_sha != wn_sha:
                            failed_checks.append("baseline_test_identity_mismatched")
                    else:
                        failed_checks.append("baseline_test_identity_mismatched")
            else:
                failed_checks.append("baseline_test_identity_mismatched")
        except Exception:
            failed_checks.append("baseline_test_identity_malformed")

    exit_code = 0 if len(failed_checks) == 0 else 1
    val_result = "PASS" if exit_code == 0 else "FAIL"

    summary = {
        "attestation_validator_exit_code": exit_code,
        "validator_result": val_result,
        "expected_source_path_count": len(expected_paths),
        "attested_source_path_count_before": len(before_paths),
        "attested_source_path_count_after": len(after_paths),
        "expected_equals_before": expected_equals_before,
        "expected_equals_after": expected_equals_after,
        "before_equals_after": before_equals_after,
        "missing_from_before": missing_from_before,
        "unexpected_in_before": unexpected_in_before,
        "missing_from_after": missing_from_after,
        "unexpected_in_after": unexpected_in_after,
        "evaluation_wave9_file_count": eval_wave9_count,
        "shadow_wiring_file_count": shadow_wiring_count,
        "controlled_integration_file_count": controlled_integration_count,
        "other_required_file_count": other_count,
        "total_source_file_count": len(before_paths),
        "source_unchanged_verified": calc_unchanged,
        "failed_checks": failed_checks
    }

    attestation_validation_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate", action="store_true", help="Run Stage B attestation validation")
    args = parser.parse_args()

    if args.validate:
        res = validate_attestation()
        ecode = res.get("attestation_validator_exit_code", 1)
        print(f"Stage B Attestation Validator finished with exit code {ecode} ({res.get('validator_result')})")
        sys.exit(ecode)
    else:
        inv = get_expected_source_inventory()
        print(json.dumps(inv, indent=2))
