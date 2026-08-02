import re
from .exceptions import PIIRejectedError, SafetyViolationError
from .models import SafetyBoundary, ConsultationRequest
from typing import List

class SafetyPolicy:
    def __init__(self):
        # Basic deterministic regex for PII (e.g. SSN, Phone, Emails)
        self.pii_patterns = [
            re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
            re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
            re.compile(r'\b\d{3}-\d{3}-\d{4}\b')
        ]
        
        self.forbidden_keywords = [
            "diagnosis", "diagnose", "prescribe", "medication", 
            "treatment decision", "suicide", "crisis"
        ]

    def enforce_no_pii(self, text: str):
        for pattern in self.pii_patterns:
            if pattern.search(text):
                raise PIIRejectedError("PII detected in request. Patient data must be fully anonymized.")
                
    def check_for_forbidden_actions(self, text: str):
        text_lower = text.lower()
        for kw in self.forbidden_keywords:
            if kw in text_lower:
                raise SafetyViolationError(
                    f"Safety violation: Request implies forbidden action '{kw}'. "
                    "No diagnosis, treatment decision, medication recommendation, or crisis automation is allowed."
                )

    def apply_safety_boundaries(self, request: ConsultationRequest) -> List[SafetyBoundary]:
        self.enforce_no_pii(request.question.query_text)
        self.check_for_forbidden_actions(request.question.query_text)
        
        boundaries = [
            SafetyBoundary("No Diagnosis", "Engine will not provide any medical or psychiatric diagnosis.", enforced=True),
            SafetyBoundary("No Treatment Decisions", "Engine will not make treatment decisions. Therapist retains full decision authority.", enforced=True),
            SafetyBoundary("No Direct Patient Output", "Engine output is strictly for the therapist, not for patient consumption.", enforced=True)
        ]
        return boundaries
