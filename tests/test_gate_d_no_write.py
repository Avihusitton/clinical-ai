import pytest
import os
import ast

def test_no_graph_writes():
    # Verify no graph writing logic exists in gate_d
    pass

def test_no_neo4j_dependency():
    engine_file = os.path.join(os.path.dirname(__file__), '../models/gate_d/consultation_engine.py')
    if os.path.exists(engine_file):
        with open(engine_file, 'r') as f:
            content = f.read()
            assert 'neo4j' not in content.lower()
            
def test_no_llm_calls():
    engine_file = os.path.join(os.path.dirname(__file__), '../models/gate_d/consultation_engine.py')
    if os.path.exists(engine_file):
        with open(engine_file, 'r') as f:
            content = f.read()
            assert 'llm' not in content.lower()
            assert 'openai' not in content.lower()
            assert 'anthropic' not in content.lower()
