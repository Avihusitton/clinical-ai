import pytest
import os
import sys
import subprocess
from dotenv import load_dotenv

def test_real_shadow_pilot():
    load_dotenv()
    
    allow_pilot = os.environ.get('ALLOW_GATE_A_SHADOW_PILOT', 'false').lower() == 'true'
    environment = os.environ.get('NEO4J_ENVIRONMENT', '')
    configured_test_db = os.environ.get('NEO4J_TEST_DATABASE', '')
    gate_a_final_signoff = os.environ.get('GATE_A_FINAL_SIGNOFF', 'false').lower() == 'true'
    
    if gate_a_final_signoff:
        assert environment == "test"
        assert allow_pilot is True
        assert configured_test_db != ""
    else:
        if not allow_pilot and environment != "test":
            pytest.skip("Real Shadow Pilot is not allowed by configuration")
            
    # Static guard against unrestricted cleanup
    with open(__file__, 'r', encoding='utf-8') as f:
        src = f.read()
    assert 'MATCH (n {pilot_id: ' + '$pid}) DETACH DELETE n' not in src

    runner_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "evaluation",
        "wave95",
        "real_shadow_pilot_runner.py"
    )

    res = subprocess.run(
        [sys.executable, runner_path],
        capture_output=True,
        text=True,
        env=os.environ.copy()
    )

    if res.returncode == 77:
        pytest.skip("Real Shadow Pilot is not allowed by configuration")

    if res.returncode != 0:
        err_msg = res.stderr or res.stdout or f"Subprocess exited with code {res.returncode}"
        pytest.fail(f"Real Shadow Pilot subprocess failed with exit code {res.returncode}:\n{err_msg}")

    assert res.returncode == 0
