#!/usr/bin/env python
"""Baseline diff analysis script."""
import json, hashlib, os, sys

os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

files = ["tests/test_gate_cd_boundary.py", "tests/test_gate_a_dry_run_and_isolation.py"]
results = []

# Check git availability
import subprocess

for rel_path in files:
    with open(rel_path, "r", encoding="utf-8") as f:
        working = f.read()
    
    git_result = subprocess.run(
        ["git", "show", f"feat/wave8-shadow-wiring:{rel_path}"],
        capture_output=True, text=True, shell=False
    )
    git_available = git_result.returncode == 0
    
    with open("PROJECT_CODE_BUNDLE.txt", "r", encoding="utf-8") as f:
        bundle = f.read()
    
    lines = bundle.splitlines(keepends=True)
    begin_idx = None
    end_idx = None
    for idx, line in enumerate(lines):
        if line.startswith("BEGIN FILE:"):
            path = line[len("BEGIN FILE:"):].strip().replace("\\", "/")
            if path == rel_path.replace("\\", "/"):
                begin_idx = idx
        elif line.startswith("END FILE:"):
            path = line[len("END FILE:"):].strip().replace("\\", "/")
            if path == rel_path.replace("\\", "/"):
                end_idx = idx
    
    bundle_available = (begin_idx is not None and end_idx is not None)
    
    if bundle_available:
        raw = "".join(lines[begin_idx+1:end_idx])
        
        def normalize(t):
            t = t.replace("\ufeff", "")
            t = t.replace("\r\n", "\n").replace("\r", "\n")
            if not t.endswith("\n"):
                t = t + "\n"
            return t
        
        n_bundle = normalize(raw)
        n_working = normalize(working)
        
        b_lines = n_bundle.splitlines()
        w_lines = n_working.splitlines()
        
        first_diff = None
        b_line = None
        w_line = None
        for i in range(min(len(b_lines), len(w_lines))):
            if b_lines[i] != w_lines[i]:
                first_diff = i + 1
                b_line = b_lines[i]
                w_line = w_lines[i]
                break
        if first_diff is None and len(b_lines) != len(w_lines):
            first_diff = min(len(b_lines), len(w_lines)) + 1
            b_line = b_lines[first_diff-1] if first_diff <= len(b_lines) else "N/A (past end)"
            w_line = w_lines[first_diff-1] if first_diff <= len(w_lines) else "N/A (past end)"
        
        match = (n_bundle == n_working)
    else:
        match = False
        first_diff = None
        b_line = None
        w_line = None
    
    # Check git status
    git_status = subprocess.run(
        ["git", "status", "--porcelain=v1", "--", rel_path],
        capture_output=True, text=True, shell=False
    )
    modified_in_git = bool(git_status.stdout.strip())
    
    entry = {
        "working_path": rel_path,
        "git_source_available": git_available,
        "bundle_source_available": bundle_available,
        "selected_independent_source": "git" if git_available else ("bundle" if bundle_available else "none"),
        "first_differing_line": first_diff,
        "working_line": w_line,
        "baseline_line": b_line,
        "normalized_match": match,
        "working_file_modified_in_git_status": modified_in_git,
        "protected_file_change_required": not match
    }
    results.append(entry)

output_path = "tests/WAVE_9_4R_BASELINE_DIFF_ANALYSIS.json"
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)

print(json.dumps(results, indent=2))
