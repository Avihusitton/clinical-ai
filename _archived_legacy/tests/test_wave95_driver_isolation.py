import sys
import os
import subprocess
import pytest
from tests.test_real_shadow_pilot import test_real_shadow_pilot

def test_fresh_process_has_no_neo4j_driver():
    code = (
        "import sys; "
        "driver_modules = {name for name in sys.modules if name == 'neo4j' or name.startswith('neo4j.')}; "
        "assert driver_modules == set(), f'Driver modules present in fresh process: {driver_modules}'"
    )
    cmd = [sys.executable, "-c", code]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, f"Fresh process check failed: {res.stderr}"

def test_pilot_wrapper_introduces_no_new_parent_driver_modules():
    before = {
        name for name in sys.modules
        if name == "neo4j" or name.startswith("neo4j.")
    }
    try:
        test_real_shadow_pilot()
    except pytest.skip.Exception:
        pass
    after = {
        name for name in sys.modules
        if name == "neo4j" or name.startswith("neo4j.")
    }
    assert after == before, f"Pilot wrapper introduced new driver modules into parent process: {after - before}"

def test_pilot_subprocess_runner_executes():
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
    assert res.returncode in (0, 77), f"Runner failed unexpectedly with exit code {res.returncode}: {res.stderr}"

def test_pilot_runner_functional_assertions():
    runner_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "evaluation",
        "wave95",
        "real_shadow_pilot_runner.py"
    )
    with open(runner_path, "r", encoding="utf-8") as f:
        src = f.read()
        
    expected_assertions = [
        "assert fixture_card_count == 3",
        "assert dry_run_write_query_count == 0",
        "assert shadow_entries_after_load == 3",
        "assert shadow_aliases_after_load > 0",
        "assert shadow_alias_of_after_load > 0",
        "assert cross_boundary_relationships == 0",
        "assert orphan_shadow_aliases == 0",
        "assert shadow_entries_missing_pilot_id == 0",
        "assert shadow_aliases_missing_pilot_id == 0",
        "assert shadow_aliases_linked_to_wrong_pilot == 0",
        "assert second_load_new_entries == 0",
        "assert second_load_updated_entries == 0",
        "assert second_load_unchanged_entries == 3",
        "assert shadow_entries_after_cleanup == 0",
        "assert shadow_aliases_after_cleanup == 0",
        "assert prod_labels_before == prod_labels_after",
        "assert prod_rels_before == prod_rels_after",
    ]
    for assertion in expected_assertions:
        assert assertion in src, f"Missing functional assertion in runner: {assertion}"

def test_subprocess_nonzero_exit_causes_test_failure(monkeypatch):
    def mock_run(*args, **kwargs):
        class MockCompletedProcess:
            returncode = 1
            stdout = ""
            stderr = "Simulated Neo4j connection failure"
        return MockCompletedProcess()
        
    monkeypatch.setattr(subprocess, "run", mock_run)
    monkeypatch.setenv("ALLOW_GATE_A_SHADOW_PILOT", "true")
    monkeypatch.setenv("NEO4J_ENVIRONMENT", "test")
    
    with pytest.raises(pytest.fail.Exception) as excinfo:
        test_real_shadow_pilot()
    assert "Real Shadow Pilot subprocess failed with exit code 1" in str(excinfo.value)
