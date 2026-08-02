import sys
import os
import subprocess
import pytest

RUNNER_PATH = os.path.join("evaluation", "wave96", "gate_a_driver_runner.py")

def _run_isolated_gate_a(test_name: str):
    env = dict(os.environ)
    proj_root = os.getcwd()
    env["PYTHONPATH"] = proj_root + os.pathsep + env.get("PYTHONPATH", "")
    cmd = [sys.executable, RUNNER_PATH, "--test", test_name]
    res = subprocess.run(cmd, capture_output=True, text=True, check=False, env=env)
    if res.returncode == 0:
        return
    elif res.returncode == 77:
        pytest.skip(res.stderr or res.stdout or f"Skipped: {test_name}")
    else:
        pytest.fail(
            f"Gate A isolated runner failed for {test_name} with exit code {res.returncode}:\n"
            f"STDOUT:\n{res.stdout}\n"
            f"STDERR:\n{res.stderr}"
        )

def test_dry_run_no_writes(monkeypatch=None):
    _run_isolated_gate_a("test_dry_run_no_writes")

def test_shadow_isolation():
    _run_isolated_gate_a("test_shadow_isolation")
