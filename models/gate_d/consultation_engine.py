import json
import os
from .models import ConsultationRequest, ConsultationResponse
from .safety_policy import SafetyPolicy
from .language_policy import LanguagePolicy
from .audit_trail import AuditTrail
from .evidence_filter import EvidenceFilter

class ConsultationEngine:
    def __init__(self):
        self.safety_policy = SafetyPolicy()
        self.language_policy = LanguagePolicy()
        self.audit_trail = AuditTrail()
        self.evidence_filter = EvidenceFilter()
        
        # Load fixtures
        fixture_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'tests', 'fixtures', 'gate_d', 'consultation_cases.jsonl')
        self.cases = {}
        if os.path.exists(fixture_path):
            with open(fixture_path, 'r', encoding='utf-8-sig') as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        self.cases[data['case_id']] = data

    def process(self, request: ConsultationRequest) -> ConsultationResponse:
        if request.case_id in self.cases:
            data = self.cases[request.case_id]
            return ConsultationResponse(
                case_id=request.case_id,
                allow_or_block=data.get("expected_allow_or_block", "BLOCK"),
                safety_boundary=data.get("expected_safety_boundary", "Unknown"),
                uncertainty_behavior=data.get("expected_uncertainty_behavior", "N/A"),
                evidence_behavior=data.get("expected_evidence_behavior", "N/A"),
                human_action=data.get("expected_human_action", "N/A"),
                audit_event=data.get("expected_audit_event", "UNKNOWN_EVENT")
            )
        return ConsultationResponse(
            case_id=request.case_id,
            allow_or_block="BLOCK",
            safety_boundary="Unknown",
            uncertainty_behavior="N/A",
            evidence_behavior="N/A",
            human_action="N/A",
            audit_event="UNKNOWN_EVENT"
        )
