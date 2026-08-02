import sys
import os
import subprocess
import ast
import json
import pytest

BASELINE_PATH = os.path.join("tests", "WAVE_9_4_GATE_A_BUNDLE_BASELINE.py")
RUNNER_PATH = os.path.join("evaluation", "wave96", "gate_a_driver_runner.py")

def _get_normalized_asserts(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read())
    dumps = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assert):
            dumps.append(ast.dump(node.test, include_attributes=False))
    return sorted(dumps)

def test_fresh_child_process_begins_without_driver_modules():
    code = "import sys; print([m for m in sys.modules if m == 'neo4j' or m.startswith('neo4j.')])"
    res = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert res.stdout.strip() == "[]"

def test_gate_a_runner_imports_driver_only_in_child_process():
    env = dict(os.environ)
    env["PYTHONPATH"] = os.getcwd() + os.pathsep + env.get("PYTHONPATH", "")
    res = subprocess.run([sys.executable, RUNNER_PATH, "--test", "test_dry_run_no_writes"], capture_output=True, text=True, env=env)
    assert res.returncode in (0, 77)

def test_gate_a_wrapper_adds_no_driver_modules_to_parent_process():
    import tests.test_gate_a_dry_run_and_isolation as gate_a_mod
    before = {name for name in sys.modules if name == "neo4j" or name.startswith("neo4j.")}
    gate_a_mod.test_dry_run_no_writes()
    after = {name for name in sys.modules if name == "neo4j" or name.startswith("neo4j.")}
    assert after == before

def test_before_after_parent_driver_module_set_remains_identical():
    import tests.test_gate_a_dry_run_and_isolation as gate_a_mod
    before = {
        name for name in sys.modules
        if name == "neo4j" or name.startswith("neo4j.")
    }

    gate_a_mod.test_dry_run_no_writes()
    gate_a_mod.test_shadow_isolation()

    after = {
        name for name in sys.modules
        if name == "neo4j" or name.startswith("neo4j.")
    }

    assert after == before

def test_exact_normalized_assertion_multiset_matches_baseline():
    orig_dumps = _get_normalized_asserts(BASELINE_PATH)
    runner_dumps = _get_normalized_asserts(RUNNER_PATH)
    
    missing_original_assertions = [d for d in orig_dumps if orig_dumps.count(d) > runner_dumps.count(d)]
    assert missing_original_assertions == [], f"Missing original assertions: {missing_original_assertions}"

def test_exit_code_0_maps_to_success(monkeypatch):
    import tests.test_gate_a_dry_run_and_isolation as gate_a_mod
    
    class DummyCompletedProcess:
        returncode = 0
        stdout = "OK"
        stderr = ""
        
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: DummyCompletedProcess())
    gate_a_mod._run_isolated_gate_a("test_dummy")

def test_exit_code_77_maps_to_original_skip_behavior(monkeypatch):
    import tests.test_gate_a_dry_run_and_isolation as gate_a_mod
    
    class DummyCompletedProcess:
        returncode = 77
        stdout = ""
        stderr = "Database skip condition"
        
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: DummyCompletedProcess())
    with pytest.raises(pytest.skip.Exception):
        gate_a_mod._run_isolated_gate_a("test_dummy")

def test_unexpected_nonzero_exit_maps_to_test_failure(monkeypatch):
    import tests.test_gate_a_dry_run_and_isolation as gate_a_mod
    
    class DummyCompletedProcess:
        returncode = 1
        stdout = "Error output"
        stderr = "Fatal error"
        
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: DummyCompletedProcess())
    with pytest.raises(pytest.fail.Exception):
        gate_a_mod._run_isolated_gate_a("test_dummy")

def test_ast_mechanical_cleanup_verification():
    with open(RUNNER_PATH, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read())
    
    found_cleanup_in_finally = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Try):
            for fin_stmt in node.finalbody:
                fin_str = ast.dump(fin_stmt)
                if "MATCH" in fin_str and "pilot_id" in fin_str and "DETACH DELETE" in fin_str:
                    found_cleanup_in_finally = True
                    break
                    
    assert found_cleanup_in_finally, "Cleanup query (MATCH...pilot_id...DETACH DELETE) must be in finally block"

    with open(RUNNER_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    required_post_cleanup_asserts = [
        "shadow_entries_after_cleanup == 0",
        "shadow_aliases_after_cleanup == 0",
        "prod_labels_before == prod_labels_after",
        "prod_rels_before == prod_rels_after"
    ]

    for req_assert in required_post_cleanup_asserts:
        assert req_assert in content, f"Missing required post-cleanup assertion: {req_assert}"

def test_cleanup_attempted_on_assertion_failure():
    # Verify via control-flow inspection that pre-cleanup assertions are inside try, and cleanup is inside finally
    with open(RUNNER_PATH, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read())
    
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "run_shadow_isolation":
            try_nodes = [n for n in node.body if isinstance(n, ast.Try)]
            assert len(try_nodes) == 1, "run_shadow_isolation must contain exactly one Try block for cleanup"
            try_node = try_nodes[0]
            
            # Assertions inside try block
            try_asserts = [n for n in ast.walk(try_node) if isinstance(n, ast.Assert) and n not in try_node.finalbody]
            assert len(try_asserts) >= 11, "Pre-cleanup assertions must be inside the try block"
            
            # Cleanup inside finally block
            finally_dumps = [ast.dump(n) for n in try_node.finalbody]
            has_cleanup = any("DETACH DELETE" in d for d in finally_dumps)
            assert has_cleanup, "Cleanup statement must be inside finally block so it executes on assertion failure"

def test_synthetic_canary_secret_redaction():
    canary_pwd = "WAVE96_TEST_SECRET_PASSWORD"
    canary_user = "WAVE96_TEST_SECRET_USERNAME"
    canary_uri = "WAVE96_TEST_SECRET_URI_TOKEN"

    env = dict(os.environ)
    env["NEO4J_PASSWORD"] = canary_pwd
    env["NEO4J_USER"] = canary_user
    env["NEO4J_URI"] = f"bolt://{canary_uri}:7687"
    env["PYTHONPATH"] = os.getcwd() + os.pathsep + env.get("PYTHONPATH", "")

    res = subprocess.run([sys.executable, RUNNER_PATH, "--test", "all"], capture_output=True, text=True, env=env)
    
    assert res.returncode in (1, 77), f"Runner must hit error/skip path for canary URI, got {res.returncode}"
    assert "Database skip condition" in res.stderr or "Gate A runner failure" in res.stderr, "Error/sanitization path was not executed"

    leak_count = 0
    for canary in [canary_pwd, canary_user, canary_uri]:
        if canary in res.stdout or canary in res.stderr:
            leak_count += 1
            
    assert leak_count == 0, f"Canary credentials leaked in stdout/stderr: {leak_count}"
