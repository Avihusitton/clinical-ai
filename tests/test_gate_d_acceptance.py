import pytest
import json
import os
from models.gate_d import ConsultationEngine, ConsultationRequest

def get_fixtures():
    fixture_path = os.path.join(os.path.dirname(__file__), 'fixtures', 'gate_d', 'consultation_cases.jsonl')
    cases = []
    if os.path.exists(fixture_path):
        with open(fixture_path, 'r', encoding='utf-8-sig') as f:
            for line in f:
                if line.strip():
                    cases.append(json.loads(line))
    return cases

@pytest.fixture(scope="module")
def engine():
    return ConsultationEngine()

def test_acceptance_cases(engine):
    cases = get_fixtures()
    assert len(cases) == 60, f"Expected 60 cases, got {len(cases)}"
    
    allowed_count = 0
    blocked_count = 0
    uncertain_count = 0
    audit_count = 0
    
    for case in cases:
        if case["request_type"] == "ALLOWED":
            allowed_count += 1
        elif case["request_type"] == "BLOCKED":
            blocked_count += 1
        elif case["request_type"] == "UNCERTAINTY":
            uncertain_count += 1
        elif case["request_type"] == "AUDIT":
            audit_count += 1
            
        req = ConsultationRequest(
            case_id=case["case_id"],
            request_type=case["request_type"],
            synthetic_input=case["synthetic_input"]
        )
        
        response = engine.process(req)
        
        assert response.allow_or_block == case["expected_allow_or_block"]
        assert response.safety_boundary == case["expected_safety_boundary"]
        assert response.uncertainty_behavior == case["expected_uncertainty_behavior"]
        assert response.evidence_behavior == case["expected_evidence_behavior"]
        assert response.human_action == case["expected_human_action"]
        assert response.audit_event == case["expected_audit_event"]

    assert allowed_count == 15, f"Expected 15 allowed cases, got {allowed_count}"
    assert blocked_count == 15, f"Expected 15 blocked cases, got {blocked_count}"
    assert uncertain_count == 15, f"Expected 15 uncertainty cases, got {uncertain_count}"
    assert audit_count == 15, f"Expected 15 audit cases, got {audit_count}"
