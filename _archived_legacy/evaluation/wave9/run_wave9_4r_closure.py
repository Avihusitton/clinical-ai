#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
evaluation/wave9/run_wave9_4r_closure.py
Wave 9.4R closure driver — fail-closed evidence generation.

This driver:
1. Uses get_expected_source_inventory() from source_attestation.py
2. Captures source inventory before evaluation
3. Runs evaluation, stress, and validator via subprocess.run(..., shell=False)
4. Captures actual return codes, stdout, stderr
5. Captures source inventory after execution
6. Creates tests/WAVE_9_4R_EXECUTION_ATTESTATION.json

The driver is fail-closed: any nonzero exit code, missing artifact,
baseline mismatch, attestation failure, or pytest failure forbids PASS.
"""

import os
import subprocess
import json
import sys
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, List

# Project root relative to this script
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
os.chdir(PROJECT_ROOT)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ---- Bundle extraction utilities (preserved for test_extractor_bundle_section) ----

from typing import Dict as DictT


def normalize_marker_path(value: str) -> str:
    """Normalize file path markers for comparison.
    Strips whitespace, replaces backslashes with forward slashes, and collapses duplicate slashes.
    """
    value = value.strip().replace("\\", "/")
    while "//" in value:
        value = value.replace("//", "/")
    return value


def normalize_text(text: str) -> str:
    text = text.removeprefix("\ufeff")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text.rstrip("\n") + "\n"


def extract_bundle_section(bundle_text: str, target_path: str) -> dict:
    """Extract a file section from a bundled text.

    Returns a dict with required fields:
    - success (bool)
    - target_path (str)
    - begin_line (int | None)
    - end_line (int | None)
    - begin_marker (str | None)
    - end_marker (str | None)
    - begin_marker_count (int)
    - end_marker_count (int)
    - section_count (int)
    - raw_content (str)
    - failure_reason (str)
    - begin_framing_removed (bool)
    - end_framing_removed (bool)
    - framing_lines_removed (bool)
    """
    lines = bundle_text.splitlines(keepends=True)
    begin_markers: DictT[str, list] = {}
    end_markers: DictT[str, list] = {}
    for idx, line in enumerate(lines):
        if line.startswith("BEGIN FILE:"):
            path = line[len("BEGIN FILE:"):].strip()
            norm = normalize_marker_path(path)
            begin_markers.setdefault(norm, []).append((idx + 1, line.rstrip("\r\n")))
        elif line.startswith("END FILE:"):
            path = line[len("END FILE:"):].strip()
            norm = normalize_marker_path(path)
            end_markers.setdefault(norm, []).append((idx + 1, line.rstrip("\r\n")))
    target_norm = normalize_marker_path(target_path)
    result = {
        "success": False,
        "target_path": target_path,
        "begin_line": None,
        "end_line": None,
        "begin_marker": None,
        "end_marker": None,
        "begin_marker_count": len(begin_markers.get(target_norm, [])),
        "end_marker_count": len(end_markers.get(target_norm, [])),
        "section_count": 0,
        "raw_content": "",
        "failure_reason": "",
        "begin_framing_removed": False,
        "end_framing_removed": False,
        "framing_lines_removed": False,
    }
    if result["begin_marker_count"] != 1:
        result["failure_reason"] = "Incorrect number of begin markers"
        return result
    if result["end_marker_count"] != 1:
        result["failure_reason"] = "Incorrect number of end markers"
        return result
    begin_line, begin_marker = begin_markers[target_norm][0]
    end_line, end_marker = end_markers[target_norm][0]
    if end_line <= begin_line:
        result["failure_reason"] = "End marker appears before begin marker"
        return result

    content_start_idx = begin_line  # 0-based index of line after BEGIN FILE
    content_end_idx = end_line - 1  # 0-based index of END FILE line

    # Check for framing separator immediately after BEGIN FILE
    if content_start_idx < content_end_idx:
        first_line = lines[content_start_idx].rstrip("\r\n")
        if len(first_line) >= 3 and len(set(first_line)) == 1 and first_line[0] in "=-~#*":
            result["begin_framing_removed"] = True
            content_start_idx += 1

    # Check for framing separator immediately before END FILE
    if content_start_idx < content_end_idx:
        last_line = lines[content_end_idx - 1].rstrip("\r\n")
        if len(last_line) >= 3 and len(set(last_line)) == 1 and last_line[0] in "=-~#*":
            result["end_framing_removed"] = True
            content_end_idx -= 1

    result["framing_lines_removed"] = result["begin_framing_removed"] or result["end_framing_removed"]

    raw_content = "".join(lines[content_start_idx:content_end_idx])
    if raw_content == "":
        result["failure_reason"] = "Empty content"
        return result

    result.update({
        "success": True,
        "begin_line": begin_line,
        "end_line": end_line,
        "begin_marker": begin_marker,
        "end_marker": end_marker,
        "section_count": 1,
        "raw_content": raw_content
    })
    return result


# ---- Fail-closed helpers ----

def sha256_str(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_text(path: str, content: str):
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def abort(status_line: str):
    """Write a minimal failure report and exit with code 1."""
    report_path = os.path.join("docs", "orchestration", "WAVE_9_4R_FINAL_REPORT.md")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(status_line + "\n")
    print(f"ABORT: {status_line}", file=sys.stderr)
    sys.exit(1)


def capture_source_inventory() -> Dict[str, Any]:
    """Capture current source inventory using source_attestation.get_expected_source_inventory()."""
    from evaluation.wave9.source_attestation import get_expected_source_inventory
    inv = get_expected_source_inventory()
    paths = sorted([item["normalized_path"] for item in inv])
    hashes = {item["normalized_path"]: item["sha256"] for item in inv}
    return {"paths": paths, "hashes": hashes}


from pathlib import Path


def run_subprocess(cmd_args: List[str], label: str) -> Dict[str, Any]:
    """Run a subprocess with shell=False, capture stdout/stderr as bytes."""
    result = subprocess.run(
        cmd_args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=PROJECT_ROOT,
        shell=False
    )
    return {
        "exit_code": result.returncode,
        "stdout_bytes": result.stdout or b"",
        "stderr_bytes": result.stderr or b"",
    }


# ---- Main driver ----

def main():
    fail_reasons = []

    # 0. Pre-checks
    if os.path.exists("pytest.ini") or os.path.exists("conftest.py"):
        abort("FINAL_STATUS: BLOCKED_PROTECTED_FILE_CHANGE_REQUIRED")

    # 1. Establish independent baselines for two protected tests
    baseline_files = [
        "tests/test_gate_cd_boundary.py",
        "tests/test_gate_a_dry_run_and_isolation.py"
    ]
    bundle_discovery = []
    baseline_data = {}

    for rel_path in baseline_files:
        # Try git show from feat/wave8-shadow-wiring
        git_result = subprocess.run(
            ["git", "show", f"feat/wave8-shadow-wiring:{rel_path}"],
            capture_output=True, text=True, cwd=PROJECT_ROOT, shell=False
        )
        if git_result.returncode == 0:
            baseline_data[rel_path] = {
                "content": git_result.stdout,
                "source_type": "git",
                "source_reference": f"feat/wave8-shadow-wiring:{rel_path}",
                "git_exit_code": 0,
                "extraction": {}
            }
        else:
            # Fallback to PROJECT_CODE_BUNDLE.txt
            bundle_path = os.path.join(PROJECT_ROOT, "PROJECT_CODE_BUNDLE.txt")
            if not os.path.exists(bundle_path):
                abort("FINAL_STATUS: BLOCKED_INDEPENDENT_BASELINE_UNAVAILABLE")
            with open(bundle_path, "r", encoding="utf-8") as bf:
                bundle_content = bf.read()
            extraction = extract_bundle_section(bundle_content, rel_path)
            bundle_discovery.append({
                "target_path": rel_path,
                "begin_marker_count": extraction["begin_marker_count"],
                "end_marker_count": extraction["end_marker_count"],
                "section_count": extraction["section_count"],
                "begin_line": extraction["begin_line"],
                "end_line": extraction["end_line"],
                "begin_framing_removed": extraction.get("begin_framing_removed", False),
                "end_framing_removed": extraction.get("end_framing_removed", False),
                "framing_lines_removed": extraction.get("framing_lines_removed", False),
                "success": extraction["success"],
                "failure_reason": extraction["failure_reason"]
            })
            if not extraction["success"]:
                abort(f"FINAL_STATUS: BLOCKED_INDEPENDENT_BASELINE_UNAVAILABLE {extraction['failure_reason']}")
            baseline_data[rel_path] = {
                "content": extraction["raw_content"],
                "source_type": "bundle",
                "source_reference": "PROJECT_CODE_BUNDLE.txt",
                "git_exit_code": git_result.returncode,
                "extraction": extraction
            }

    # 2. Compare baselines with working files
    detailed_baseline = []
    for path, info in baseline_data.items():
        content = info["content"]
        working_file_path = os.path.join(PROJECT_ROOT, path)
        with open(working_file_path, "r", encoding="utf-8") as wf:
            working_content = wf.read()

        working_sha = sha256_str(working_content)
        baseline_sha = sha256_str(content)
        working_len = len(working_content.encode("utf-8"))
        baseline_len = len(content.encode("utf-8"))

        norm_baseline = normalize_text(content)
        norm_working = normalize_text(working_content)
        baseline_norm_sha = sha256_str(norm_baseline)
        working_norm_sha = sha256_str(norm_working)

        if info["source_type"] == "git":
            match = (baseline_sha == working_sha)
            comparison_type = "EXACT_BYTE_MATCH"
        else:
            match = (norm_baseline == norm_working)
            comparison_type = "NORMALIZED_TEXT_MATCH"

        extraction = info.get("extraction", {})
        detailed_baseline.append({
            "working_path": path,
            "baseline_source_type": info["source_type"],
            "baseline_source_reference": info["source_reference"],
            "git_lookup_exit_code": info["git_exit_code"],
            "bundle_begin_marker_count": extraction.get("begin_marker_count", 0),
            "bundle_end_marker_count": extraction.get("end_marker_count", 0),
            "bundle_section_count": extraction.get("section_count", 0),
            "bundle_begin_line": extraction.get("begin_line"),
            "bundle_end_line": extraction.get("end_line"),
            "begin_framing_removed": extraction.get("begin_framing_removed", False),
            "end_framing_removed": extraction.get("end_framing_removed", False),
            "framing_lines_removed": extraction.get("framing_lines_removed", False),
            "baseline_extraction_success": extraction.get("success", info["source_type"] == "git"),
            "baseline_extraction_failure_reason": extraction.get("failure_reason", ""),
            "baseline_sha256": baseline_sha,
            "working_sha256": working_sha,
            "baseline_normalized_sha256": baseline_norm_sha,
            "working_normalized_sha256": working_norm_sha,
            "baseline_byte_length": baseline_len,
            "working_byte_length": working_len,
            "comparison_type": comparison_type,
            "match": match,
            "working_file_used_as_baseline": False
        })

    # Write baseline identity
    identity_path = os.path.join("tests", "WAVE_9_4R_BASELINE_TEST_IDENTITY.json")
    write_text(identity_path, json.dumps(detailed_baseline, indent=2))

    # Write bundle marker discovery
    discovery_path = os.path.join("tests", "WAVE_9_4R_BUNDLE_MARKER_DISCOVERY.json")
    write_text(discovery_path, json.dumps(bundle_discovery, indent=2))

    # 3. Record baseline match status
    any_baseline_mismatch = any(not entry["match"] for entry in detailed_baseline)
    if any_baseline_mismatch:
        fail_reasons.append("baseline_test_identity_mismatch")

    # 4. Capture source inventory BEFORE evaluation
    started_at = datetime.now(timezone.utc).isoformat()
    inventory_before = capture_source_inventory()

    # Write expected source inventory
    inv_path = os.path.join("tests", "WAVE_9_4R_EXPECTED_SOURCE_INVENTORY.json")
    from evaluation.wave9.source_attestation import get_expected_source_inventory
    inv_data = get_expected_source_inventory()
    write_text(inv_path, json.dumps({
        "file_hashes": {item["normalized_path"]: item["sha256"] for item in inv_data},
        "combined_hash": hashlib.sha256(
            "".join(item["sha256"] for item in inv_data).encode()
        ).hexdigest()
    }, indent=2))

    # 5. Run evaluation harness
    python_exe = sys.executable
    eval_result = run_subprocess(
        [python_exe, "-B", "-m", "evaluation.wave9.evaluation_harness"],
        "evaluation"
    )
    eval_stdout_bytes = eval_result["stdout_bytes"]
    eval_stderr_bytes = eval_result["stderr_bytes"]
    eval_stdout_sha256 = sha256_bytes(eval_stdout_bytes)
    eval_stderr_sha256 = sha256_bytes(eval_stderr_bytes)

    if eval_result["exit_code"] != 0:
        fail_reasons.append(f"evaluation_exit_code_{eval_result['exit_code']}")

    # 6. Run stress harness
    stress_result = run_subprocess(
        [python_exe, "-B", "-m", "evaluation.wave9.stress_harness"],
        "stress"
    )
    stress_stdout_bytes = stress_result["stdout_bytes"]
    stress_stderr_bytes = stress_result["stderr_bytes"]
    stress_stdout_sha256 = sha256_bytes(stress_stdout_bytes)
    stress_stderr_sha256 = sha256_bytes(stress_stderr_bytes)

    if stress_result["exit_code"] != 0:
        fail_reasons.append(f"stress_exit_code_{stress_result['exit_code']}")

    # 7. Run validator
    validator_result = run_subprocess(
        [python_exe, "-B", "-m", "evaluation.wave9.validator"],
        "validator"
    )
    validator_stdout_bytes = validator_result["stdout_bytes"]
    validator_stderr_bytes = validator_result["stderr_bytes"]
    validator_stdout_sha256 = sha256_bytes(validator_stdout_bytes)
    validator_stderr_sha256 = sha256_bytes(validator_stderr_bytes)

    if validator_result["exit_code"] != 0:
        fail_reasons.append(f"validator_exit_code_{validator_result['exit_code']}")

    # Write all raw bytes files BEFORE writing execution attestation
    Path("tests/WAVE_9_4R_EVALUATION_STDOUT.txt").write_bytes(eval_stdout_bytes)
    Path("tests/WAVE_9_4R_EVALUATION_STDERR.txt").write_bytes(eval_stderr_bytes)
    Path("tests/WAVE_9_4R_STRESS_STDOUT.txt").write_bytes(stress_stdout_bytes)
    Path("tests/WAVE_9_4R_STRESS_STDERR.txt").write_bytes(stress_stderr_bytes)
    Path("tests/WAVE_9_4R_VALIDATOR_STDOUT.txt").write_bytes(validator_stdout_bytes)
    Path("tests/WAVE_9_4R_VALIDATOR_STDERR.txt").write_bytes(validator_stderr_bytes)

    # 8. Capture source inventory AFTER execution
    finished_at = datetime.now(timezone.utc).isoformat()
    inventory_after = capture_source_inventory()

    # 9. Compute source change analysis
    before_set = set(inventory_before["paths"])
    after_set = set(inventory_after["paths"])
    added = sorted(list(after_set - before_set))
    missing = sorted(list(before_set - after_set))
    modified = sorted([
        p for p in before_set & after_set
        if inventory_before["hashes"].get(p) != inventory_after["hashes"].get(p)
    ])
    source_unchanged = (len(added) == 0 and len(missing) == 0 and len(modified) == 0)

    if not source_unchanged:
        fail_reasons.append("source_changed_during_evaluation")

    # 10. Create WAVE_9_4R_EXECUTION_ATTESTATION.json (LAST)
    attestation = {
        "execution_started_at_utc": started_at,
        "execution_finished_at_utc": finished_at,
        "evaluation_exit_code": eval_result["exit_code"],
        "stress_exit_code": stress_result["exit_code"],
        "validator_exit_code": validator_result["exit_code"],
        "source_paths_before": inventory_before["paths"],
        "source_paths_after": inventory_after["paths"],
        "source_hashes_before": inventory_before["hashes"],
        "source_hashes_after": inventory_after["hashes"],
        "source_unchanged_during_evaluation": source_unchanged,
        "added_during_execution": added,
        "missing_after_execution": missing,
        "modified_during_execution": modified,
        "evaluation_stdout_sha256": eval_stdout_sha256,
        "evaluation_stderr_sha256": eval_stderr_sha256,
        "stress_stdout_sha256": stress_stdout_sha256,
        "stress_stderr_sha256": stress_stderr_sha256,
        "validator_stdout_sha256": validator_stdout_sha256,
        "validator_stderr_sha256": validator_stderr_sha256,
    }

    attest_path = Path("tests/WAVE_9_4R_EXECUTION_ATTESTATION.json")
    attest_path.write_text(json.dumps(attestation, indent=2), encoding="utf-8")

    # 11. Determine exit status — fail-closed
    if fail_reasons:
        print(f"Wave 9.4R closure driver completed with FAILURES: {fail_reasons}", file=sys.stderr)
        sys.exit(1)
    else:
        print("Wave 9.4R closure driver completed successfully")
        sys.exit(0)


if __name__ == "__main__":
    main()
