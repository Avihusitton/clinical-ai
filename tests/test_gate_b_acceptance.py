import json
import os
import pytest

from models.second_order_reasoner import evaluate_fixture

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), 'fixtures', 'gate_b')

def load_fixtures():
    fixtures = []
    if not os.path.exists(FIXTURE_DIR):
        return fixtures
    for filename in os.listdir(FIXTURE_DIR):
        if filename.endswith(".json"):
            fixtures.append(os.path.join(FIXTURE_DIR, filename))
    return fixtures

@pytest.mark.parametrize("fixture_path", load_fixtures())
def test_gate_b_fixture(fixture_path):
    with open(fixture_path, 'r') as f:
        fixture = json.load(f)
        
    result = evaluate_fixture(fixture)
    
    assert result["decision"] == fixture["expected_decision"]
    
    if "blocking_reason" in fixture and fixture["blocking_reason"]:
        assert fixture["blocking_reason"] in result.get("blocking_reasons", [])
        
    if "virtual_path" in fixture:
        assert result.get("virtual_path", False) == fixture["virtual_path"]
        
    if "duplicate_exists" in fixture:
        assert result.get("duplicate_exists", False) == fixture["duplicate_exists"]
