"""
tests/test_controlled_integration_orchestrator.py
---------------------------------------------------
Unit tests for IntegrationOrchestrator pipeline execution.
Verifies end-to-end processing across operating modes, boundary integration, and exception safety.
"""

import pytest
import uuid
from controlled_integration.models import IntegrationRequest, IntegrationContext
from controlled_integration.orchestration import IntegrationOrchestrator


def test_orchestrator_legacy_only_mode():
    """Verify orchestrator executes legacy adapter and returns LEGACY_SERVED in LEGACY_ONLY mode."""
    orchestrator = IntegrationOrchestrator()
    ctx = IntegrationContext(session_id="s_leg", user_id="u_leg", user_role="ROLE_INTERNAL_THERAPIST")
    req = IntegrationRequest(
        request_id=str(uuid.uuid4()),
        query_text="Legacy baseline query",
        context=ctx,
        operating_mode_override="LEGACY_ONLY",
    )

    decision, explanation, res = orchestrator.process(req)

    assert decision.verdict == "LEGACY_SERVED"
    assert decision.active_mode == "LEGACY_ONLY"
    assert explanation.decision_verdict == "LEGACY_SERVED"
    assert "legacy_adapter" in explanation.step_trace
    assert res["response_type"] == "LEGACY_BASELINE"


def test_orchestrator_emergency_disabled_mode():
    """Verify orchestrator returns LEGACY_SERVED in EMERGENCY_DISABLED mode."""
    orchestrator = IntegrationOrchestrator()
    ctx = IntegrationContext(session_id="s_em", user_id="u_em", user_role="ROLE_INTERNAL_THERAPIST")
    req = IntegrationRequest(
        request_id=str(uuid.uuid4()),
        query_text="Emergency query",
        context=ctx,
        operating_mode_override="EMERGENCY_DISABLED",
    )

    decision, explanation, res = orchestrator.process(req)

    assert decision.verdict == "LEGACY_SERVED"
    assert decision.active_mode == "EMERGENCY_DISABLED"
    assert res["response_type"] == "LEGACY_BASELINE"


def test_orchestrator_official_retrieval_only_mode():
    """Verify orchestrator executes Gate B and returns OFFICIAL_RAG_SERVED in OFFICIAL_RETRIEVAL_ONLY mode."""
    orchestrator = IntegrationOrchestrator()
    ctx = IntegrationContext(session_id="s_off", user_id="u_off", user_role="ROLE_INTERNAL_THERAPIST")
    req = IntegrationRequest(
        request_id=str(uuid.uuid4()),
        query_text="Official RAG query",
        context=ctx,
        operating_mode_override="OFFICIAL_RETRIEVAL_ONLY",
    )

    decision, explanation, official_bundle = orchestrator.process(req)

    assert decision.verdict == "OFFICIAL_RAG_SERVED"
    assert decision.active_mode == "OFFICIAL_RETRIEVAL_ONLY"
    assert "gate_b_adapter" in explanation.step_trace
    assert official_bundle.provenance_valid is True


def test_orchestrator_therapist_pilot_full_pipeline():
    """Verify orchestrator executes full multi-gate pipeline in THERAPIST_PILOT mode."""
    orchestrator = IntegrationOrchestrator()
    ctx = IntegrationContext(session_id="s_pilot", user_id="u_pilot", user_role="ROLE_INTERNAL_THERAPIST")
    req = IntegrationRequest(
        request_id=str(uuid.uuid4()),
        query_text="Full pilot consultation query",
        context=ctx,
        operating_mode_override="THERAPIST_PILOT",
    )

    decision, explanation, consultation_output = orchestrator.process(req)

    assert decision.verdict == "FULL_PILOT_SERVED"
    assert decision.active_mode == "THERAPIST_PILOT"
    assert "gate_cd_boundary" in explanation.step_trace
    assert "gate_d" in explanation.step_trace
    assert explanation.boundary_summary["eligible_count"] >= 1
    assert consultation_output.therapist_decision_required is True


def test_orchestrator_fallback_on_unhandled_mode():
    """Verify orchestrator falls back to legacy retrieval on invalid operating mode."""
    orchestrator = IntegrationOrchestrator()
    ctx = IntegrationContext(session_id="s_err", user_id="u_err", user_role="ROLE_INTERNAL_THERAPIST")
    req = IntegrationRequest(
        request_id=str(uuid.uuid4()),
        query_text="Fault query",
        context=ctx,
        operating_mode_override="UNKNOWN_INVALID_MODE",
    )

    decision, explanation, fallback_res = orchestrator.process(req)

    assert decision.verdict == "FALLBACK_TRIGGERED"
    assert explanation.decision_verdict == "FALLBACK_TRIGGERED"
    assert "fallback" in explanation.step_trace
    assert fallback_res["is_fallback"] is False  # Baseline response indicates fallback executed
    assert "fallback_reason" in fallback_res


def test_orchestrator_audit_event_logging():
    """Verify orchestrator logs mandatory audit events during request processing."""
    orchestrator = IntegrationOrchestrator()
    ctx = IntegrationContext(session_id="s_audit", user_id="u_audit", user_role="ROLE_INTERNAL_THERAPIST")
    req_id = str(uuid.uuid4())
    req = IntegrationRequest(
        request_id=req_id,
        query_text="Audit trace query",
        context=ctx,
        operating_mode_override="LEGACY_ONLY",
    )

    orchestrator.process(req)
    events = orchestrator.audit.get_events_for_request(req_id)

    assert len(events) >= 2
    event_types = [e.event_type for e in events]
    assert "INTEGRATION_REQUEST_RECEIVED" in event_types
    assert "FEATURE_FLAGS_EVALUATED" in event_types
