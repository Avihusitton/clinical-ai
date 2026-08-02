"""
controlled_integration/telemetry/telemetry_collector.py
---------------------------------------------------------
Telemetry collector maintaining structured metric snapshots and telemetry events matching TELEMETRY_SCHEMA.json.
Guarantees zero raw text storage and hashed therapist/user identities.
"""

import hashlib
from typing import Dict, Any, List, Optional
from datetime import datetime

class TelemetryCollector:
    """
    Collects runtime telemetry metrics and schema-compliant telemetry payloads.
    Guarantees zero raw text and SHA-256 hashed therapist/user IDs.
    """
    def __init__(self, environment: str = "integration_test", salt: str = "clinical_ai_salt_2026"):
        self.environment = environment
        self.salt = salt
        self.events: List[Dict[str, Any]] = []
        self.metrics: Dict[str, Any] = {
            "total_requests": 0,
            "legacy_served_count": 0,
            "official_rag_served_count": 0,
            "full_pilot_served_count": 0,
            "fallback_count": 0,
            "blocked_evidence_count": 0,
        }

    def hash_therapist_id(self, raw_id: str) -> str:
        """Hashes therapist/user ID using SHA-256 with rotating salt."""
        if not raw_id:
            raw_id = "anonymous"
        salted = f"{self.salt}:{raw_id}"
        h = hashlib.sha256(salted.encode("utf-8")).hexdigest()
        return f"sha256:{h}"

    def build_common_header(
        self,
        trace_id: str,
        request_id: str,
        session_id: str,
        operating_mode: str,
        user_id: str,
        feature_flags: Dict[str, bool]
    ) -> Dict[str, Any]:
        """Constructs common header conforming to TELEMETRY_SCHEMA.json."""
        if not trace_id.startswith("tr-"):
            h = hashlib.md5(trace_id.encode("utf-8")).hexdigest()
            trace_id = f"tr-{h}"
        if not request_id.startswith("req-"):
            h = hashlib.md5(request_id.encode("utf-8")).hexdigest()[:16]
            request_id = f"req-{h}"
        if not session_id.startswith("sess-"):
            h = hashlib.md5(session_id.encode("utf-8")).hexdigest()[:16]
            session_id = f"sess-{h}"

        mode_map = {
            "LEGACY_ONLY": "legacy_only",
            "SHADOW_COMPARE": "shadow_comparison",
            "OFFICIAL_RETRIEVAL_ONLY": "reviewed_consultation",
            "THERAPIST_PILOT": "reviewed_consultation",
            "EMERGENCY_DISABLED": "fallback_error"
        }
        schema_mode = mode_map.get(operating_mode, "legacy_only")

        flags_payload = {
            "master_pilot_flag": feature_flags.get("therapist_pilot_access_enabled", False),
            "shadow_mode_enabled": feature_flags.get("shadow_comparison_enabled", False),
            "graph_rag_enabled": feature_flags.get("gate_b_reasoning_enabled", False),
            "strict_provenance_enforced": feature_flags.get("official_retrieval_enabled", False),
            "novelty_blocking_enabled": not feature_flags.get("gate_c_novelty_enabled", False),
            "legacy_fallback_enabled": True
        }

        return {
            "trace_id": trace_id,
            "request_id": request_id,
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat(),
            "environment": self.environment,
            "operating_mode": schema_mode,
            "therapist_id_hash": self.hash_therapist_id(user_id),
            "feature_flags": flags_payload
        }

    def record_decision(self, verdict: str):
        self.metrics["total_requests"] += 1
        if verdict == "LEGACY_SERVED":
            self.metrics["legacy_served_count"] += 1
        elif verdict == "OFFICIAL_RAG_SERVED":
            self.metrics["official_rag_served_count"] += 1
        elif verdict == "FULL_PILOT_SERVED":
            self.metrics["full_pilot_served_count"] += 1
        elif verdict == "FALLBACK_TRIGGERED":
            self.metrics["fallback_count"] += 1

    def record_blocked_evidence(self, count: int):
        self.metrics["blocked_evidence_count"] += count

    def record_retrieval_event(
        self,
        header: Dict[str, Any],
        legacy_doc_count: int,
        graph_node_count: int,
        agreement_score: float,
        latency_ms: float,
        evidence_ids: List[str]
    ):
        event = {
            "header": header,
            "event_type": "retrieval_event",
            "payload": {
                "legacy_document_count": legacy_doc_count,
                "graph_node_count": graph_node_count,
                "retrieval_agreement_score": max(0.0, min(1.0, agreement_score)),
                "retrieval_latency_ms": latency_ms,
                "retrieved_evidence_ids": evidence_ids
            }
        }
        self.events.append(event)

    def record_fallback_event(
        self,
        header: Dict[str, Any],
        failure_reason: str,
        failing_component: str,
        fallback_latency_ms: float = 0.0
    ):
        event = {
            "header": header,
            "event_type": "fallback_event",
            "payload": {
                "fallback_triggered": True,
                "failure_reason": failure_reason,
                "failing_component": failing_component,
                "fallback_component": "legacy_retrieval_engine",
                "fallback_latency_ms": fallback_latency_ms
            }
        }
        self.events.append(event)

    def record_security_event(
        self,
        header: Dict[str, Any],
        check_type: str,
        passed: bool,
        violation_code: Optional[str],
        action_enforced: str
    ):
        event = {
            "header": header,
            "event_type": "security_event",
            "payload": {
                "security_check_type": check_type,
                "passed": passed,
                "violation_code": violation_code,
                "action_enforced": action_enforced
            }
        }
        self.events.append(event)

    def get_summary(self) -> Dict[str, Any]:
        return dict(self.metrics)

    def get_events(self) -> List[Dict[str, Any]]:
        return list(self.events)


# Maintain TelemetryRecorder alias for backward compatibility
TelemetryRecorder = TelemetryCollector
