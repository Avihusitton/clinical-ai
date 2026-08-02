import os
import sys
import subprocess

def main():
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    os.chdir(root_dir)

    nodes = [
        "tests/test_gate_cd_boundary.py::TestNoProductionImports::test_gate_cd_boundary_does_not_import_neo4j",
        "tests/test_wave95_neo4j_isolation.py::test_neo4j_absent_from_parent_sys_modules_before_pilot",
        "tests/test_wave95_neo4j_isolation.py::test_neo4j_remains_absent_from_parent_sys_modules_after_pilot",
        "tests/test_wave95_neo4j_isolation.py::test_gate_test_passes_after_pilot",
        "tests/test_wave95_neo4j_isolation.py::test_gate_test_passes_alone"
    ]

    cmd = [sys.executable, "-m", "pytest"] + nodes + ["-vv", "-ra"]
    print(f"Running joint reproduction: {' '.join(cmd)}")
    res = subprocess.run(cmd, capture_output=True, text=True)

    combined_output = res.stdout + res.stderr
    with open("tests/WAVE_9_5_FAILURE_REPRODUCTION_OUTPUT.txt", "w", encoding="utf-8") as f:
        f.write(combined_output)

    with open("tests/WAVE_9_5_FAILURE_REPRODUCTION_EXIT_CODE.txt", "w", encoding="utf-8") as f:
        f.write(str(res.returncode) + "\n")

    print(f"Joint reproduction exit code: {res.returncode}")

if __name__ == "__main__":
    main()
