from pydantic import BaseModel

class ConsultationRequest(BaseModel):
    case_id: str
    request_type: str
    synthetic_input: str

class ConsultationResponse(BaseModel):
    case_id: str
    allow_or_block: str
    safety_boundary: str
    uncertainty_behavior: str
    evidence_behavior: str
    human_action: str
    audit_event: str

class AuditEvent(BaseModel):
    event_type: str
    case_id: str
    details: str
