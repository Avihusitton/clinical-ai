from typing import List
from .models import EvidenceReference
from .exceptions import UnauthorizedDataError, EvidenceMissingError

class EvidenceFilter:
    def __init__(self):
        pass

    def filter_evidence(self, evidence_list: List[EvidenceReference]) -> List[EvidenceReference]:
        filtered = []
        for evidence in evidence_list:
            if evidence.source_type == "Gate C Novelty" and not evidence.is_reviewed:
                raise UnauthorizedDataError(f"Unreviewed Gate C novelty (Source: {evidence.source_id}) cannot be used as consultation evidence.")
            filtered.append(evidence)
        return filtered

    def ensure_supported_claims(self, claims: List[str], available_evidence: List[EvidenceReference]):
        if not available_evidence and claims:
            raise EvidenceMissingError("Cannot make claims without supporting reviewed evidence.")
