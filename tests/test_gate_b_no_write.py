import ast
import os
import pytest

def get_python_files(directory):
    if not os.path.exists(directory):
        return
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                yield os.path.join(root, file)

def test_no_graph_write_methods():
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    models_dir = os.path.join(project_root, 'models')
    
    forbidden_methods = ['create', 'update', 'delete', 'merge', 'write', 'push', 'commit', 'save']
    
    checked_files = 0
    for py_file in get_python_files(models_dir):
        if "relation_policy" not in py_file and "second_order_reasoner" not in py_file:
            continue
            
        checked_files += 1
        with open(py_file, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read(), filename=py_file)
            
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                assert not any(forbidden in node.name.lower() for forbidden in forbidden_methods), \
                    f"Write method '{node.name}' found in {py_file}. Gate B must be read-only."
                    
    # It's fine if checked_files == 0 initially, meaning TDD hasn't created them yet.

def test_no_neo4j_driver_required():
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    models_dir = os.path.join(project_root, 'models')
    
    for py_file in get_python_files(models_dir):
        if "relation_policy" not in py_file and "second_order_reasoner" not in py_file:
            continue
            
        with open(py_file, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "neo4j" not in content.lower(), f"Neo4j driver dependency found in {py_file}. Gate B must not require Neo4j."
            assert "cypher" not in content.lower(), f"Cypher logic found in {py_file}. Gate B must be engine-agnostic."
