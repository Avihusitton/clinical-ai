import sys
import os
import glob
import py_compile
import json
import hashlib
import subprocess
import time

def run_step_3_py_compile():
    print("--- Step 3: py_compile ---")
    files = (
        glob.glob("gate_c/*.py") +
        glob.glob("gate_d/*.py") +
        glob.glob("gate_cd_boundary/*.py") +
        glob.glob("tests/test_gate_c_*.py") +
        glob.glob("tests/test_gate_d_*.py") +
        glob.glob("tests/test_gate_cd_*.py")
    )
    print(f"Compiling {len(files)} files...")
    for f in files:
        py_compile.compile(f, doraise=True)
    print(f"Successfully compiled all {len(files)} files.\n")

def run_step_4_fixture_validation():
    print("--- Step 4: Fixture Validation ---")
    c_fixture = "tests/fixtures/gate_c/novelty_cases.jsonl"
    d_fixture = "tests/fixtures/gate_d/consultation_cases.jsonl"

    with open(c_fixture, "r", encoding="utf-8") as f:
        c_lines = [line for line in f if line.strip()]
    with open(d_fixture, "r", encoding="utf-8") as f:
        d_lines = [line for line in f if line.strip()]

    c_count = len(c_lines)
    d_count = len(d_lines)

    print(f"gate_c fixture count: {c_count}")
    print(f"gate_d fixture count: {d_count}")

    assert c_count == 60, f"Expected 60 gate_c cases, got {c_count}"
    assert d_count == 60, f"Expected 60 gate_d cases, got {d_count}"
    print("Fixture counts validated successfully.\n")
    return c_count, d_count

def run_step_5_pytest():
    print("--- Step 5: Run full test suite ---")
    test_files = [
        "tests/test_gate_c_models.py",
        "tests/test_gate_c_novelty_engine.py",
        "tests/test_gate_c_known_knowledge.py",
        "tests/test_gate_c_review_queue.py",
        "tests/test_gate_c_explainability.py",
        "tests/test_gate_c_acceptance.py",
        "tests/test_gate_c_no_write.py",
        "tests/test_gate_d_models.py",
        "tests/test_gate_d_consultation_engine.py",
        "tests/test_gate_d_safety_policy.py",
        "tests/test_gate_d_language_policy.py",
        "tests/test_gate_d_audit_trail.py",
        "tests/test_gate_d_evidence_filter.py",
        "tests/test_gate_d_acceptance.py",
        "tests/test_gate_d_no_write.py",
        "tests/test_gate_cd_boundary.py",
        "tests/test_gate_cd_safety_boundary.py",
    ]

    cmd = [sys.executable, "-m", "pytest"] + test_files + ["-v"]
    print(f"Executing: {' '.join(cmd)}")

    start_time = time.time()
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    duration = time.time() - start_time

    output_path = "tests/WAVE_4_FINAL_PYTEST_OUTPUT.txt"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(result.stdout)

    print(f"Pytest exit code: {result.returncode}")
    print(f"Saved complete output to {output_path}")
    print(f"Duration: {duration:.2f}s")

    return result.returncode, result.stdout, duration

def run_step_6_hash_verification():
    print("\n--- Step 6: Hash Verification ---")
    with open("initial_hashes.json", "r", encoding="utf-8") as f:
        initial_hashes = json.load(f)

    mismatches = []
    for filepath, expected_hash in initial_hashes.items():
        # Normalize path
        norm_path = os.path.normpath(filepath)
        if not os.path.exists(norm_path):
            # Check relative path
            rel_path = os.path.relpath(filepath, "C:\\Avihusitton\\clinical_ai")
            if os.path.exists(rel_path):
                norm_path = rel_path
            else:
                mismatches.append((filepath, "FILE_MISSING", expected_hash))
                continue
        with open(norm_path, "rb") as f:
            content = f.read()
            actual_hash = hashlib.sha256(content).hexdigest().upper()
        if actual_hash != expected_hash.upper():
            mismatches.append((norm_path, actual_hash, expected_hash))

    print(f"Checked {len(initial_hashes)} protected/frozen files against initial_hashes.json.")
    if mismatches:
        print(f"WARNING: {len(mismatches)} hash mismatches found!")
        for path, act, exp in mismatches:
            print(f"  {path}: actual {act} != expected {exp}")
    else:
        print("All initial_hashes.json files are UNCHANGED.")

    # Read-only files check
    read_only_files = [
        "retrieval.py", "ingestion_pipeline.py", "build_glossary.py",
        "run_full_pipeline.py", "master_dashboard.py", "review_app.py",
        "config.py", "llm_client.py", "relation_policy.py", "second_order_reasoner.py"
    ]
    for ro_file in read_only_files:
        assert os.path.exists(ro_file), f"Read-only file missing: {ro_file}"
    print(f"All {len(read_only_files)} read-only core files verified present.\n")

    return len(mismatches)

if __name__ == "__main__":
    run_step_3_py_compile()
    c_count, d_count = run_step_4_fixture_validation()
    exit_code, pytest_out, duration = run_step_5_pytest()
    mismatches = run_step_6_hash_verification()

    print("=== SUMMARY ===")
    print(f"Exit code: {exit_code}")
    print(f"Duration: {duration:.2f}s")
    print(f"Gate C cases: {c_count}")
    print(f"Gate D cases: {d_count}")
    print(f"Hash mismatches: {mismatches}")
