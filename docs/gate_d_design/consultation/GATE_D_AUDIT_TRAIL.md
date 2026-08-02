# Gate D: Audit Trail Design

## Overview
Every interaction within the Gate D Consultation system must generate a comprehensive, immutable audit trail. This ensures accountability, supports quality assurance, and provides a record that human authority was maintained at all times.

## Consultation Audit Event
The core of the audit trail is the `ConsultationAuditEvent`.

### Required Metadata
For every event, the following metadata must be captured:
- `eventId`: Unique identifier for the audit record.
- `timestamp`: UTC timestamp of the event.
- `eventType`: The category of the event (see Event Types below).
- `actorId`: The ID of the therapist or system component triggering the event.
- `targetEntityId`: The ID of the consultation request, response, or decision involved.
- `contextSnapshot`: A hashed or de-identified summary of the context at the time of the event to preserve the state.

## Event Types

### 1. Request Submitted
- Triggered when a therapist submits a `ConsultationRequest`.
- Logs the therapist ID, time of submission, and the scope of the inquiry.

### 2. System Response Generated
- Triggered when the system produces a `ConsultationResponse`.
- Logs the generation time, the model/system version used, and the sources retrieved.

### 3. Therapist Decision Recorded
- Triggered when the therapist actively reviews the response and submits a `TherapistDecision`.
- Logs which elements were accepted, rejected, or modified, reinforcing human oversight.

### 4. Safety Boundary Triggered
- Triggered if a consultation request or context touches upon a defined `SafetyBoundary` (e.g., mention of crisis).
- Logs the warning presented to the therapist.

## Data Retention and Privacy
- Audit logs must strictly adhere to the rule of "No Live Identifiable Patient Data." All patient-specific context must be de-identified prior to logging, or the log must only reference internal, opaque IDs.
- Audit trails must be maintained in an append-only datastore to prevent tampering.
