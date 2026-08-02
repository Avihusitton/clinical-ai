# -*- coding: utf-8 -*-
"""
tests/test_wave_8_4_report_validator.py
Mutation test suite for tests/wave_8_4_report_validator.py in Wave 8.6.
Calls real validator logic against mutated temporary evidence copies to prove it fails correctly.
"""

import json
import shutil
import tempfile
from pathlib import Path
import pytest

from tests.wave_8_4_report_validator import run_validation


@pytest.fixture
def temp_evidence_dir(tmp_path):
    src_dir = Path("tests")
    shutil.copy(src_dir / "WAVE_8_6_HARNESS_OUTPUT.txt", tmp_path / "WAVE_8_6_HARNESS_OUTPUT.txt")
    shutil.copy(src_dir / "WAVE_8_4_HARNESS_OUTPUT.txt", tmp_path / "WAVE_8_4_HARNESS_OUTPUT.txt")
    shutil.copy(src_dir / "WAVE_8_2_EVIDENCE_HARNESS_OUTPUT.txt", tmp_path / "WAVE_8_2_EVIDENCE_HARNESS_OUTPUT.txt")
    shutil.copy(src_dir / "WAVE_8_6_EXECUTION_ATTESTATION.json", tmp_path / "WAVE_8_6_EXECUTION_ATTESTATION.json")
    shutil.copy(src_dir / "WAVE_8_4_EXECUTION_ATTESTATION.json", tmp_path / "WAVE_8_4_EXECUTION_ATTESTATION.json")
    shutil.copy(src_dir / "WAVE_8_4_AST_ATTESTATION.json", tmp_path / "WAVE_8_4_AST_ATTESTATION.json")
    shutil.copy(src_dir / "WAVE_8_LEGACY_INVARIANCE_REPORT.json", tmp_path / "WAVE_8_LEGACY_INVARIANCE_REPORT.json")
    shutil.copy(src_dir / "WAVE_8_SHADOW_BEHAVIOR_REPORT.json", tmp_path / "WAVE_8_SHADOW_BEHAVIOR_REPORT.json")
    shutil.copy(src_dir / "WAVE_8_4_REDACTION_BENCHMARK.json", tmp_path / "WAVE_8_4_REDACTION_BENCHMARK.json")
    shutil.copy(src_dir / "WAVE_8_5_VALIDATION_INPUT_HASHES.json", tmp_path / "WAVE_8_5_VALIDATION_INPUT_HASHES.json")
    return tmp_path


def test_validator_passes_on_unmodified_evidence(temp_evidence_dir):
    res = run_validation(input_dir=temp_evidence_dir)
    assert res["validator_result"] == "PASS"
    assert len(res["failed_checks"]) == 0


def test_validator_fails_when_f2_runner_entered_later_than_answer_started(temp_evidence_dir):
    p = temp_evidence_dir / "WAVE_8_2_EVIDENCE_HARNESS_OUTPUT.txt"
    data = json.loads(p.read_text(encoding="utf-8"))
    f2_ts = data["scenario_f2_preblocked_worker_does_not_block_request"]["observed_timestamps"]
    f2_ts["runner_entered_ns"] = f2_ts["answer_started_ns"] + 50000
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")

    res = run_validation(input_dir=temp_evidence_dir)
    assert res["validator_result"] == "FAIL"
    assert "scenario_f2_invalid" in res["failed_checks"]


def test_validator_fails_when_f2_runner_entered_later_than_answer_returned(temp_evidence_dir):
    p = temp_evidence_dir / "WAVE_8_2_EVIDENCE_HARNESS_OUTPUT.txt"
    data = json.loads(p.read_text(encoding="utf-8"))
    f2_ts = data["scenario_f2_preblocked_worker_does_not_block_request"]["observed_timestamps"]
    f2_ts["runner_entered_ns"] = f2_ts["answer_returned_ns"] + 50000
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")

    res = run_validation(input_dir=temp_evidence_dir)
    assert res["validator_result"] == "FAIL"
    assert "scenario_f2_invalid" in res["failed_checks"]


def test_validator_fails_when_f2_answer_returned_later_than_release(temp_evidence_dir):
    p = temp_evidence_dir / "WAVE_8_2_EVIDENCE_HARNESS_OUTPUT.txt"
    data = json.loads(p.read_text(encoding="utf-8"))
    f2_ts = data["scenario_f2_preblocked_worker_does_not_block_request"]["observed_timestamps"]
    f2_ts["answer_returned_ns"] = f2_ts["runner_release_requested_ns"] + 50000
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")

    res = run_validation(input_dir=temp_evidence_dir)
    assert res["validator_result"] == "FAIL"
    assert "scenario_f2_invalid" in res["failed_checks"]


def test_validator_fails_when_f2_runner_exited_before_release(temp_evidence_dir):
    p = temp_evidence_dir / "WAVE_8_2_EVIDENCE_HARNESS_OUTPUT.txt"
    data = json.loads(p.read_text(encoding="utf-8"))
    f2_states = data["scenario_f2_preblocked_worker_does_not_block_request"]["observed_states"]
    f2_states["runner_exited_event_set_before_release"] = True
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")

    res = run_validation(input_dir=temp_evidence_dir)
    assert res["validator_result"] == "FAIL"
    assert "scenario_f2_invalid" in res["failed_checks"]


def test_validator_fails_when_f2_runner_exited_earlier_than_release(temp_evidence_dir):
    p = temp_evidence_dir / "WAVE_8_2_EVIDENCE_HARNESS_OUTPUT.txt"
    data = json.loads(p.read_text(encoding="utf-8"))
    f2_ts = data["scenario_f2_preblocked_worker_does_not_block_request"]["observed_timestamps"]
    f2_ts["runner_exited_ns"] = f2_ts["runner_release_requested_ns"] - 50000
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")

    res = run_validation(input_dir=temp_evidence_dir)
    assert res["validator_result"] == "FAIL"
    assert "scenario_f2_invalid" in res["failed_checks"]


def test_validator_fails_when_f1_classification_mismatched(temp_evidence_dir):
    p = temp_evidence_dir / "WAVE_8_2_EVIDENCE_HARNESS_OUTPUT.txt"
    data = json.loads(p.read_text(encoding="utf-8"))
    data["scenario_f1_request_returns_before_worker_start"]["classification"] = "INVALID_CLASSIFICATION"
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")

    res = run_validation(input_dir=temp_evidence_dir)
    assert res["validator_result"] == "FAIL"
    assert "scenario_f1_invalid" in res["failed_checks"]


def test_validator_fails_when_exception_record_removed(temp_evidence_dir):
    p = temp_evidence_dir / "WAVE_8_LEGACY_INVARIANCE_REPORT.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    data["legacy_exception_invariance"]["observed_exception_scenarios"].pop()
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")

    res = run_validation(input_dir=temp_evidence_dir)
    assert res["validator_result"] == "FAIL"
    assert "legacy_exceptions_invalid" in res["failed_checks"]


def test_validator_fails_when_duplicate_exception_scenario_id(temp_evidence_dir):
    p = temp_evidence_dir / "WAVE_8_LEGACY_INVARIANCE_REPORT.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    scs = data["legacy_exception_invariance"]["observed_exception_scenarios"]
    if scs:
        scs[1]["scenario_id"] = scs[0]["scenario_id"]
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")

    res = run_validation(input_dir=temp_evidence_dir)
    assert res["validator_result"] == "FAIL"
    assert "legacy_exceptions_invalid" in res["failed_checks"]


def test_validator_fails_when_queue_submit_3_moved_after_worker_release(temp_evidence_dir):
    p = temp_evidence_dir / "WAVE_8_2_EVIDENCE_HARNESS_OUTPUT.txt"
    data = json.loads(p.read_text(encoding="utf-8"))
    data["scenario_e_queue_saturation"]["observed"]["submit_3_returned_ns"] = 999999999999999
    data["scenario_e_queue_saturation"]["observed"]["worker_release_ns"] = 100000000000000
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")

    res = run_validation(input_dir=temp_evidence_dir)
    assert res["validator_result"] == "FAIL"
    assert "queue_saturation_invalid" in res["failed_checks"]


def test_validator_fails_when_pii_record_removed(temp_evidence_dir):
    p = temp_evidence_dir / "WAVE_8_2_EVIDENCE_HARNESS_OUTPUT.txt"
    data = json.loads(p.read_text(encoding="utf-8"))
    data["scenario_h_pii_rejection"]["observed"]["cases_tested_count"] = 19
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")

    res = run_validation(input_dir=temp_evidence_dir)
    assert res["validator_result"] == "FAIL"
    assert "pii_records_invalid" in res["failed_checks"]


def test_validator_fails_when_pii_detected_false(temp_evidence_dir):
    p = temp_evidence_dir / "WAVE_8_2_EVIDENCE_HARNESS_OUTPUT.txt"
    data = json.loads(p.read_text(encoding="utf-8"))
    data["scenario_h_pii_rejection"]["observed"]["all_pii_detected"] = False
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")

    res = run_validation(input_dir=temp_evidence_dir)
    assert res["validator_result"] == "FAIL"
    assert "pii_records_invalid" in res["failed_checks"]


def test_validator_fails_when_synthetic_query_subscript_count_non_zero(temp_evidence_dir):
    p = temp_evidence_dir / "WAVE_8_4_AST_ATTESTATION.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    data["synthetic_query_subscript_count"] = 1
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")

    res = run_validation(input_dir=temp_evidence_dir)
    assert res["validator_result"] == "FAIL"
    assert "ast_source_invalid" in res["failed_checks"]


def test_validator_fails_when_redaction_wording_overclaims(temp_evidence_dir):
    p = temp_evidence_dir / "WAVE_8_4_REDACTION_BENCHMARK.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    data["approved_wording"] = "100% production precision and perfect PII detection guaranteed."
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")

    res = run_validation(input_dir=temp_evidence_dir)
    assert res["validator_result"] == "FAIL"
    assert "redaction_benchmark_invalid" in res["failed_checks"]
