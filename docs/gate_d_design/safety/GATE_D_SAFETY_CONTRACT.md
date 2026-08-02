# Gate D Safety Contract

## Overview
This document defines the core safety domains and explicitly blocked scenarios for the internal therapist pilot. It serves as the foundational safety contract for Gate D.

## Required Safety Domains
1. **Human Decision Authority**: The system must never make decisions; all outputs are advisory and must be reviewed by a human therapist.
2. **Scope Boundaries**: The system operates strictly within clinical consultation support and does not perform tasks outside this scope.
3. **Data Minimization**: The system requests and retains only the minimum data necessary for the consultation.
4. **PII Rejection**: The system must aggressively detect and reject any Personally Identifiable Information (PII).
5. **Synthetic and Anonymized Cases**: During the pilot, only synthetic or rigorously anonymized cases are permitted.
6. **Uncertainty Disclosure**: The system must explicitly state when information is uncertain, incomplete, or ambiguous.
7. **Source Visibility**: All claims and information must be traceable to their source evidence (provenance).
8. **Novelty Separation**: Novel or inferred insights must be clearly separated from established factual evidence.
9. **Therapist Override**: The therapist must always have the ability to override, ignore, or correct the system's output.
10. **Feedback and Correction**: The system must support mechanisms for the therapist to provide feedback and correct errors.
11. **Audit Logging**: All requests, responses, decisions, and system actions must be immutably logged for auditing.
12. **Feature Flags**: All new capabilities must be gated by feature flags for controlled rollout and immediate deactivation.
13. **Legacy Fallback**: A functional legacy fallback mechanism must be available in case of system failure or unexpected behavior.
14. **Rollback**: Procedures must be in place for immediate rollback to a known safe state.
15. **Access Control**: Strict role-based access control (RBAC) ensuring only authorized internal therapists have access.
16. **Incident Reporting**: A clear, frictionless mechanism for reporting safety incidents or anomalous behavior.
17. **Clinical Reviewer Sign-off**: All system behavior changes affecting clinical output require explicit sign-off from designated clinical reviewers.

## Required Blocked Scenarios
The system must automatically block and flag the following scenarios:
- **Identifiable patient info**: Any input containing potential PII or PHI.
- **Direct diagnosis request**: Requests asking the system to diagnose a patient.
- **Autonomous treatment request**: Requests for the system to prescribe or dictate a treatment plan.
- **Medication request**: Requests involving prescription or medical advice outside the scope of therapy.
- **Crisis automation**: Any indication of a crisis (e.g., self-harm, harm to others) must trigger an immediate block and direct the user to established crisis protocols.
- **Direct patient-facing response**: Requests to generate responses meant to be sent directly to a patient without review.
- **Request to conceal uncertainty/invent evidence**: Any prompt attempting to force the system to sound confident when uncertain or to hallucinate evidence.
- **Unsupported novelty as fact**: Presenting inferred or novel ideas as established clinical facts.
- **Bypassing therapist approval**: Any workflow that attempts to skip the therapist review step.
- **Missing provenance**: Responses where the source of the clinical information cannot be traced.
- **Contradictory reviewed evidence**: Outputs that contradict established, reviewed clinical guidelines without explicit flagging.
- **Out-of-scope professional request**: Requests pertaining to legal, financial, or non-therapeutic medical advice.
- **Attempt to write inferred knowledge permanently**: Attempts to update the core knowledge base with inferred data without going through the formal curation process.
- **Attempt to activate production integration**: Any attempt to connect the pilot system to live, production patient databases or EHR systems.
