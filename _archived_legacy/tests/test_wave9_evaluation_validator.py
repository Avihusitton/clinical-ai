# -*- coding: utf-8 -*-
"""
tests/test_wave9_evaluation_validator.py
Mutation test suite for Stage A evaluation validator in Wave 9.2.
Executes real validator logic against mutated temporary evidence files.
"""

import json
import shutil
from pathlib import Path
import pytest

from evaluation.wave9.validator import run_stage_a_validation


@pytest.fixture
def temp_wave9_dir(tmp_path):
    src_dir = Path("tests")
    files_to_copy = [
        "WAVE_9_FIXTURE_RESULTS.jsonl",
        "WAVE_9_DETERMINISM_RESULTS.json",
        "WAVE_9_STRESS_RESULTS.json",
        "WAVE_9_OVERHEAD_RESULTS.json",
        "WAVE_9_REDACTION_RESULTS.json"
    ]
    for f in files_to_copy:
        src_f = src_dir / f
        if src_f.exists():
            shutil.copy(src_f, tmp_path / f)
    return tmp_path


def test_validator_passes_on_clean_wave9_evidence(temp_wave9_dir):
    res = run_stage_a_validation(input_dir=temp_wave9_dir)
    assert res["stage_a_validator_exit_code"] == 0
    assert res["validator_result"] == "PASS"
    assert len(res["failed_checks"]) == 0


def test_validator_fails_when_one_fixture_removed(temp_wave9_dir):
    p = temp_wave9_dir / "WAVE_9_FIXTURE_RESULTS.jsonl"
    lines = [line for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]
    lines.pop()
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")

    res = run_stage_a_validation(input_dir=temp_wave9_dir)
    assert res["stage_a_validator_exit_code"] == 1
    assert res["validator_result"] == "FAIL"
    assert "fixture_count_not_140_distinct" in res["failed_checks"]


def test_validator_fails_when_one_fixture_id_duplicated(temp_wave9_dir):
    p = temp_wave9_dir / "WAVE_9_FIXTURE_RESULTS.jsonl"
    lines = [line for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(lines) >= 2:
        item0 = json.loads(lines[0])
        item1 = json.loads(lines[1])
        item1["case_id"] = item0["case_id"]
        lines[1] = json.dumps(item1)
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")

    res = run_stage_a_validation(input_dir=temp_wave9_dir)
    assert res["stage_a_validator_exit_code"] == 1
    assert res["validator_result"] == "FAIL"
    assert "fixture_count_not_140_distinct" in res["failed_checks"]


def test_validator_fails_when_one_legacy_result_differs(temp_wave9_dir):
    p = temp_wave9_dir / "WAVE_9_FIXTURE_RESULTS.jsonl"
    lines = [line for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]
    if lines:
        item = json.loads(lines[0])
        item["exact_legacy_match"] = False
        lines[0] = json.dumps(item)
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")

    res = run_stage_a_validation(input_dir=temp_wave9_dir)
    assert res["stage_a_validator_exit_code"] == 1
    assert res["validator_result"] == "FAIL"
    assert "exact_legacy_matches_not_140" in res["failed_checks"]


def test_validator_fails_when_one_shadow_output_user_visible(temp_wave9_dir):
    p = temp_wave9_dir / "WAVE_9_FIXTURE_RESULTS.jsonl"
    lines = [line for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]
    if lines:
        item = json.loads(lines[0])
        item["user_visible_result_fingerprint"] = "MUTATED_SHADOW_FINGERPRINT"
        item["exact_legacy_match"] = False
        lines[0] = json.dumps(item)
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")

    res = run_stage_a_validation(input_dir=temp_wave9_dir)
    assert res["stage_a_validator_exit_code"] == 1
    assert res["validator_result"] == "FAIL"
    assert "user_visible_shadow_output_detected" in res["failed_checks"]


def test_validator_fails_when_raw_query_leak_inserted(temp_wave9_dir):
    p = temp_wave9_dir / "WAVE_9_FIXTURE_RESULTS.jsonl"
    lines = [line for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]
    if lines:
        item = json.loads(lines[0])
        item["raw_query_leak_detected"] = True
        lines[0] = json.dumps(item)
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")

    res = run_stage_a_validation(input_dir=temp_wave9_dir)
    assert res["stage_a_validator_exit_code"] == 1
    assert res["validator_result"] == "FAIL"
    assert "raw_query_leak_detected" in res["failed_checks"]


def test_validator_fails_when_israeli_pii_case_queued(temp_wave9_dir):
    p = temp_wave9_dir / "WAVE_9_REDACTION_RESULTS.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    data["israeli_pii_cases_queued"] = 1
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")

    res = run_stage_a_validation(input_dir=temp_wave9_dir)
    assert res["stage_a_validator_exit_code"] == 1
    assert res["validator_result"] == "FAIL"
    assert "israeli_pii_rejection_invalid" in res["failed_checks"]


def test_validator_fails_when_determinism_outcome_mismatched(temp_wave9_dir):
    p = temp_wave9_dir / "WAVE_9_DETERMINISM_RESULTS.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    data["deterministic_fixture_outcomes"] = 139
    data["all_runs_identical"] = False
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")

    res = run_stage_a_validation(input_dir=temp_wave9_dir)
    assert res["stage_a_validator_exit_code"] == 1
    assert res["validator_result"] == "FAIL"
    assert "determinism_not_140_across_3_runs" in res["failed_checks"]


def test_validator_fails_when_request_thread_wait_inserted(temp_wave9_dir):
    p = temp_wave9_dir / "WAVE_9_STRESS_RESULTS.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    if data:
        data[0]["request_thread_waits"] = 1
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")

    res = run_stage_a_validation(input_dir=temp_wave9_dir)
    assert res["stage_a_validator_exit_code"] == 1
    assert res["validator_result"] == "FAIL"
    assert "request_thread_waits_non_zero" in res["failed_checks"]


def test_validator_fails_when_non_contract_difference_class_inserted(temp_wave9_dir):
    p = temp_wave9_dir / "WAVE_9_FIXTURE_RESULTS.jsonl"
    lines = [line for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]
    if lines:
        item = json.loads(lines[0])
        item["difference_class"] = "EMERGENCY_DISABLED"
        lines[0] = json.dumps(item)
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")

    res = run_stage_a_validation(input_dir=temp_wave9_dir)
    assert res["stage_a_validator_exit_code"] == 1
    assert res["validator_result"] == "FAIL"
    assert "non_contract_difference_class_inserted" in res["failed_checks"]


def test_validator_fails_when_operating_mode_inserted_into_difference_class(temp_wave9_dir):
    p = temp_wave9_dir / "WAVE_9_FIXTURE_RESULTS.jsonl"
    lines = [line for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]
    if lines:
        item = json.loads(lines[0])
        item["difference_class"] = "SHADOW_COMPARE"
        lines[0] = json.dumps(item)
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")

    res = run_stage_a_validation(input_dir=temp_wave9_dir)
    assert res["stage_a_validator_exit_code"] == 1
    assert res["validator_result"] == "FAIL"
    assert "non_contract_difference_class_inserted" in res["failed_checks"]


def test_validator_fails_when_incremental_overhead_field_missing(temp_wave9_dir):
    p = temp_wave9_dir / "WAVE_9_OVERHEAD_RESULTS.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    if data:
        data[0].pop("incremental_median_ns", None)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")

    res = run_stage_a_validation(input_dir=temp_wave9_dir)
    assert res["stage_a_validator_exit_code"] == 1
    assert res["validator_result"] == "FAIL"
    assert "incremental_overhead_field_missing" in res["failed_checks"]


def test_validator_fails_code_2_when_required_file_missing(temp_wave9_dir):
    p = temp_wave9_dir / "WAVE_9_FIXTURE_RESULTS.jsonl"
    if p.exists():
        p.unlink()

    res = run_stage_a_validation(input_dir=temp_wave9_dir)
    assert res["stage_a_validator_exit_code"] == 2
    assert res["validator_result"] == "FAIL"
    assert "missing_WAVE_9_FIXTURE_RESULTS.jsonl" in res["failed_checks"]
