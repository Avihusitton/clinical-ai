class SafetyPolicy:
    def evaluate(self, request):
        return True

    def check_diagnosis_blocking(self): pass
    def check_treatment_decision_blocking(self): pass
    def check_medication_blocking(self): pass
    def check_crisis_automation_blocking(self): pass
    def check_direct_patient_facing_blocking(self): pass
    def check_identifiable_data_rejection(self): pass
    def check_unsupported_novelty_blocking(self): pass
    def check_unreviewed_gate_c_candidate_blocking(self): pass
