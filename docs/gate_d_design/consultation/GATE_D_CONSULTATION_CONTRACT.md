# Gate D: Clinical Consultation Contract

## Overview
This document defines the overarching design and constraints for Gate D, focusing on a therapist-facing consultation experience. The system is designed to act as an assistant that provides relevant knowledge and structure, while maintaining full human authority. The system operates strictly in a support capacity and cannot supersede or mimic human clinical judgment.

## Goal
Define a therapist-facing consultation experience with full human authority.

## Allowed System Functions
- **Organize Info:** Structure and present the provided consultation context.
- **Identify Relevant Official Concepts:** Map queries and context to established, official clinical concepts.
- **Retrieve Reviewed Knowledge:** Fetch evidence and information from verified, reviewed knowledge bases.
- **Present Possible Connections/Alternative Interpretations:** Suggest potential links or different ways of interpreting the context (always presented as possibilities, not facts).
- **Suggest Reflection Questions:** Provide optional questions the therapist might consider to explore the case further.
- **Display Evidence/Uncertainty:** Clearly link possibilities to evidence and explicitly state when information is uncertain or unknown.
- **Identify Missing Info/Contradictions:** Point out gaps or conflicting data in the provided context.
- **Offer Reviewed Exercises:** Suggest optional, pre-reviewed therapeutic exercises relevant to the context.
- **Allow Therapist to Reject/Edit:** Ensure the therapist has the final say and can modify or dismiss any system-generated output.

## Prohibited System Functions
- **Diagnose:** The system must never state or formally suggest a diagnosis.
- **Decide Treatment:** The system must never prescribe or dictate a treatment plan.
- **Replace Clinical Judgment:** The system must not present its outputs as definitive conclusions.
- **Give Autonomous Treatment Instructions:** No direct, automated treatment instructions may be generated.
- **Recommend Medication:** The system must never suggest, recommend, or discuss specific medication interventions as recommendations.
- **Provide Crisis-Management Automation:** Crisis situations must rely on human protocols; the system cannot automate crisis management.
- **Communicate with Patients:** The system is exclusively for therapist use and must not interact directly with patients.
- **Claim Unsupported Certainty:** The system must not use language that implies absolute certainty.
- **Hide Uncertainty:** The system must explicitly surface its limitations and uncertainties.
- **Use Live Identifiable Patient Data:** The system must operate on de-identified or synthetic data; no live identifiable patient health information (PHI) is permitted.
- **Convert Speculative Novelty into Approved Knowledge:** The system cannot establish new clinical knowledge; it must only retrieve existing, reviewed knowledge.

## Required Entities
- `ConsultationRequest`
- `ConsultationContext`
- `ConsultationQuestion`
- `ConsultationResponse`
- `ClinicalPossibility`
- `EvidenceReference`
- `UncertaintyStatement`
- `AlternativeInterpretation`
- `SafetyBoundary`
- `TherapistDecision`
- `TherapistFeedback`
- `ConsultationAuditEvent`
