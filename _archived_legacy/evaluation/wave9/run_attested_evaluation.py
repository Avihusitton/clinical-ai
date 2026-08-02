# -*- coding: utf-8 -*-
"""
evaluation/wave9/run_attested_evaluation.py
Attested Execution Orchestrator for Wave 9.4.
Executes evaluation harness, stress harness, and Stage A validator in subprocesses.
Captures actual return codes, stdout, stderr, and generates runtime before/after source attestation.
"""

import sys
import json
import hashlib
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List

from .source_attestation import get_expected_source_inventory


def run_pipeline() -> int:
    root_dir = Path(__file__).resolve().parent.parent.parent
    tests_dir = root_dir / "tests"
    tests_dir.mkdir(exist_ok=True)

    # 1. Runtime UTC start timestamp
    started_utc = datetime.now(timezone.utc).isoformat()

    # 2. Source inventory before
    inv_before = get_expected_source_inventory()
    paths_before = [item["normalized_path"] for item in inv_before]
    hashes_before = {item["normalized_path"]: item["sha256"] for item in inv_before}

    # 3. Execute evaluation harness
    eval_proc = subprocess.run(
        [sys.executable, "-B", "-m", "evaluation.wave9.evaluation_harness"],
        cwd=str(root_dir),
        capture_output=True,
        text=True
    )
    eval_stdout_p = tests_dir / "WAVE_9_4_EVALUATION_STDOUT.txt"
    eval_stderr_p = tests_dir / "WAVE_9_4_EVALUATION_STDERR.txt"
    eval_stdout_p.write_bytes(eval_proc.stdout.encode("utf-8"))
    eval_stderr_p.write_bytes(eval_proc.stderr.encode("utf-8"))

    # 4. Execute stress harness
    stress_proc = subprocess.run(
        [sys.executable, "-B", "-m", "evaluation.wave9.stress_harness"],
        cwd=str(root_dir),
        capture_output=True,
        text=True
    )
    stress_stdout_p = tests_dir / "WAVE_9_4_STRESS_STDOUT.txt"
    stress_stderr_p = tests_dir / "WAVE_9_4_STRESS_STDERR.txt"
    stress_stdout_p.write_bytes(stress_proc.stdout.encode("utf-8"))
    stress_stderr_p.write_bytes(stress_proc.stderr.encode("utf-8"))

    # 5. Execute Stage A validator
    val_proc = subprocess.run(
        [sys.executable, "-B", "-m", "evaluation.wave9.validator"],
        cwd=str(root_dir),
        capture_output=True,
        text=True
    )
    val_stdout_p = tests_dir / "WAVE_9_4_VALIDATOR_STDOUT.txt"
    val_stderr_p = tests_dir / "WAVE_9_4_VALIDATOR_STDERR.txt"
    val_stdout_p.write_bytes(val_proc.stdout.encode("utf-8"))
    val_stderr_p.write_bytes(val_proc.stderr.encode("utf-8"))

    # 6. Runtime UTC finish timestamp
    finished_utc = datetime.now(timezone.utc).isoformat()

    # 7. Source inventory after
    inv_after = get_expected_source_inventory()
    paths_after = [item["normalized_path"] for item in inv_after]
    hashes_after = {item["normalized_path"]: item["sha256"] for item in inv_after}

    before_keys = set(hashes_before.keys())
    after_keys = set(hashes_after.keys())

    missing_after = sorted(list(before_keys - after_keys))
    added_during = sorted(list(after_keys - before_keys))

    common_keys = before_keys & after_keys
    modified_during = sorted([k for k in common_keys if hashes_before[k] != hashes_after[k]])

    source_unchanged = (paths_before == paths_after and hashes_before == hashes_after)

    # 8. Raw output hashes read from written file bytes
    eval_stdout_sha = hashlib.sha256(eval_stdout_p.read_bytes()).hexdigest()
    eval_stderr_sha = hashlib.sha256(eval_stderr_p.read_bytes()).hexdigest()

    stress_stdout_sha = hashlib.sha256(stress_stdout_p.read_bytes()).hexdigest()
    stress_stderr_sha = hashlib.sha256(stress_stderr_p.read_bytes()).hexdigest()

    val_stdout_sha = hashlib.sha256(val_stdout_p.read_bytes()).hexdigest()
    val_stderr_sha = hashlib.sha256(val_stderr_p.read_bytes()).hexdigest()

    attestation = {
        "execution_started_at_utc": started_utc,
        "execution_finished_at_utc": finished_utc,
        "source_hashes_before": hashes_before,
        "source_hashes_after": hashes_after,
        "source_paths_before": paths_before,
        "source_paths_after": paths_after,
        "added_during_execution": added_during,
        "missing_after_execution": missing_after,
        "modified_during_execution": modified_during,
        "source_unchanged_during_evaluation": source_unchanged,
        "evaluation_exit_code": eval_proc.returncode,
        "stress_exit_code": stress_proc.returncode,
        "validator_exit_code": val_proc.returncode,
        "evaluation_stdout_sha256": eval_stdout_sha,
        "evaluation_stderr_sha256": eval_stderr_sha,
        "stress_stdout_sha256": stress_stdout_sha,
        "stress_stderr_sha256": stress_stderr_sha,
        "validator_stdout_sha256": val_stdout_sha,
        "validator_stderr_sha256": val_stderr_sha
    }

    attest_p = tests_dir / "WAVE_9_4_EXECUTION_ATTESTATION.json"
    attest_p.write_text(json.dumps(attestation, indent=2, sort_keys=True), encoding="utf-8")

    pipeline_exit_code = 0 if (eval_proc.returncode == 0 and stress_proc.returncode == 0 and val_proc.returncode == 0 and source_unchanged) else 1
    print(f"Wave 9.4 Attested Orchestrator finished with pipeline exit code {pipeline_exit_code}")
    return pipeline_exit_code


if __name__ == "__main__":
    code = run_pipeline()
    sys.exit(code)
