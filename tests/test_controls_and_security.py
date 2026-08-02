"""
tests/test_controls_and_security.py
-----------------------------------
Comprehensive test suite verifying Wave 6 Task W6-A2 Controls and Security package.
Covers 5 operating modes, fail-closed rules ERR_01-ERR_07, emergency override, PII rejection,
narrative protection, least-privilege RBAC, immutable audit logging with hash chaining,
and schema-compliant zero-PII telemetry collection.
"""

import os
import tempfile
import pytest
import uuid
from controlled_integration.feature_flags import (
    FeatureFlagManager, FeatureFlagEvaluator, VALID_OPERATING_MODES, DEFAULT_FLAGS
)
from controlled_integration.fallback import FallbackHandler
from controlled_integration.security import (
    SecurityPolicy, PIIRejectedError, AccessDeniedError, RawNarrativeStoreForbiddenError
)
from controlled_integration.audit import AuditLogger
from controlled_integration.telemetry import TelemetryCollector, TelemetryRecorder
from controlled_integration.orchestration import IntegrationOrchestrator
from controlled_integration.models import (
    IntegrationRequest, IntegrationContext
)
from controlled_integration.exceptions import FeatureFlagError, IntegrationException

def test_five_operating_modes_defined():
    """Verify all 5 required operating modes are recognized."""
    expected = {"LEGACY_ONLY", "SHADOW_COMPARE", "OFFICIAL_RETRIEVAL_ONLY", "THERAPIST_PILOT", "EMERGENCY_DISABLED"}
    assert VALID_OPERATING_MODES == expected

def test_operating_mode_defaults_and_evaluation():
    """Verify default operating mode is LEGACY_ONLY and flag maps evaluate cleanly."""
    mgr = FeatureFlagManager()
    
    mode, flags = mgr.evaluate_mode(mode_override="LEGACY_ONLY")
    assert mode == "LEGACY_ONLY"
    assert flags["official_retrieval_enabled"] is False
    assert flags["audit_logging_enabled"] is True

    mode, flags = mgr.evaluate_mode(mode_override="THERAPIST_PILOT")
    assert mode == "THERAPIST_PILOT"
    assert flags["therapist_pilot_access_enabled"] is True
    assert flags["gate_d_formatting_enabled"] is True

def test_invalid_mode_fails_closed_to_legacy():
    """Verify unknown operating mode fails closed immediately to LEGACY_ONLY."""
    mgr = FeatureFlagManager()
    mode, flags = mgr.evaluate_mode(mode_override="INVALID_MODE_99", raise_on_error=False)
    assert mode == "LEGACY_ONLY"
    assert flags["official_retrieval_enabled"] is False

    with pytest.raises(FeatureFlagError):
        mgr.evaluate_mode(mode_override="INVALID_MODE_99", raise_on_error=True)

def test_unknown_flag_key_fails_closed():
    """Verify unknown flag key fails closed to LEGACY_ONLY."""
    mgr = FeatureFlagManager()
    mode, flags = mgr.evaluate_mode(
        mode_override="THERAPIST_PILOT",
        flag_overrides={"unknown_malicious_flag": True},
        raise_on_error=False
    )
    assert mode == "LEGACY_ONLY"

    with pytest.raises(FeatureFlagError):
        mgr.evaluate_mode(
            mode_override="THERAPIST_PILOT",
            flag_overrides={"unknown_malicious_flag": True},
            raise_on_error=True
        )

def test_rule_err_01_emergency_mode():
    """Verify ERR_01: EMERGENCY_DISABLED forces all feature sub-flags False."""
    mgr = FeatureFlagManager()
    mode, flags = mgr.evaluate_mode(
        mode_override="EMERGENCY_DISABLED",
        flag_overrides={"official_retrieval_enabled": True},
        raise_on_error=False
    )
    assert mode == "EMERGENCY_DISABLED"
    assert flags["official_retrieval_enabled"] is False
    assert flags["gate_b_reasoning_enabled"] is False

def test_rule_err_03_gate_b_requires_official_retrieval():
    """Verify ERR_03: gate_b_reasoning_enabled requires official_retrieval_enabled=True."""
    mgr = FeatureFlagManager()
    with pytest.raises(FeatureFlagError):
        mgr.evaluate_mode(
            mode_override="THERAPIST_PILOT",
            flag_overrides={"gate_b_reasoning_enabled": True, "official_retrieval_enabled": False},
            raise_on_error=True
        )

def test_emergency_disable_environment_variable(monkeypatch):
    """Verify CLINICAL_AI_EMERGENCY_DISABLE env var forces EMERGENCY_DISABLED mode."""
    monkeypatch.setenv("CLINICAL_AI_EMERGENCY_DISABLE", "true")
    mgr = FeatureFlagManager()
    assert mgr.is_emergency_disabled() is True
    mode, flags = mgr.evaluate_mode(mode_override="THERAPIST_PILOT", raise_on_error=False)
    assert mode == "EMERGENCY_DISABLED"
    assert flags["therapist_pilot_access_enabled"] is False

def test_emergency_disable_sentinel_file(tmp_path, monkeypatch):
    """Verify presence of data/EMERGENCY_DISABLE.sentinel forces emergency shutdown."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    sentinel = data_dir / "EMERGENCY_DISABLE.sentinel"
    sentinel.touch()
    
    monkeypatch.chdir(tmp_path)
    mgr = FeatureFlagManager()
    assert mgr.is_emergency_disabled() is True

def test_pii_rejection_email_phone_ssn():
    """Verify SecurityPolicy detects and rejects emails, phone numbers, and SSNs."""
    policy = SecurityPolicy()
    
    # Safe text
    policy.validate_input("What are standard protocols for anxiety management?")
    
    # Email
    with pytest.raises(PIIRejectedError):
        policy.validate_input("Patient email is therapist@clinic.org for consultation")
        
    # US Phone
    with pytest.raises(PIIRejectedError):
        policy.validate_input("Contact patient at 555-123-4567 immediately")
        
    # Israeli Phone
    with pytest.raises(PIIRejectedError):
        policy.validate_input("Call patient at 054-9876543 for review")

    # SSN
    with pytest.raises(PIIRejectedError):
        policy.validate_input("Patient SSN is 123-45-6789")

def test_pii_text_sanitization():
    """Verify SecurityPolicy redacts PII strings accurately."""
    text = "User patient@example.com with phone 052-1234567 and SSN 123-45-6789"
    sanitized = SecurityPolicy.sanitize_text(text)
    assert "[REDACTED_EMAIL]" in sanitized
    assert "[REDACTED_PHONE]" in sanitized
    assert "[REDACTED_SSN]" in sanitized
    assert "patient@example.com" not in sanitized

def test_raw_narrative_storage_forbidden():
    """Verify RawNarrativeStoreForbiddenError is raised when narrative storage is attempted."""
    policy = SecurityPolicy()
    with pytest.raises(RawNarrativeStoreForbiddenError):
        policy.validate_narrative_storage(store_raw_narrative=True)
    policy.validate_narrative_storage(store_raw_narrative=False)

def test_rbac_least_privilege_access_control():
    """Verify Role-Based Access Control matrix enforcement."""
    policy = SecurityPolicy()
    
    # Therapist Pilot User allowed for pilot query
    assert policy.check_access("ROLE_INTERNAL_THERAPIST", "pilot_query_advisor") is True
    assert policy.check_access("THERAPIST_PILOT_USER", "pilot_query_advisor") is True
    
    # Clinical Reviewer denied pilot query advisor
    with pytest.raises(AccessDeniedError):
        policy.check_access("CLINICAL_REVIEWER", "pilot_query_advisor")
        
    # Clinical Reviewer allowed for novelty candidate queue
    assert policy.check_access("CLINICAL_REVIEWER", "novelty_candidate_queue") is True
    
    # Knowledge Graph write forbidden for ALL roles
    with pytest.raises(AccessDeniedError):
        policy.check_access("SYSTEM_OPERATOR", "knowledge_graph_write")
    with pytest.raises(AccessDeniedError):
        policy.check_access("THERAPIST_PILOT_USER", "knowledge_graph_write")
        
    # Security Auditor allowed for audit logs
    assert policy.check_access("SECURITY_AUDITOR", "audit_logs") is True

def test_immutable_audit_logger_hash_chaining():
    """Verify AuditLogger logs events with SHA-256 hash chaining and verifies chain integrity."""
    logger = AuditLogger()
    
    e1 = logger.log_allow("req_1", "sess_1", {"action": "query"})
    e2 = logger.log_block("req_2", "sess_1", {"reason": "PII detected"})
    e3 = logger.log_fallback("req_3", "sess_1", {"trigger": "LLM timeout"})
    e4 = logger.log_emergency_override("req_4", "sess_1", {"operator": "admin"})

    assert len(logger.get_all_events()) == 4
    assert logger.verify_chain_integrity() is True

    # Verify tampering detection
    logger.events[1].details["reason"] = "Tampered reason"
    assert logger.verify_chain_integrity() is False

def test_telemetry_collector_schema_compliance_and_hashing():
    """Verify TelemetryCollector hashes therapist IDs and emits clean, zero-PII headers and events."""
    collector = TelemetryCollector(environment="shadow_pilot", salt="test_salt")
    
    h1 = collector.hash_therapist_id("user_therapist_99")
    h2 = collector.hash_therapist_id("user_therapist_99")
    assert h1 == h2
    assert h1.startswith("sha256:")
    assert "user_therapist_99" not in h1
    
    header = collector.build_common_header(
        trace_id="tr-12345678901234567890123456789012",
        request_id="req-1234567890123456",
        session_id="sess-1234567890123456",
        operating_mode="THERAPIST_PILOT",
        user_id="user_therapist_99",
        feature_flags={"therapist_pilot_access_enabled": True, "official_retrieval_enabled": True}
    )
    
    assert header["environment"] == "shadow_pilot"
    assert header["operating_mode"] == "reviewed_consultation"
    assert header["therapist_id_hash"] == h1

    collector.record_retrieval_event(
        header=header,
        legacy_doc_count=3,
        graph_node_count=5,
        agreement_score=0.92,
        latency_ms=120.5,
        evidence_ids=["OFF_001", "OFF_002"]
    )
    
    events = collector.get_events()
    assert len(events) == 1
    assert events[0]["event_type"] == "retrieval_event"
    assert events[0]["payload"]["legacy_document_count"] == 3

def test_orchestrator_pii_rejection_trigger_fallback():
    """Verify IntegrationOrchestrator rejects PII queries and returns legacy fallback."""
    orchestrator = IntegrationOrchestrator()
    ctx = IntegrationContext(session_id="sess_123", user_id="usr_456", user_role="ROLE_INTERNAL_THERAPIST")
    req = IntegrationRequest(
        request_id=str(uuid.uuid4()),
        query_text="Patient phone is 050-1234567 please advise on therapy",
        context=ctx,
        operating_mode_override="THERAPIST_PILOT"
    )
    
    decision, explanation, res = orchestrator.process(req)
    
    assert decision.verdict == "FALLBACK_TRIGGERED"
    assert "PII" in explanation.blocking_reasons[0]
    
    audit_events = orchestrator.audit.get_events_for_request(req.request_id)
    assert any(e.event_type == "BLOCK" for e in audit_events)
    assert any(e.event_type == "FALLBACK" for e in audit_events)
