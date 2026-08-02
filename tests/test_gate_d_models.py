import pytest
from models.gate_d import ConsultationRequest, ConsultationResponse, AuditEvent

def test_consultation_request_model():
    req = ConsultationRequest(
        case_id="TEST_001",
        request_type="ALLOWED",
        synthetic_input="What are evidence-based interventions for anxiety?"
    )
    assert req.case_id == "TEST_001"
    assert req.request_type == "ALLOWED"

def test_consultation_response_model():
    res = ConsultationResponse(
        case_id="TEST_001",
        allow_or_block="ALLOW",
        safety_boundary="In-scope",
        uncertainty_behavior="Disclose",
        evidence_behavior="Cite",
        human_action="Review",
        audit_event="EVENT_OK"
    )
    assert res.allow_or_block == "ALLOW"

def test_audit_event_model():
    event = AuditEvent(
        event_type="UNAUTHORIZED_WRITE",
        case_id="AUDIT_001",
        details="Attempted graph write"
    )
    assert event.event_type == "UNAUTHORIZED_WRITE"
