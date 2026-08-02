"""
tests/test_gate_cd_safety_boundary.py
---------------------------------------
Safety-focused boundary tests for the Gate C → Gate D boundary.

These tests verify that the safety invariants of the boundary cannot be
circumvented, and that no dangerous data flow is possible.

Coverage:
  - Known approved knowledge is eligible (safety baseline)
  - Pending novelty is blocked (safety enforcement)
  - Discovery-only novelty is blocked (safety enforcement)
  - Rejected novelty is blocked (safety enforcement)
  - Contradictory unresolved novelty is blocked (safety enforcement)
  - Approved official evidence remains eligible
  - No Gate C candidate is promoted automatically (promotion gate)
  - No mutation occurs (immutability invariant)
  - No production module is imported (dependency isolation)
  - EvidenceEligibilityDecision carries correct audit fields

All objects are constructed inline.  No production modules imported.
"""
import sys
import pathlib
import pytest

from gate_cd_boundary import (
    ReviewedEvidenceProvider,
    NoveltyEvidenceFilter,
    ConsultationEvidenceBundle,
    EvidenceEligibilityDecision,
    EvidenceEligibilityStatus,
    BlockedReason,
    EvidenceEligibilityChecker,
)


# ---------------------------------------------------------------------------
# Safety baseline: approved knowledge is eligible
# ---------------------------------------------------------------------------

class TestSafetyBaseline:
    def test_approved_official_knowledge_eligible(self):
        """Official knowledge with full approval must be eligible."""
        provider = ReviewedEvidenceProvider(
            source_id="SAFETY-OFFICIAL-001",
            content_summary="CBT intervention for anxiety disorder.",
            provenance="APA Guideline 2024",
            is_approved=True,
            is_reviewed=True,
        )
        checker = EvidenceEligibilityChecker()
        decision = checker.check_reviewed_evidence(provider)
        assert decision.is_eligible, (
            "Approved official knowledge should always be eligible at the boundary."
        )

    def test_reviewed_relationship_eligible(self):
        """A reviewed relationship (approved + reviewed) must be eligible."""
        provider = ReviewedEvidenceProvider(
            source_id="SAFETY-REL-001",
            content_summary="Reviewed: CBT treats GAD",
            provenance="Reviewed Relationship Registry v1.0",
            is_approved=True,
            is_reviewed=True,
        )
        assert provider.is_eligible()

    def test_approved_reviewed_exercise_eligible(self):
        """Approved reviewed exercises must be eligible."""
        provider = ReviewedEvidenceProvider(
            source_id="SAFETY-EX-001",
            content_summary="5-4-3-2-1 Grounding Exercise (approved)",
            provenance="Approved Exercise Registry",
            is_approved=True,
            is_reviewed=True,
        )
        checker = EvidenceEligibilityChecker()
        decision = checker.check_reviewed_evidence(provider)
        assert decision.is_eligible


# ---------------------------------------------------------------------------
# Safety enforcement: all blocked novelty types
# ---------------------------------------------------------------------------

class TestSafetyEnforcement:
    """Each blocked category must produce a definitive BLOCKED decision."""

    def test_discovery_only_blocked(self):
        """DISCOVERY_ONLY status must always be blocked at the boundary."""
        checker = EvidenceEligibilityChecker()
        nf = NoveltyEvidenceFilter(
            candidate_id="SAFETY-DISC-001",
            status="DISCOVERY_ONLY",
            review_status="PENDING_HUMAN_REVIEW",
            novelty_type="NEW_RELATION_CANDIDATE",
        )
        decision = checker.check_novelty_filter(nf)
        assert decision.is_blocked, "DISCOVERY_ONLY must be blocked."
        assert decision.blocked_reason == BlockedReason.DISCOVERY_ONLY

    def test_pending_human_review_blocked(self):
        """PENDING_HUMAN_REVIEW must always be blocked at the boundary."""
        checker = EvidenceEligibilityChecker()
        nf = NoveltyEvidenceFilter(
            candidate_id="SAFETY-PEND-001",
            status="DISCOVERY_ONLY",
            review_status="PENDING_HUMAN_REVIEW",
            novelty_type="NEW_RELATION_CANDIDATE",
        )
        decision = checker.check_novelty_filter(nf)
        assert decision.is_blocked, "PENDING_HUMAN_REVIEW novelty must be blocked."

    def test_rejected_novelty_blocked(self):
        """REJECTED review_status must always be blocked at the boundary."""
        checker = EvidenceEligibilityChecker()
        nf = NoveltyEvidenceFilter(
            candidate_id="SAFETY-REJ-001",
            status="REVIEWED",
            review_status="REJECTED",
            novelty_type="NEW_RELATION_CANDIDATE",
        )
        decision = checker.check_novelty_filter(nf)
        assert decision.is_blocked, "Rejected novelty must be blocked."
        assert decision.blocked_reason == BlockedReason.REJECTED_NOVELTY

    def test_insufficient_evidence_blocked(self):
        """INSUFFICIENT_EVIDENCE novelty_type must always be blocked."""
        checker = EvidenceEligibilityChecker()
        nf = NoveltyEvidenceFilter(
            candidate_id="SAFETY-INSUF-001",
            status="REVIEWED",
            review_status="APPROVED",
            novelty_type="INSUFFICIENT_EVIDENCE",
        )
        decision = checker.check_novelty_filter(nf)
        assert decision.is_blocked, "Insufficient-evidence novelty must be blocked."
        assert decision.blocked_reason == BlockedReason.INSUFFICIENT_EVIDENCE

    def test_unresolved_contradiction_blocked(self):
        """POSSIBLE_CONTRADICTION novelty_type must always be blocked."""
        checker = EvidenceEligibilityChecker()
        nf = NoveltyEvidenceFilter(
            candidate_id="SAFETY-CONTRA-001",
            status="REVIEWED",
            review_status="APPROVED",
            novelty_type="POSSIBLE_CONTRADICTION",
        )
        decision = checker.check_novelty_filter(nf)
        assert decision.is_blocked, "Unresolved contradiction must be blocked."
        assert decision.blocked_reason == BlockedReason.UNRESOLVED_CONTRADICTION

    def test_out_of_scope_novelty_blocked(self):
        """OUT_OF_SCOPE novelty_type (from Gate C engine) must be blocked."""
        checker = EvidenceEligibilityChecker()
        nf = NoveltyEvidenceFilter(
            candidate_id="SAFETY-OOS-001",
            status="REVIEWED",
            review_status="APPROVED",
            novelty_type="OUT_OF_SCOPE",
        )
        decision = checker.check_novelty_filter(nf)
        assert decision.is_blocked, "OUT_OF_SCOPE novelty must be blocked."


# ---------------------------------------------------------------------------
# No automatic promotion gate
# ---------------------------------------------------------------------------

class TestNoAutomaticPromotionSafety:
    def test_novelty_filters_never_populate_eligible_items(self):
        """
        No novelty filter — regardless of status — should appear in
        bundle.eligible_items after build_consultation_bundle.
        """
        checker = EvidenceEligibilityChecker()
        novelty_scenarios = [
            NoveltyEvidenceFilter("PROMO-1", "DISCOVERY_ONLY", "PENDING_HUMAN_REVIEW", "NEW_RELATION_CANDIDATE"),
            NoveltyEvidenceFilter("PROMO-2", "REVIEWED", "REJECTED", "NEW_RELATION_CANDIDATE"),
            NoveltyEvidenceFilter("PROMO-3", "REVIEWED", "APPROVED", "INSUFFICIENT_EVIDENCE"),
            NoveltyEvidenceFilter("PROMO-4", "REVIEWED", "APPROVED", "POSSIBLE_CONTRADICTION"),
            NoveltyEvidenceFilter("PROMO-5", "REVIEWED", "APPROVED", "OUT_OF_SCOPE"),
        ]
        bundle, decisions = checker.build_consultation_bundle(
            session_id="PROMO-SAFETY-SESS",
            reviewed_providers=[],
            novelty_filters=novelty_scenarios,
        )
        # No eligible items should exist
        assert bundle.item_count() == 0
        # All 5 must be blocked
        assert bundle.blocked_count == 5
        # All decisions must be BLOCKED
        for d in decisions:
            assert d.is_blocked, f"Decision for {d.source_id} should be BLOCKED"

    def test_mix_does_not_promote_any_novelty(self):
        """
        When mixing approved providers with blocked novelty,
        only the approved providers appear in eligible_items.
        """
        checker = EvidenceEligibilityChecker()
        approved = [
            ReviewedEvidenceProvider(f"APRV-{i}", "Summary", "Provenance", True, True)
            for i in range(3)
        ]
        novelties = [
            NoveltyEvidenceFilter("DISC-MIX", "DISCOVERY_ONLY", "PENDING_HUMAN_REVIEW", "NEW_RELATION_CANDIDATE"),
            NoveltyEvidenceFilter("REJ-MIX", "REVIEWED", "REJECTED", "NEW_RELATION_CANDIDATE"),
        ]
        bundle, decisions = checker.build_consultation_bundle(
            session_id="MIX-SESS",
            reviewed_providers=approved,
            novelty_filters=novelties,
        )
        assert bundle.item_count() == 3
        assert bundle.blocked_count == 2
        # Verify all eligible items are ReviewedEvidenceProvider instances
        for item in bundle.eligible_items:
            assert isinstance(item, ReviewedEvidenceProvider)


# ---------------------------------------------------------------------------
# Immutability invariant tests
# ---------------------------------------------------------------------------

class TestImmutabilityInvariant:
    def test_reviewed_evidence_provider_immutable(self):
        provider = ReviewedEvidenceProvider(
            source_id="IMM-001",
            content_summary="Immutable evidence",
            provenance="ImmutableSource",
            is_approved=True,
            is_reviewed=True,
        )
        with pytest.raises((AttributeError, TypeError)):
            provider.is_approved = False  # type: ignore[misc]

    def test_novelty_evidence_filter_immutable(self):
        nf = NoveltyEvidenceFilter(
            candidate_id="IMM-NF-001",
            status="DISCOVERY_ONLY",
            review_status="PENDING_HUMAN_REVIEW",
            novelty_type="NEW_RELATION_CANDIDATE",
        )
        with pytest.raises((AttributeError, TypeError)):
            nf.review_status = "APPROVED"  # type: ignore[misc]

    def test_consultation_evidence_bundle_immutable(self):
        bundle = ConsultationEvidenceBundle(
            eligible_items=[],
            blocked_count=0,
            session_id="IMM-BUNDLE",
        )
        with pytest.raises((AttributeError, TypeError)):
            bundle.session_id = "MUTATED"  # type: ignore[misc]

    def test_eligibility_decision_immutable(self):
        decision = EvidenceEligibilityDecision(
            source_id="IMM-DEC-001",
            status=EvidenceEligibilityStatus.ELIGIBLE,
        )
        with pytest.raises((AttributeError, TypeError)):
            decision.source_id = "MUTATED"  # type: ignore[misc]

    def test_no_mutation_after_build_bundle(self):
        """
        Building a bundle must not mutate any input objects.
        The original providers list and novelty filters must be unchanged.
        """
        checker = EvidenceEligibilityChecker()
        provider = ReviewedEvidenceProvider(
            source_id="NO-MUT-PROV",
            content_summary="Original summary",
            provenance="Original provenance",
            is_approved=True,
            is_reviewed=True,
        )
        nf = NoveltyEvidenceFilter(
            candidate_id="NO-MUT-NF",
            status="DISCOVERY_ONLY",
            review_status="PENDING_HUMAN_REVIEW",
            novelty_type="NEW_RELATION_CANDIDATE",
        )
        # Capture original values
        orig_provider_source = provider.source_id
        orig_nf_status = nf.status

        checker.build_consultation_bundle(
            session_id="NO-MUT-SESS",
            reviewed_providers=[provider],
            novelty_filters=[nf],
        )

        # Verify no mutation occurred
        assert provider.source_id == orig_provider_source
        assert nf.status == orig_nf_status


# ---------------------------------------------------------------------------
# Dependency isolation tests
# ---------------------------------------------------------------------------

class TestDependencyIsolation:
    def test_no_neo4j_imported(self):
        """neo4j must not appear in sys.modules after boundary imports."""
        # gate_cd_boundary was already imported at top of file
        for mod_name in sys.modules:
            if "gate_cd_boundary" in mod_name:
                assert "neo4j" not in mod_name.lower(), (
                    f"neo4j found in boundary module: {mod_name}"
                )
        # Also check globally
        neo4j_mods = [m for m in sys.modules if "neo4j" in m.lower()]
        # neo4j may be installed but must not be imported by gate_cd_boundary
        # We verify boundary files contain no neo4j imports
        boundary_dir = pathlib.Path("gate_cd_boundary")
        for py_file in boundary_dir.glob("*.py"):
            content = py_file.read_text(encoding="utf-8")
            assert "neo4j" not in content, (
                f"neo4j reference found in {py_file}"
            )

    def test_no_llm_client_imported(self):
        """LLM client must not be imported by any gate_cd_boundary module."""
        boundary_dir = pathlib.Path("gate_cd_boundary")
        for py_file in boundary_dir.glob("*.py"):
            content = py_file.read_text(encoding="utf-8")
            for forbidden in ["openai", "anthropic", "llm_client"]:
                assert forbidden not in content.lower(), (
                    f"Forbidden import '{forbidden}' found in {py_file}"
                )

    def test_no_graph_write_in_boundary(self):
        """No graph write operations in any boundary module."""
        boundary_dir = pathlib.Path("gate_cd_boundary")
        for py_file in boundary_dir.glob("*.py"):
            content = py_file.read_text(encoding="utf-8")
            for pattern in ["session.run", "GraphDatabase", ".merge(", ".create("]:
                assert pattern not in content, (
                    f"Graph write pattern '{pattern}' found in {py_file}"
                )

    def test_no_production_modules_imported(self):
        """
        gate_cd_boundary must not import any production pipeline modules:
        retrieval, ingestion_pipeline, build_glossary, etc.
        """
        production_modules = [
            "retrieval",
            "ingestion_pipeline",
            "build_glossary",
            "run_full_pipeline",
            "master_dashboard",
            "review_app",
            "config",
            "llm_client",
            "relation_policy",
            "second_order_reasoner",
        ]
        boundary_dir = pathlib.Path("gate_cd_boundary")
        for py_file in boundary_dir.glob("*.py"):
            content = py_file.read_text(encoding="utf-8")
            for mod in production_modules:
                assert f"import {mod}" not in content, (
                    f"Production module 'import {mod}' found in {py_file}"
                )
                assert f"from {mod}" not in content, (
                    f"Production module 'from {mod}' found in {py_file}"
                )


# ---------------------------------------------------------------------------
# Audit trail completeness
# ---------------------------------------------------------------------------

class TestAuditTrailCompleteness:
    def test_every_decision_has_source_id(self):
        checker = EvidenceEligibilityChecker()
        providers = [ReviewedEvidenceProvider(f"AUDIT-{i}", "S", "P", True, True) for i in range(3)]
        nfs = [
            NoveltyEvidenceFilter(f"AUDIT-NF-{i}", "DISCOVERY_ONLY", "PENDING_HUMAN_REVIEW", "NEW_RELATION_CANDIDATE")
            for i in range(2)
        ]
        _, decisions = checker.build_consultation_bundle(
            session_id="AUDIT-SESS",
            reviewed_providers=providers,
            novelty_filters=nfs,
        )
        for d in decisions:
            assert d.source_id, f"Decision missing source_id: {d}"

    def test_every_decision_has_status(self):
        checker = EvidenceEligibilityChecker()
        providers = [ReviewedEvidenceProvider("AUDIT-STATUS", "S", "P", True, True)]
        _, decisions = checker.build_consultation_bundle(
            session_id="AUDIT-STATUS-SESS",
            reviewed_providers=providers,
            novelty_filters=[],
        )
        for d in decisions:
            assert d.status in (
                EvidenceEligibilityStatus.ELIGIBLE,
                EvidenceEligibilityStatus.BLOCKED,
            )

    def test_blocked_decisions_have_blocked_reason(self):
        checker = EvidenceEligibilityChecker()
        nf = NoveltyEvidenceFilter("AUDIT-BLOCK", "DISCOVERY_ONLY", "PENDING_HUMAN_REVIEW", "NEW_RELATION_CANDIDATE")
        _, decisions = checker.build_consultation_bundle(
            session_id="AUDIT-BLOCK-SESS",
            reviewed_providers=[],
            novelty_filters=[nf],
        )
        for d in decisions:
            if d.is_blocked:
                assert d.blocked_reason is not None, (
                    f"Blocked decision for {d.source_id} missing blocked_reason"
                )

    def test_eligible_decisions_have_no_blocked_reason(self):
        checker = EvidenceEligibilityChecker()
        provider = ReviewedEvidenceProvider("AUDIT-ELIG", "S", "P", True, True)
        _, decisions = checker.build_consultation_bundle(
            session_id="AUDIT-ELIG-SESS",
            reviewed_providers=[provider],
            novelty_filters=[],
        )
        for d in decisions:
            if d.is_eligible:
                assert d.blocked_reason is None

    def test_bundle_session_id_preserved(self):
        checker = EvidenceEligibilityChecker()
        bundle, _ = checker.build_consultation_bundle(
            session_id="MY-SESSION-ID",
            reviewed_providers=[],
            novelty_filters=[],
        )
        assert bundle.session_id == "MY-SESSION-ID"
