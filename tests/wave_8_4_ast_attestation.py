# -*- coding: utf-8 -*-
"""
tests/wave_8_4_ast_attestation.py
Mechanically derives AST attestation metrics from tests/wave_8_evidence_harness.py.
Zero assigned constants.
"""

import ast
import json
from pathlib import Path


def run_ast_attestation():
    fpath = Path("tests/wave_8_evidence_harness.py")
    raw_code = fpath.read_text(encoding="utf-8")

    ast_parse_success = False
    tree = None
    try:
        tree = ast.parse(raw_code, filename=str(fpath))
        ast_parse_success = True
    except Exception:
        ast_parse_success = False

    lines = raw_code.splitlines()
    scenario_g_comment_count = sum(1 for line in lines if "#" in line and "Scenario G" in line)
    scenario_h_comment_count = sum(1 for line in lines if "#" in line and "Scenario H" in line)

    synthetic_query_subscript_count = 0
    pii_results_append_call_count = 0
    emergency_env_assignment_count = 0
    emergency_env_cleanup_count = 0
    try_finally_count = 0

    if tree:
        for node in ast.walk(tree):
            # Check for c["synthetic_query"] subscript
            if isinstance(node, ast.Subscript):
                if isinstance(node.slice, ast.Constant) and node.slice.value == "synthetic_query":
                    synthetic_query_subscript_count += 1

            # Check for pii_results.append(...)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == "append" and isinstance(node.func.value, ast.Name) and node.func.value.id == "pii_results":
                    pii_results_append_call_count += 1

            # Check for os.environ["CLINICAL_AI_EMERGENCY_DISABLE"] = ...
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Subscript) and isinstance(target.value, ast.Attribute):
                        if target.value.attr == "environ" and isinstance(target.slice, ast.Constant) and target.slice.value == "CLINICAL_AI_EMERGENCY_DISABLE":
                            emergency_env_assignment_count += 1

            # Check for os.environ.pop("CLINICAL_AI_EMERGENCY_DISABLE", ...)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == "pop" and isinstance(node.func.value, ast.Attribute) and node.func.value.attr == "environ":
                    if len(node.args) >= 1 and isinstance(node.args[0], ast.Constant) and node.args[0].value == "CLINICAL_AI_EMERGENCY_DISABLE":
                        emergency_env_cleanup_count += 1

            # Check try-finally
            if isinstance(node, ast.Try) and len(node.finalbody) > 0:
                try_finally_count += 1

    attestation = {
        "ast_parse_success": ast_parse_success,
        "scenario_g_comment_count": scenario_g_comment_count,
        "scenario_h_comment_count": scenario_h_comment_count,
        "synthetic_query_subscript_count": synthetic_query_subscript_count,
        "pii_results_append_call_count": pii_results_append_call_count,
        "emergency_env_assignment_count": emergency_env_assignment_count,
        "emergency_env_cleanup_count": emergency_env_cleanup_count,
        "try_finally_count": try_finally_count,
    }

    out_path = Path("tests/WAVE_8_4_AST_ATTESTATION.json")
    out_path.write_text(json.dumps(attestation, indent=2), encoding="utf-8")
    print(json.dumps(attestation, indent=2))
    return attestation


if __name__ == "__main__":
    run_ast_attestation()
