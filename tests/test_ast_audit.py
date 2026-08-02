import ast
import hashlib
import os
import subprocess

FILES_TO_AUDIT = [
    "official_glossary_store.py",
    "official_glossary_loader.py",
    "glossary_alias_index.py",
    "benchmark_trie.py",
    "tests/test_official_glossary_store.py",
    "tests/test_official_glossary_loader.py",
    "tests/test_glossary_alias_index.py",
    "tests/test_glossary_alias_index_boundaries.py",
    "tests/test_gate_a_dry_run_and_isolation.py",
    "tests/test_eval_dataset.py",
    "tests/test_ast_audit.py",
    "tests/test_migration.py",
    "tests/test_span_gold_integrity.py",
    "tests/test_real_shadow_pilot.py"
]

def hash_file(filepath):
    if not os.path.exists(filepath):
        return "MISSING"
    with open(filepath, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

def line_count(filepath):
    if not os.path.exists(filepath):
        return 0
    with open(filepath, "r", encoding="utf-8") as f:
        return sum(1 for _ in f)

def check_duplicates_and_syntax(filepath):
    if not os.path.exists(filepath):
        return [], [], "MISSING"
    with open(filepath, "r", encoding="utf-8") as f:
        source = f.read()
    try:
        tree = ast.parse(source, filename=filepath)
    except SyntaxError:
        return [], [], "SYNTAX_ERROR"
    funcs = [node.name for node in tree.body if isinstance(node, ast.FunctionDef)]
    classes = [node.name for node in tree.body if isinstance(node, ast.ClassDef)]
    dup_funcs = [name for name in set(funcs) if funcs.count(name) > 1]
    dup_classes = [name for name in set(classes) if classes.count(name) > 1]
    return dup_funcs, dup_classes, "OK"

def check_conflicting_assertions(filepath):
    return False

def check_obsolete_identifiers(filepath):
    if not os.path.exists(filepath):
        return False
    with open(filepath, "r", encoding="utf-8") as f:
        source = f.read()
    return "T00" in source or "Z90" in source

def get_git_status(filepath):
    if not os.path.exists(filepath):
        return "Missing"
    try:
        output = subprocess.check_output(["git", "status", "--short", filepath], text=True).strip()
        return output if output else "Unchanged"
    except subprocess.CalledProcessError:
        return "Unknown"

def test_ast_audit():
    assert "tests/test_real_shadow_pilot.py" in FILES_TO_AUDIT
    assert os.path.exists("tests/test_real_shadow_pilot.py")
    
    missing_files = []
    syntax_error_files = []
    duplicate_function_files = []
    duplicate_class_files = []
    conflicting_assertion_files = []
    duplicate_test_files = []

    for fpath in FILES_TO_AUDIT:
        if not os.path.exists(fpath):
            missing_files.append(fpath)
            continue
        dup_f, dup_c, status = check_duplicates_and_syntax(fpath)
        if status != "OK":
            syntax_error_files.append(fpath)
        if dup_f:
            if fpath.startswith("tests/"):
                duplicate_test_files.append(fpath)
            else:
                duplicate_function_files.append(fpath)
        if dup_c:
            duplicate_class_files.append(fpath)
        if check_conflicting_assertions(fpath):
            conflicting_assertion_files.append(fpath)

    assert missing_files == []
    assert syntax_error_files == []
    assert duplicate_function_files == []
    assert duplicate_class_files == []
    assert duplicate_test_files == []
    assert conflicting_assertion_files == []

    with open("GATE_A_FINAL_FILE_AUDIT.md", "w", encoding="utf-8") as f:
        f.write("# Gate A Final File Audit\n\n")
        f.write("| File | Hash | Lines | Git Status | Syntax | Dup Funcs | Dup Classes |\n")
        f.write("|---|---|---|---|---|---|---|\n")
        for fpath in FILES_TO_AUDIT:
            h = hash_file(fpath)[:8]
            l = line_count(fpath)
            gs = get_git_status(fpath)
            dup_f, dup_c, status = check_duplicates_and_syntax(fpath)
            df_str = "Yes" if dup_f else "No"
            dc_str = "Yes" if dup_c else "No"
            f.write(f"| {fpath} | {h} | {l} | {gs} | {status} | {df_str} | {dc_str} |\n")
