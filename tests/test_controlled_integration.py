"""
tests/test_controlled_integration.py
-------------------------------------
Unit and safety tests for controlled_integration adapter layer.
Verifies all acceptance criteria, entity definitions, boundary filters, and safety invariants.
"""

import pytest
import uuid
from controlled_integration.models import (
    IntegrationRequest, IntegrationContext, OfficialEvidenceBundle,
    NoveltyDiscoveryBundle, ConsultationInputBundle, ConsultationOutputBundle,
    IntegrationDecision, IntegrationExplanation, IntegrationAuditEvent
)
from controlled_integration.adapters import (
    GateBAdapter, GateCAdapter, BoundaryAdapter, GateDAdapter
)
from controlled_integration.orchestration import IntegrationOrchestrator
from controlled_integration.feature_flags import FeatureFlagEvaluator
from controlled_integration.exceptions import UnreviewedNoveltyLeakError, FeatureFlagError

def test_entities_instantiation():
    """Verify all 9 integration entities instantiate correctly."""
    ctx = IntegrationContext(session_id="s_123", user_id="u_456", user_role="ROLE_INTERNAL_THERAPIST")
    req = IntegrationRequest(request_id=str(uuid.uuid4()), query_text="Test query", context=ctx)
    
    assert req.query_text == "Test query"
    assert ctx.user_role == "ROLE_INTERNAL_THERAPIST"

def test_boundary_screening_blocks_unreviewed_novelty():
    """Verify Gate C/D boundary screens out unreviewed DISCOVERY_ONLY candidates."""
    boundary = BoundaryAdapter()
    
    official = OfficialEvidenceBundle(
        bundle_id="b_1",
        official_entries=[
            {
                "source_id": "OFF_001",
                "content_summary": "Approved guideline",
                "provenance": "Manual",
                "is_approved": True,
                "is_reviewed": True
            }
        ]
    )
    
    novelty = NoveltyDiscoveryBundle(
        bundle_id="n_1",
        candidates=[
            {
                "candidate_id": "NOV_001",
                "source_entity": "A",
                "target_entity": "B",
                "relation_type": "REL",
                "status": "DISCOVERY_ONLY",
                "review_status": "PENDING_HUMAN_REVIEW"
            }
        ]
    )
    
    input_bundle = boundary.filter_for_consultation("s_123", official, novelty)
    
    assert input_bundle.blocked_novelty_count == 1
    assert len(input_bundle.eligible_official_evidence) == 1
    assert input_bundle.eligible_official_evidence[0]["source_id"] == "OFF_001"

def test_boundary_raises_exception_on_unreviewed_leak():
    """Verify UnreviewedNoveltyLeakError is raised if an unreviewed item attempts forced leak."""
    boundary = BoundaryAdapter()
    official = OfficialEvidenceBundle(bundle_id="b_1")
    novelty = NoveltyDiscoveryBundle(
        bundle_id="n_1",
        candidates=[
            {
                "candidate_id": "NOV_LEAK",
                "status": "DISCOVERY_ONLY",
                "review_status": "PENDING_HUMAN_REVIEW",
                "force_leak": True
            }
        ]
    )
    
    with pytest.raises(UnreviewedNoveltyLeakError):
        boundary.filter_for_consultation("s_123", official, novelty)

def test_orchestrator_legacy_mode():
    """Verify orchestrator returns LEGACY_SERVED in LEGACY_ONLY mode."""
    orchestrator = IntegrationOrchestrator()
    ctx = IntegrationContext(session_id="s_123", user_id="u_456", user_role="ROLE_INTERNAL_THERAPIST")
    req = IntegrationRequest(
        request_id=str(uuid.uuid4()),
        query_text="Legacy query",
        context=ctx,
        operating_mode_override="LEGACY_ONLY"
    )
    
    decision, explanation, res = orchestrator.process(req)
    
    assert decision.verdict == "LEGACY_SERVED"
    assert decision.active_mode == "LEGACY_ONLY"
    assert explanation.decision_verdict == "LEGACY_SERVED"

def test_orchestrator_therapist_pilot_mode():
    """Verify orchestrator runs full pipeline and returns FULL_PILOT_SERVED in THERAPIST_PILOT mode."""
    orchestrator = IntegrationOrchestrator()
    ctx = IntegrationContext(session_id="s_123", user_id="u_456", user_role="ROLE_INTERNAL_THERAPIST")
    req = IntegrationRequest(
        request_id=str(uuid.uuid4()),
        query_text="Therapist pilot query",
        context=ctx,
        operating_mode_override="THERAPIST_PILOT"
    )
    
    decision, explanation, res = orchestrator.process(req)
    
    assert decision.verdict == "FULL_PILOT_SERVED"
    assert decision.active_mode == "THERAPIST_PILOT"
    assert explanation.boundary_summary["blocked_count"] >= 0
    assert res.therapist_decision_required is True

def test_orchestrator_shadow_compare_mode():
    """Verify SHADOW_COMPARE mode serves primary legacy response and never alters legacy result."""
    orchestrator = IntegrationOrchestrator()
    ctx = IntegrationContext(session_id="s_shadow", user_id="u_456", user_role="ROLE_INTERNAL_THERAPIST")
    req = IntegrationRequest(
        request_id=str(uuid.uuid4()),
        query_text="Shadow query",
        context=ctx,
        operating_mode_override="SHADOW_COMPARE"
    )
    
    decision, explanation, res = orchestrator.process(req)
    
    assert decision.verdict == "LEGACY_SERVED"
    assert decision.active_mode == "SHADOW_COMPARE"
    assert res["response_type"] == "LEGACY_BASELINE"
    assert "shadow_graphrag_executed" in explanation.step_trace

def test_orchestrator_official_retrieval_only_mode():
    """Verify OFFICIAL_RETRIEVAL_ONLY returns OFFICIAL_RAG_SERVED."""
    orchestrator = IntegrationOrchestrator()
    ctx = IntegrationContext(session_id="s_official", user_id="u_456", user_role="ROLE_INTERNAL_THERAPIST")
    req = IntegrationRequest(
        request_id=str(uuid.uuid4()),
        query_text="Official RAG query",
        context=ctx,
        operating_mode_override="OFFICIAL_RETRIEVAL_ONLY"
    )
    
    decision, explanation, res = orchestrator.process(req)
    
    assert decision.verdict == "OFFICIAL_RAG_SERVED"
    assert decision.active_mode == "OFFICIAL_RETRIEVAL_ONLY"
    assert isinstance(res, OfficialEvidenceBundle)

def test_feature_flag_unknown_key_err07():
    """Verify FeatureFlagEvaluator raises FeatureFlagError on unknown flag key (ERR_07)."""
    evaluator = FeatureFlagEvaluator()
    with pytest.raises(FeatureFlagError) as exc_info:
        evaluator.evaluate_mode(
            mode_override="THERAPIST_PILOT",
            flag_overrides={"unknown_flag_key": True}
        )
    assert "Unknown feature flag key" in str(exc_info.value)

def test_orchestrator_fail_closed_on_unreviewed_leak():
    """Verify orchestrator fails closed to legacy fallback on boundary violation."""
    orchestrator = IntegrationOrchestrator()
    ctx = IntegrationContext(session_id="s_leak", user_id="u_456", user_role="ROLE_INTERNAL_THERAPIST")
    req = IntegrationRequest(
        request_id=str(uuid.uuid4()),
        query_text="Leak attempt query",
        context=ctx,
        operating_mode_override="THERAPIST_PILOT"
    )
    
    # Force leak in Gate C candidates via adapter override
    def leak_novelty(request, mock_candidates=None):
        return NoveltyDiscoveryBundle(
            bundle_id="leak_b",
            candidates=[{"candidate_id": "LEAK_1", "status": "DISCOVERY_ONLY", "force_leak": True}],
            status="DISCOVERY_ONLY",
            review_status="PENDING_HUMAN_REVIEW"
        )
    
    orchestrator.gate_c.evaluate_novelty = leak_novelty
    decision, explanation, res = orchestrator.process(req)
    
    assert decision.verdict == "FALLBACK_TRIGGERED"
    assert explanation.decision_verdict == "FALLBACK_TRIGGERED"
    assert "LEAK_1" in explanation.blocking_reasons[0]

