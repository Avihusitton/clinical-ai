# -*- coding: utf-8 -*-
import glob
import ast
import os


FORBIDDEN_SHADOW_IMPORTS = {
    "neo4j",
    "requests",
    "httpx",
    "urllib",
    "socket",
    "subprocess",
    "llm_client",
    "streamlit",
}


def test_shadow_wiring_package_imports_isolation():
    shadow_files = glob.glob("shadow_wiring/*.py")
    assert len(shadow_files) > 0, "No shadow_wiring Python files found!"

    for fpath in shadow_files:
        with open(fpath, "r", encoding="utf-8") as fp:
            tree = ast.parse(fp.read(), filename=fpath)

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.name.split(".")[0]
                    assert name not in FORBIDDEN_SHADOW_IMPORTS, f"File {fpath} illegally imports {name}"
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    mod = node.module.split(".")[0]
                    assert mod not in FORBIDDEN_SHADOW_IMPORTS, f"File {fpath} illegally imports from {mod}"


def test_unmodified_protected_system_components():
    protected = [
        "config.py",
        "llm_client.py",
        "ingestion_pipeline.py",
        "build_glossary.py",
        "data/glossary.json",
        "data/exercises.json",
    ]
    for p in protected:
        assert os.path.exists(p), f"Protected component {p} is missing!"
