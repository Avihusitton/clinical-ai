"""
controlled_integration/audit/audit_logger.py
---------------------------------------------
Immutable audit logging engine with cryptographic SHA-256 hash chaining.
"""

import hashlib
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from ..models import IntegrationAuditEvent
from ..security.security_policy import SecurityPolicy

class AuditLogger:
    """
    Records immutable structured audit log events with SHA-256 hash chaining.
    """
    def __init__(self):
        self.events: List[IntegrationAuditEvent] = []
        self.previous_hash: str = "0" * 64
        self.sequence_number: int = 0
        self.security_policy = SecurityPolicy()

    def _calculate_hash(
        self,
        seq: int,
        prev_hash: str,
        timestamp: str,
        event_type: str,
        request_id: str,
        session_id: str,
        details: Dict[str, Any]
    ) -> str:
        data_str = f"{seq}|{prev_hash}|{timestamp}|{event_type}|{request_id}|{session_id}|{json.dumps(details, sort_keys=True)}"
        return hashlib.sha256(data_str.encode("utf-8")).hexdigest()

    def log_event(
        self,
        event_type: str,
        request_id: str,
        session_id: str,
        details: Dict[str, Any]
    ) -> IntegrationAuditEvent:
        """
        Creates, hash-chains, and stores an immutable IntegrationAuditEvent.
        Redacts PII from details before recording.
        """
        sanitized_details = self._sanitize_details(details)
        self.sequence_number += 1
        ts = datetime.utcnow().isoformat()

        current_hash = self._calculate_hash(
            seq=self.sequence_number,
            prev_hash=self.previous_hash,
            timestamp=ts,
            event_type=event_type,
            request_id=request_id,
            session_id=session_id,
            details=sanitized_details
        )

        audit_details = dict(sanitized_details)
        audit_details["_seq"] = self.sequence_number
        audit_details["_prev_hash"] = self.previous_hash
        audit_details["_hash"] = current_hash

        event = IntegrationAuditEvent(
            event_type=event_type,
            request_id=request_id,
            session_id=session_id,
            details=audit_details,
            timestamp=ts
        )

        self.previous_hash = current_hash
        self.events.append(event)
        return event

    def log_allow(self, request_id: str, session_id: str, details: Dict[str, Any]) -> IntegrationAuditEvent:
        """Emits immutable audit event for allowed request/action."""
        return self.log_event("ALLOW", request_id, session_id, details)

    def log_block(self, request_id: str, session_id: str, details: Dict[str, Any]) -> IntegrationAuditEvent:
        """Emits immutable audit event for blocked candidate/request."""
        return self.log_event("BLOCK", request_id, session_id, details)

    def log_fallback(self, request_id: str, session_id: str, details: Dict[str, Any]) -> IntegrationAuditEvent:
        """Emits immutable audit event for fallback trigger."""
        return self.log_event("FALLBACK", request_id, session_id, details)

    def log_emergency_override(self, request_id: str, session_id: str, details: Dict[str, Any]) -> IntegrationAuditEvent:
        """Emits immutable audit event for emergency override."""
        return self.log_event("EMERGENCY_OVERRIDE", request_id, session_id, details)

    def verify_chain_integrity(self) -> bool:
        """Verifies SHA-256 hash chain across all stored audit events."""
        prev = "0" * 64
        for event in self.events:
            seq = event.details.get("_seq")
            event_prev = event.details.get("_prev_hash")
            event_hash = event.details.get("_hash")
            if event_prev != prev:
                return False
            # Recompute details copy without metadata tags
            cleaned = {k: v for k, v in event.details.items() if not k.startswith("_")}
            expected_hash = self._calculate_hash(
                seq=seq,
                prev_hash=prev,
                timestamp=event.timestamp,
                event_type=event.event_type,
                request_id=event.request_id,
                session_id=event.session_id,
                details=cleaned
            )
            if expected_hash != event_hash:
                return False
            prev = event_hash
        return True

    def _sanitize_details(self, details: Dict[str, Any]) -> Dict[str, Any]:
        sanitized = {}
        for k, v in details.items():
            if isinstance(v, str):
                sanitized[k] = self.security_policy.sanitize_text(v)
            elif isinstance(v, dict):
                sanitized[k] = self._sanitize_details(v)
            elif isinstance(v, list):
                sanitized[k] = [self.security_policy.sanitize_text(i) if isinstance(i, str) else i for i in v]
            else:
                sanitized[k] = v
        return sanitized

    def get_events_for_request(self, request_id: str) -> List[IntegrationAuditEvent]:
        return [e for e in self.events if e.request_id == request_id]

    def get_all_events(self) -> List[IntegrationAuditEvent]:
        return list(self.events)
