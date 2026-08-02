# -*- coding: utf-8 -*-
"""
tests/test_wave9_source_attestation.py
Mutation test suite for Stage B attestation validation in Wave 9.4R.
Executes real attestation validation logic against mutated temporary attestation records.
Includes consistent omission mutations, baseline identity mutation tests, and atomic-write tests.
"""

import json
import hashlib
from pathlib import Path
import pytest

from evaluation.wave9.source_attestation import validate_attestation, get_expected_source_inventory


@pytest.fixture
def temp_attest_dir(tmp_path):
    inv = get_expected_source_inventory()
    source_paths = [item["normalized_path"] for item in inv]
    source_hashes = {item["normalized_path"]: item["sha256"] for item in inv}

    raw_files_data = {
        "WAVE_9_4R_EVALUATION_STDOUT.txt": b"synthetic eval stdout\n",
        "WAVE_9_4R_EVALUATION_STDERR.txt": b"",
        "WAVE_9_4R_STRESS_STDOUT.txt": b"synthetic stress stdout\n",
        "WAVE_9_4R_STRESS_STDERR.txt": b"",
        "WAVE_9_4R_VALIDATOR_STDOUT.txt": b"synthetic validator stdout\n",
        "WAVE_9_4R_VALIDATOR_STDERR.txt": b"",
    }

    raw_hashes = {}
    for filename, content_bytes in raw_files_data.items():
        (tmp_path / filename).write_bytes(content_bytes)
        key = filename.replace("WAVE_9_4R_", "").replace(".txt", "").lower() + "_sha256"
        raw_hashes[key] = hashlib.sha256(content_bytes).hexdigest()

    attestation_data = {
        "execution_started_at_utc": "2026-07-24T00:00:00+00:00",
        "execution_finished_at_utc": "2026-07-24T00:01:00+00:00",
        "evaluation_exit_code": 0,
        "stress_exit_code": 0,
        "validator_exit_code": 0,
        "source_paths_before": source_paths,
        "source_paths_after": source_paths,
        "source_hashes_before": source_hashes,
        "source_hashes_after": source_hashes,
        "source_unchanged_during_evaluation": True,
        "added_during_execution": [],
        "missing_after_execution": [],
        "modified_during_execution": [],
        "evaluation_stdout_sha256": raw_hashes["evaluation_stdout_sha256"],
        "evaluation_stderr_sha256": raw_hashes["evaluation_stderr_sha256"],
        "stress_stdout_sha256": raw_hashes["stress_stdout_sha256"],
        "stress_stderr_sha256": raw_hashes["stress_stderr_sha256"],
        "validator_stdout_sha256": raw_hashes["validator_stdout_sha256"],
        "validator_stderr_sha256": raw_hashes["validator_stderr_sha256"],
    }
    (tmp_path / "WAVE_9_4R_EXECUTION_ATTESTATION.json").write_text(json.dumps(attestation_data, indent=2), encoding="utf-8")

    content1 = b"import pytest\ndef test_gate_cd_boundary(): pass\n"
    sha1 = hashlib.sha256(content1).hexdigest()

    content2 = b"import pytest\ndef test_gate_a(): pass\n"
    sha2 = hashlib.sha256(content2).hexdigest()

    baseline_identity_data = [
        {
            "working_path": "tests/test_gate_cd_boundary.py",
            "baseline_source_type": "bundle",
            "baseline_source_reference": "PROJECT_CODE_BUNDLE.txt",
            "git_lookup_exit_code": 128,
            "bundle_begin_marker_count": 1,
            "bundle_end_marker_count": 1,
            "bundle_section_count": 1,
            "bundle_begin_line": 75850,
            "bundle_end_line": 76370,
            "begin_framing_removed": True,
            "end_framing_removed": False,
            "framing_lines_removed": True,
            "baseline_extraction_success": True,
            "baseline_extraction_failure_reason": "",
            "baseline_sha256": sha1,
            "working_sha256": sha1,
            "baseline_normalized_sha256": sha1,
            "working_normalized_sha256": sha1,
            "baseline_byte_length": len(content1),
            "working_byte_length": len(content1),
            "comparison_type": "NORMALIZED_TEXT_MATCH",
            "match": True,
            "working_file_used_as_baseline": False
        },
        {
            "working_path": "tests/test_gate_a_dry_run_and_isolation.py",
            "baseline_source_type": "bundle",
            "baseline_source_reference": "PROJECT_CODE_BUNDLE.txt",
            "git_lookup_exit_code": 128,
            "bundle_begin_marker_count": 1,
            "bundle_end_marker_count": 1,
            "bundle_section_count": 1,
            "bundle_begin_line": 72702,
            "bundle_end_line": 72891,
            "begin_framing_removed": True,
            "end_framing_removed": False,
            "framing_lines_removed": True,
            "baseline_extraction_success": True,
            "baseline_extraction_failure_reason": "",
            "baseline_sha256": sha2,
            "working_sha256": sha2,
            "baseline_normalized_sha256": sha2,
            "working_normalized_sha256": sha2,
            "baseline_byte_length": len(content2),
            "working_byte_length": len(content2),
            "comparison_type": "NORMALIZED_TEXT_MATCH",
            "match": True,
            "working_file_used_as_baseline": False
        }
    ]
    (tmp_path / "WAVE_9_4R_BASELINE_TEST_IDENTITY.json").write_text(json.dumps(baseline_identity_data, indent=2), encoding="utf-8")

    return tmp_path


def test_attestation_passes_on_clean_evidence(temp_attest_dir):
    res = validate_attestation(input_dir=temp_attest_dir)
    assert res["attestation_validator_exit_code"] == 0
    assert res["validator_result"] == "PASS"
    assert res["failed_checks"] == []


def test_atomic_write_hash_match(tmp_path):
    inv = get_expected_source_inventory()
    source_paths = [item["normalized_path"] for item in inv]
    source_hashes = {item["normalized_path"]: item["sha256"] for item in inv}

    raw_files_data = {
        "WAVE_9_4R_EVALUATION_STDOUT.txt": b"synthetic eval stdout bytes \x00\xff\n",
        "WAVE_9_4R_EVALUATION_STDERR.txt": b"synthetic eval stderr bytes \x01\xfe\n",
        "WAVE_9_4R_STRESS_STDOUT.txt": b"synthetic stress stdout bytes \x02\xfd\n",
        "WAVE_9_4R_STRESS_STDERR.txt": b"synthetic stress stderr bytes \x03\xfc\n",
        "WAVE_9_4R_VALIDATOR_STDOUT.txt": b"synthetic validator stdout bytes \x04\xfb\n",
        "WAVE_9_4R_VALIDATOR_STDERR.txt": b"synthetic validator stderr bytes \x05\xfa\n",
    }

    raw_hashes = {}
    for filename, content_bytes in raw_files_data.items():
        (tmp_path / filename).write_bytes(content_bytes)
        key = filename.replace("WAVE_9_4R_", "").replace(".txt", "").lower() + "_sha256"
        raw_hashes[key] = hashlib.sha256(content_bytes).hexdigest()

    attestation_data = {
        "execution_started_at_utc": "2026-07-24T00:00:00+00:00",
        "execution_finished_at_utc": "2026-07-24T00:01:00+00:00",
        "evaluation_exit_code": 0,
        "stress_exit_code": 0,
        "validator_exit_code": 0,
        "source_paths_before": source_paths,
        "source_paths_after": source_paths,
        "source_hashes_before": source_hashes,
        "source_hashes_after": source_hashes,
        "source_unchanged_during_evaluation": True,
        "added_during_execution": [],
        "missing_after_execution": [],
        "modified_during_execution": [],
        "evaluation_stdout_sha256": raw_hashes["evaluation_stdout_sha256"],
        "evaluation_stderr_sha256": raw_hashes["evaluation_stderr_sha256"],
        "stress_stdout_sha256": raw_hashes["stress_stdout_sha256"],
        "stress_stderr_sha256": raw_hashes["stress_stderr_sha256"],
        "validator_stdout_sha256": raw_hashes["validator_stdout_sha256"],
        "validator_stderr_sha256": raw_hashes["validator_stderr_sha256"],
    }
    (tmp_path / "WAVE_9_4R_EXECUTION_ATTESTATION.json").write_text(json.dumps(attestation_data, indent=2), encoding="utf-8")

    content1 = b"import pytest\ndef test_gate_cd_boundary(): pass\n"
    sha1 = hashlib.sha256(content1).hexdigest()

    content2 = b"import pytest\ndef test_gate_a(): pass\n"
    sha2 = hashlib.sha256(content2).hexdigest()

    baseline_identity_data = [
        {
            "working_path": "tests/test_gate_cd_boundary.py",
            "baseline_source_type": "bundle",
            "baseline_source_reference": "PROJECT_CODE_BUNDLE.txt",
            "git_lookup_exit_code": 128,
            "bundle_begin_marker_count": 1,
            "bundle_end_marker_count": 1,
            "bundle_section_count": 1,
            "bundle_begin_line": 75850,
            "bundle_end_line": 76370,
            "begin_framing_removed": True,
            "end_framing_removed": False,
            "framing_lines_removed": True,
            "baseline_extraction_success": True,
            "baseline_extraction_failure_reason": "",
            "baseline_sha256": sha1,
            "working_sha256": sha1,
            "baseline_normalized_sha256": sha1,
            "working_normalized_sha256": sha1,
            "baseline_byte_length": len(content1),
            "working_byte_length": len(content1),
            "comparison_type": "NORMALIZED_TEXT_MATCH",
            "match": True,
            "working_file_used_as_baseline": False
        },
        {
            "working_path": "tests/test_gate_a_dry_run_and_isolation.py",
            "baseline_source_type": "bundle",
            "baseline_source_reference": "PROJECT_CODE_BUNDLE.txt",
            "git_lookup_exit_code": 128,
            "bundle_begin_marker_count": 1,
            "bundle_end_marker_count": 1,
            "bundle_section_count": 1,
            "bundle_begin_line": 72702,
            "bundle_end_line": 72891,
            "begin_framing_removed": True,
            "end_framing_removed": False,
            "framing_lines_removed": True,
            "baseline_extraction_success": True,
            "baseline_extraction_failure_reason": "",
            "baseline_sha256": sha2,
            "working_sha256": sha2,
            "baseline_normalized_sha256": sha2,
            "working_normalized_sha256": sha2,
            "baseline_byte_length": len(content2),
            "working_byte_length": len(content2),
            "comparison_type": "NORMALIZED_TEXT_MATCH",
            "match": True,
            "working_file_used_as_baseline": False
        }
    ]
    (tmp_path / "WAVE_9_4R_BASELINE_TEST_IDENTITY.json").write_text(json.dumps(baseline_identity_data, indent=2), encoding="utf-8")

    res = validate_attestation(input_dir=tmp_path)
    assert res["attestation_validator_exit_code"] == 0
    assert res["validator_result"] == "PASS"
    assert not any(check.startswith("raw_output_sha256_mismatch") for check in res["failed_checks"])


def test_attestation_fails_when_pytest_ini_present(temp_attest_dir):
    pytest_ini = temp_attest_dir.parent / "pytest.ini"
    pytest_ini.write_text("[pytest]\n", encoding="utf-8")
    try:
        res = validate_attestation(input_dir=temp_attest_dir)
        assert res["attestation_validator_exit_code"] == 1
        assert "pytest_ini_present" in res["failed_checks"]
    finally:
        if pytest_ini.exists():
            pytest_ini.unlink()


def test_attestation_fails_when_root_conftest_present(temp_attest_dir):
    conftest = temp_attest_dir.parent / "conftest.py"
    conftest.write_text("# conftest\n", encoding="utf-8")
    try:
        res = validate_attestation(input_dir=temp_attest_dir)
        assert res["attestation_validator_exit_code"] == 1
        assert "root_conftest_present" in res["failed_checks"]
    finally:
        if conftest.exists():
            conftest.unlink()


def test_attestation_fails_when_evaluation_exit_code_nonzero(temp_attest_dir):
    p = temp_attest_dir / "WAVE_9_4R_EXECUTION_ATTESTATION.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    data["evaluation_exit_code"] = 1
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")

    res = validate_attestation(input_dir=temp_attest_dir)
    assert res["attestation_validator_exit_code"] == 1
    assert "evaluation_exit_code_nonzero" in res["failed_checks"]


def test_attestation_fails_when_stress_exit_code_nonzero(temp_attest_dir):
    p = temp_attest_dir / "WAVE_9_4R_EXECUTION_ATTESTATION.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    data["stress_exit_code"] = 1
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")

    res = validate_attestation(input_dir=temp_attest_dir)
    assert res["attestation_validator_exit_code"] == 1
    assert "stress_exit_code_nonzero" in res["failed_checks"]


def test_attestation_fails_when_validator_exit_code_nonzero(temp_attest_dir):
    p = temp_attest_dir / "WAVE_9_4R_EXECUTION_ATTESTATION.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    data["validator_exit_code"] = 1
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")

    res = validate_attestation(input_dir=temp_attest_dir)
    assert res["attestation_validator_exit_code"] == 1
    assert "validator_exit_code_nonzero" in res["failed_checks"]


def test_attestation_fails_when_start_timestamp_missing(temp_attest_dir):
    p = temp_attest_dir / "WAVE_9_4R_EXECUTION_ATTESTATION.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    data.pop("execution_started_at_utc", None)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")

    res = validate_attestation(input_dir=temp_attest_dir)
    assert res["attestation_validator_exit_code"] == 1
    assert "execution_start_timestamp_missing" in res["failed_checks"]


def test_attestation_fails_when_finish_timestamp_missing(temp_attest_dir):
    p = temp_attest_dir / "WAVE_9_4R_EXECUTION_ATTESTATION.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    data.pop("execution_finished_at_utc", None)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")

    res = validate_attestation(input_dir=temp_attest_dir)
    assert res["attestation_validator_exit_code"] == 1
    assert "execution_finish_timestamp_missing" in res["failed_checks"]


def _perform_consistent_omission_mutation(temp_attest_dir, omitted_filename):
    p = temp_attest_dir / "WAVE_9_4R_EXECUTION_ATTESTATION.json"
    data = json.loads(p.read_text(encoding="utf-8"))

    data["source_paths_before"] = [path for path in data["source_paths_before"] if not path.endswith(omitted_filename)]
    data["source_paths_after"] = [path for path in data["source_paths_after"] if not path.endswith(omitted_filename)]

    data["source_hashes_before"] = {k: v for k, v in data["source_hashes_before"].items() if not k.endswith(omitted_filename)}
    data["source_hashes_after"] = {k: v for k, v in data["source_hashes_after"].items() if not k.endswith(omitted_filename)}

    data["source_unchanged_during_evaluation"] = True
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")

    res = validate_attestation(input_dir=temp_attest_dir)
    assert res["attestation_validator_exit_code"] == 1
    assert "source_inventory_set_inequality" in res["failed_checks"] or "source_hashes_changed_during_evaluation" in res["failed_checks"]


def test_consistent_omission_mutation_eval_wave9_file(temp_attest_dir):
    _perform_consistent_omission_mutation(temp_attest_dir, "metrics.py")


def test_consistent_omission_mutation_shadow_wiring_file(temp_attest_dir):
    _perform_consistent_omission_mutation(temp_attest_dir, "dispatcher.py")


def test_consistent_omission_mutation_controlled_integration_file(temp_attest_dir):
    _perform_consistent_omission_mutation(temp_attest_dir, "orchestrator.py")


def test_consistent_omission_mutation_retrieval_py(temp_attest_dir):
    _perform_consistent_omission_mutation(temp_attest_dir, "retrieval.py")


def test_consistent_omission_mutation_frozen_fixture(temp_attest_dir):
    _perform_consistent_omission_mutation(temp_attest_dir, "shadow_cases.jsonl")


def test_attestation_fails_when_one_source_hash_changed_while_boolean_true(temp_attest_dir):
    p = temp_attest_dir / "WAVE_9_4R_EXECUTION_ATTESTATION.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    data["source_hashes_after"]["retrieval.py"] = "MUTATED_HASH_AFTER"
    data["source_unchanged_during_evaluation"] = True
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")

    res = validate_attestation(input_dir=temp_attest_dir)
    assert res["attestation_validator_exit_code"] == 1
    assert "source_hashes_changed_during_evaluation" in res["failed_checks"]


def test_attestation_fails_when_baseline_extraction_failed(temp_attest_dir):
    p = temp_attest_dir / "WAVE_9_4R_BASELINE_TEST_IDENTITY.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    if isinstance(data, list):
        for entry in data:
            entry["match"] = False
    else:
        data["gate_cd_boundary"]["match"] = False
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")

    res = validate_attestation(input_dir=temp_attest_dir)
    assert res["attestation_validator_exit_code"] == 1
    assert "baseline_test_identity_mismatched" in res["failed_checks"]


def test_attestation_fails_when_working_file_used_as_baseline_true(temp_attest_dir):
    p = temp_attest_dir / "WAVE_9_4R_BASELINE_TEST_IDENTITY.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    if isinstance(data, list):
        for entry in data:
            entry["working_file_used_as_baseline"] = True
    else:
        data["summary"]["working_files_used_as_own_baseline"] = True
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")

    res = validate_attestation(input_dir=temp_attest_dir)
    assert res["attestation_validator_exit_code"] == 1
    assert "baseline_test_identity_mismatched" in res["failed_checks"]


def test_attestation_fails_code_2_when_attestation_file_missing(temp_attest_dir):
    p = temp_attest_dir / "WAVE_9_4R_EXECUTION_ATTESTATION.json"
    if p.exists():
        p.unlink()

    res = validate_attestation(input_dir=temp_attest_dir)
    assert res["attestation_validator_exit_code"] == 2
    assert res["validator_result"] == "FAIL"
    assert "attestation_file_missing" in res["failed_checks"]


def test_attestation_fails_code_2_when_attestation_file_malformed(temp_attest_dir):
    p = temp_attest_dir / "WAVE_9_4R_EXECUTION_ATTESTATION.json"
    p.write_text("MALFORMED JSON {{{", encoding="utf-8")

    res = validate_attestation(input_dir=temp_attest_dir)
    assert res["attestation_validator_exit_code"] == 2
    assert res["validator_result"] == "FAIL"
    assert "attestation_file_malformed" in res["failed_checks"]
