class EvidenceFilter:
    def filter_evidence(self, request):
        return True
    
    def check_evidence_visibility(self): pass
    def check_uncertainty_visibility(self): pass
    def check_missing_provenance(self): pass
    def check_contradictory_evidence(self): pass
