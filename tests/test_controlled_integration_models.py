"""
tests/test_controlled_integration_models.py
--------------------------------------------
Unit tests for controlled_integration data models.
Verifies instantiation, immutability, default field generation, and field types.
"""

import pytest
import uuid
from dataclasses import FrozenInstanceError
from controlled_integration.models import (
    IntegrationContext,
    IntegrationRequest,
    OfficialEvidenceBundle,
    NoveltyDiscoveryBundle,
    ConsultationInputBundle,
    ConsultationOutputBundle,
    IntegrationDecision,
    IntegrationExplanation,
    IntegrationAuditEvent,
)


def test_integration_context_instantiation_and_defaults():
    """Verify IntegrationContext instantiates with required fields and generates defaults."""
    ctx = IntegrationContext(
        session_id="sess_001",
        user_id="user_123",
        user_role="ROLE_INTERNAL_THERAPIST",
    )
    assert ctx.session_id == "sess_001"
    assert ctx.user_id == "user_123"
    assert ctx.user_role == "ROLE_INTERNAL_THERAPIST"
    assert ctx.environment == "DEV"
    assert isinstance(ctx.correlation_id, str) and len(ctx.correlation_id) > 0
    assert isinstance(ctx.timestamp, str) and len(ctx.timestamp) > 0


def test_integration_context_immutability():
    """Verify IntegrationContext is frozen and cannot be mutated."""
    ctx = IntegrationContext(session_id="sess_001", user_id="u1", user_role="therapist")
    with pytest.raises((FrozenInstanceError, TypeError, AttributeError)):
        ctx.environment = "PROD"  # type: ignore


def test_integration_request_instantiation():
    """Verify IntegrationRequest instantiates with context and default overrides."""
    ctx = IntegrationContext(session_id="sess_002", user_id="u2", user_role="therapist")
    req_id = str(uuid.uuid4())
    req = IntegrationRequest(
        request_id=req_id,
        query_text="Protocol query for CBT depression",
        context=ctx,
    )
    assert req.request_id == req_id
    assert req.query_text == "Protocol query for CBT depression"
    assert req.context == ctx
    assert req.operating_mode_override is None
    assert req.flag_overrides == {}


def test_official_evidence_bundle():
    """Verify OfficialEvidenceBundle structure and defaults."""
    bundle = OfficialEvidenceBundle(
        bundle_id="bundle_b1",
        official_entries=[{"source_id": "OFF_01", "content_summary": "Summary"}],
        confidence_score=0.98,
        provenance_valid=True,
    )
    assert bundle.bundle_id == "bundle_b1"
    assert len(bundle.official_entries) == 1
    assert bundle.confidence_score == 0.98
    assert bundle.provenance_valid is True
    assert bundle.traversed_paths == []


def test_novelty_discovery_bundle():
    """Verify NoveltyDiscoveryBundle default status and candidate lists."""
    bundle = NoveltyDiscoveryBundle(
        bundle_id="bundle_c1",
        candidates=[{"candidate_id": "NOV_01", "status": "DISCOVERY_ONLY"}],
    )
    assert bundle.bundle_id == "bundle_c1"
    assert bundle.status == "DISCOVERY_ONLY"
    assert bundle.review_status == "PENDING_HUMAN_REVIEW"
    assert len(bundle.candidates) == 1
    assert bundle.contradictions == []


def test_consultation_input_bundle():
    """Verify ConsultationInputBundle fields for Gate C/D boundary."""
    bundle = ConsultationInputBundle(
        session_id="sess_cd1",
        eligible_official_evidence=[{"source_id": "OFF_01"}],
        blocked_novelty_count=2,
        is_validated=True,
    )
    assert bundle.session_id == "sess_cd1"
    assert len(bundle.eligible_official_evidence) == 1
    assert bundle.blocked_novelty_count == 2
    assert bundle.is_validated is True


def test_consultation_output_bundle():
    """Verify ConsultationOutputBundle fields for Gate D response."""
    bundle = ConsultationOutputBundle(
        request_summary="Summary of clinical query",
        official_entries=[{"source_id": "OFF_01"}],
        interpretations=[{"description": "Interpretation 1"}],
        therapist_decision_required=True,
    )
    assert bundle.request_summary == "Summary of clinical query"
    assert len(bundle.official_entries) == 1
    assert len(bundle.interpretations) == 1
    assert bundle.therapist_decision_required is True


def test_integration_decision():
    """Verify IntegrationDecision verdict and active mode."""
    decision = IntegrationDecision(
        request_id="req_dec_01",
        verdict="FULL_PILOT_SERVED",
        active_mode="THERAPIST_PILOT",
    )
    assert decision.request_id == "req_dec_01"
    assert decision.verdict == "FULL_PILOT_SERVED"
    assert decision.active_mode == "THERAPIST_PILOT"
    assert isinstance(decision.timestamp, str)


def test_integration_explanation():
    """Verify IntegrationExplanation diagnostic breakdown."""
    exp = IntegrationExplanation(
        request_id="req_exp_01",
        decision_verdict="LEGACY_SERVED",
        step_trace=["ingestion", "legacy_adapter"],
        blocking_reasons=[],
        score_breakdown={"confidence": 0.95},
    )
    assert exp.request_id == "req_exp_01"
    assert exp.decision_verdict == "LEGACY_SERVED"
    assert "legacy_adapter" in exp.step_trace
    assert exp.score_breakdown["confidence"] == 0.95


def test_integration_audit_event():
    """Verify IntegrationAuditEvent fields and default generation."""
    event = IntegrationAuditEvent(
        event_type="TEST_EVENT",
        request_id="req_audit_01",
        session_id="sess_audit_01",
        details={"key": "val"},
    )
    assert event.event_type == "TEST_EVENT"
    assert event.request_id == "req_audit_01"
    assert event.session_id == "sess_audit_01"
    assert event.details == {"key": "val"}
    assert isinstance(event.event_id, str) and len(event.event_id) > 0
    assert isinstance(event.timestamp, str) and len(event.timestamp) > 0
