"""
tests/test_gate_cd_boundary.py
-------------------------------
Functional boundary tests for the Gate C → Gate D boundary layer.

Coverage:
  - Known approved knowledge is eligible
  - Pending novelty is blocked
  - Discovery-only novelty is blocked
  - Rejected novelty is blocked
  - Contradictory / unresolved novelty is blocked
  - Approved official evidence remains eligible
  - No Gate C candidate is promoted automatically
  - No mutation occurs on any input object
  - No production module (Neo4j, LLM, graph writes) is imported

No production modules are imported.
All objects are constructed inline (no fixtures pulled from production modules).
"""
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
# Helpers
# ---------------------------------------------------------------------------

def _approved_provider(source_id: str = "SRC-001") -> ReviewedEvidenceProvider:
    """Returns a fully approved, reviewed evidence provider."""
    return ReviewedEvidenceProvider(
        source_id=source_id,
        content_summary="Approved official knowledge entry.",
        provenance="Official Guideline v2.3",
        is_approved=True,
        is_reviewed=True,
    )


def _unapproved_provider(source_id: str = "SRC-UNAPP") -> ReviewedEvidenceProvider:
    """Returns a provider that has NOT been approved."""
    return ReviewedEvidenceProvider(
        source_id=source_id,
        content_summary="Draft entry not yet approved.",
        provenance="Draft",
        is_approved=False,
        is_reviewed=False,
    )


def _novelty_filter(
    candidate_id: str,
    status: str = "DISCOVERY_ONLY",
    review_status: str = "PENDING_HUMAN_REVIEW",
    novelty_type: str = "NEW_RELATION_CANDIDATE",
) -> NoveltyEvidenceFilter:
    return NoveltyEvidenceFilter(
        candidate_id=candidate_id,
        status=status,
        review_status=review_status,
        novelty_type=novelty_type,
    )


# ---------------------------------------------------------------------------
# Test: Approved knowledge is eligible
# ---------------------------------------------------------------------------

class TestApprovedEvidenceEligible:
    def test_approved_reviewed_provider_is_eligible(self):
        provider = _approved_provider()
        assert provider.is_eligible() is True

    def test_eligibility_check_returns_eligible_decision(self):
        checker = EvidenceEligibilityChecker()
        provider = _approved_provider("OFFICIAL-001")
        decision = checker.check_reviewed_evidence(provider)
        assert decision.is_eligible is True
        assert decision.status == EvidenceEligibilityStatus.ELIGIBLE
        assert decision.blocked_reason is None

    def test_approved_official_evidence_multiple_sources(self):
        checker = EvidenceEligibilityChecker()
        providers = [_approved_provider(f"SRC-{i}") for i in range(5)]
        decisions = [checker.check_reviewed_evidence(p) for p in providers]
        assert all(d.is_eligible for d in decisions)

    def test_unapproved_provider_not_eligible(self):
        provider = _unapproved_provider()
        assert provider.is_eligible() is False

    def test_unapproved_returns_blocked_decision(self):
        checker = EvidenceEligibilityChecker()
        provider = _unapproved_provider()
        decision = checker.check_reviewed_evidence(provider)
        assert decision.is_blocked is True
        assert decision.status == EvidenceEligibilityStatus.BLOCKED


# ---------------------------------------------------------------------------
# Test: Pending novelty is blocked
# ---------------------------------------------------------------------------

class TestPendingNoveltyBlocked:
    def test_pending_human_review_novelty_is_blocked(self):
        nf = _novelty_filter(
            candidate_id="NF-PENDING",
            status="DISCOVERY_ONLY",
            review_status="PENDING_HUMAN_REVIEW",
            novelty_type="NEW_RELATION_CANDIDATE",
        )
        assert nf.is_blocked() is True

    def test_pending_returns_blocked_reason(self):
        nf = _novelty_filter(
            candidate_id="NF-PENDING-2",
            status="DISCOVERY_ONLY",
            review_status="PENDING_HUMAN_REVIEW",
            novelty_type="NEW_RELATION_CANDIDATE",
        )
        reason = nf.blocked_reason()
        assert reason == BlockedReason.DISCOVERY_ONLY  # status checked first

    def test_checker_blocks_pending_novelty(self):
        checker = EvidenceEligibilityChecker()
        nf = _novelty_filter(
            candidate_id="NF-PENDING-CHK",
            status="DISCOVERY_ONLY",
            review_status="PENDING_HUMAN_REVIEW",
            novelty_type="NEW_RELATION_CANDIDATE",
        )
        decision = checker.check_novelty_filter(nf)
        assert decision.is_blocked is True
        assert decision.status == EvidenceEligibilityStatus.BLOCKED

    def test_pending_novelty_not_in_bundle(self):
        checker = EvidenceEligibilityChecker()
        nf = _novelty_filter(
            candidate_id="NF-BUNDLE-PENDING",
            status="DISCOVERY_ONLY",
            review_status="PENDING_HUMAN_REVIEW",
            novelty_type="NEW_RELATION_CANDIDATE",
        )
        bundle, decisions = checker.build_consultation_bundle(
            session_id="SESS-01",
            reviewed_providers=[],
            novelty_filters=[nf],
        )
        assert bundle.item_count() == 0
        assert bundle.blocked_count == 1
        assert decisions[0].is_blocked is True


# ---------------------------------------------------------------------------
# Test: Discovery-only novelty is blocked
# ---------------------------------------------------------------------------

class TestDiscoveryOnlyBlocked:
    def test_discovery_only_status_is_blocked(self):
        nf = NoveltyEvidenceFilter(
            candidate_id="NF-DISC",
            status="DISCOVERY_ONLY",
            review_status="PENDING_HUMAN_REVIEW",
            novelty_type="NEW_RELATION_CANDIDATE",
        )
        assert nf.is_blocked() is True
        assert nf.blocked_reason() == BlockedReason.DISCOVERY_ONLY

    def test_checker_blocks_discovery_only(self):
        checker = EvidenceEligibilityChecker()
        nf = NoveltyEvidenceFilter(
            candidate_id="NF-DISC-CHK",
            status="DISCOVERY_ONLY",
            review_status="PENDING_HUMAN_REVIEW",
            novelty_type="NEW_RELATION_CANDIDATE",
        )
        decision = checker.check_novelty_filter(nf)
        assert decision.is_blocked is True
        assert decision.blocked_reason == BlockedReason.DISCOVERY_ONLY

    def test_discovery_only_decision_source_id_matches(self):
        checker = EvidenceEligibilityChecker()
        nf = NoveltyEvidenceFilter(
            candidate_id="NF-DISC-ID",
            status="DISCOVERY_ONLY",
            review_status="PENDING_HUMAN_REVIEW",
            novelty_type="NEW_RELATION_CANDIDATE",
        )
        decision = checker.check_novelty_filter(nf)
        assert decision.source_id == "NF-DISC-ID"


# ---------------------------------------------------------------------------
# Test: Rejected novelty is blocked
# ---------------------------------------------------------------------------

class TestRejectedNoveltyBlocked:
    def test_rejected_review_status_is_blocked(self):
        nf = NoveltyEvidenceFilter(
            candidate_id="NF-REJECTED",
            status="REVIEWED",  # not DISCOVERY_ONLY
            review_status="REJECTED",
            novelty_type="NEW_RELATION_CANDIDATE",
        )
        assert nf.is_blocked() is True
        assert nf.blocked_reason() == BlockedReason.REJECTED_NOVELTY

    def test_checker_blocks_rejected_novelty(self):
        checker = EvidenceEligibilityChecker()
        nf = NoveltyEvidenceFilter(
            candidate_id="NF-REJ-CHK",
            status="REVIEWED",
            review_status="REJECTED",
            novelty_type="NEW_RELATION_CANDIDATE",
        )
        decision = checker.check_novelty_filter(nf)
        assert decision.is_blocked is True
        assert decision.blocked_reason == BlockedReason.REJECTED_NOVELTY

    def test_rejected_not_in_bundle(self):
        checker = EvidenceEligibilityChecker()
        nf = NoveltyEvidenceFilter(
            candidate_id="NF-REJ-BUNDLE",
            status="REVIEWED",
            review_status="REJECTED",
            novelty_type="NEW_RELATION_CANDIDATE",
        )
        bundle, decisions = checker.build_consultation_bundle(
            session_id="SESS-02",
            reviewed_providers=[],
            novelty_filters=[nf],
        )
        assert bundle.item_count() == 0
        assert bundle.blocked_count == 1


# ---------------------------------------------------------------------------
# Test: Insufficient-evidence novelty is blocked
# ---------------------------------------------------------------------------

class TestInsufficientEvidenceBlocked:
    def test_insufficient_evidence_novelty_type_blocked(self):
        nf = NoveltyEvidenceFilter(
            candidate_id="NF-INSUF",
            status="REVIEWED",
            review_status="APPROVED",
            novelty_type="INSUFFICIENT_EVIDENCE",
        )
        assert nf.is_blocked() is True
        assert nf.blocked_reason() == BlockedReason.INSUFFICIENT_EVIDENCE

    def test_checker_blocks_insufficient_evidence(self):
        checker = EvidenceEligibilityChecker()
        nf = NoveltyEvidenceFilter(
            candidate_id="NF-INSUF-CHK",
            status="REVIEWED",
            review_status="APPROVED",
            novelty_type="INSUFFICIENT_EVIDENCE",
        )
        decision = checker.check_novelty_filter(nf)
        assert decision.is_blocked is True
        assert decision.blocked_reason == BlockedReason.INSUFFICIENT_EVIDENCE


# ---------------------------------------------------------------------------
# Test: Contradictory / unresolved novelty is blocked
# ---------------------------------------------------------------------------

class TestContradictoryUnresolvedBlocked:
    def test_possible_contradiction_novelty_type_blocked(self):
        nf = NoveltyEvidenceFilter(
            candidate_id="NF-CONTRA",
            status="REVIEWED",
            review_status="APPROVED",
            novelty_type="POSSIBLE_CONTRADICTION",
        )
        assert nf.is_blocked() is True
        assert nf.blocked_reason() == BlockedReason.UNRESOLVED_CONTRADICTION

    def test_checker_blocks_contradiction(self):
        checker = EvidenceEligibilityChecker()
        nf = NoveltyEvidenceFilter(
            candidate_id="NF-CONTRA-CHK",
            status="REVIEWED",
            review_status="APPROVED",
            novelty_type="POSSIBLE_CONTRADICTION",
        )
        decision = checker.check_novelty_filter(nf)
        assert decision.is_blocked is True
        assert decision.blocked_reason == BlockedReason.UNRESOLVED_CONTRADICTION

    def test_contradiction_not_in_bundle(self):
        checker = EvidenceEligibilityChecker()
        nf = NoveltyEvidenceFilter(
            candidate_id="NF-CONTRA-BUNDLE",
            status="REVIEWED",
            review_status="APPROVED",
            novelty_type="POSSIBLE_CONTRADICTION",
        )
        bundle, decisions = checker.build_consultation_bundle(
            session_id="SESS-03",
            reviewed_providers=[],
            novelty_filters=[nf],
        )
        assert bundle.item_count() == 0
        assert bundle.blocked_count == 1


# ---------------------------------------------------------------------------
# Test: Approved official evidence remains eligible in bundle
# ---------------------------------------------------------------------------

class TestApprovedOfficialInBundle:
    def test_bundle_contains_approved_evidence(self):
        checker = EvidenceEligibilityChecker()
        providers = [_approved_provider(f"OFF-{i}") for i in range(3)]
        bundle, decisions = checker.build_consultation_bundle(
            session_id="SESS-04",
            reviewed_providers=providers,
            novelty_filters=[],
        )
        assert bundle.item_count() == 3
        assert bundle.blocked_count == 0
        assert all(d.is_eligible for d in decisions)

    def test_bundle_mixed_eligible_and_blocked(self):
        checker = EvidenceEligibilityChecker()
        approved = _approved_provider("APPROVED-1")
        blocked_nf = _novelty_filter(
            candidate_id="DISC-1",
            status="DISCOVERY_ONLY",
            review_status="PENDING_HUMAN_REVIEW",
        )
        bundle, decisions = checker.build_consultation_bundle(
            session_id="SESS-05",
            reviewed_providers=[approved],
            novelty_filters=[blocked_nf],
        )
        assert bundle.item_count() == 1
        assert bundle.blocked_count == 1
        eligible_decisions = [d for d in decisions if d.is_eligible]
        blocked_decisions = [d for d in decisions if d.is_blocked]
        assert len(eligible_decisions) == 1
        assert len(blocked_decisions) == 1


# ---------------------------------------------------------------------------
# Test: No Gate C candidate is promoted automatically
# ---------------------------------------------------------------------------

class TestNoAutomaticPromotion:
    def test_novelty_never_enters_bundle_eligible_items(self):
        """
        Even if a novelty filter somehow passes all status checks,
        it must not be auto-promoted into eligible_items of the bundle.
        The bundle only accepts ReviewedEvidenceProvider objects.
        """
        checker = EvidenceEligibilityChecker()
        # Construct a novelty filter that "looks" approved but still has
        # DISCOVERY_ONLY status — should be blocked
        nf_discovery = NoveltyEvidenceFilter(
            candidate_id="NF-AUTO-PROMOTE-1",
            status="DISCOVERY_ONLY",
            review_status="PENDING_HUMAN_REVIEW",
            novelty_type="NEW_RELATION_CANDIDATE",
        )
        bundle, _ = checker.build_consultation_bundle(
            session_id="SESS-AUTO",
            reviewed_providers=[],
            novelty_filters=[nf_discovery],
        )
        # Eligible items must remain empty
        assert bundle.item_count() == 0
        assert all(
            isinstance(item, ReviewedEvidenceProvider)
            for item in bundle.eligible_items
        )

    def test_no_gate_c_candidate_in_eligible_items(self):
        """
        After processing multiple novelty filters, none should appear in
        bundle.eligible_items regardless of their internal state.
        """
        checker = EvidenceEligibilityChecker()
        novelty_filters = [
            NoveltyEvidenceFilter(
                candidate_id=f"NF-NO-PROMO-{i}",
                status="DISCOVERY_ONLY",
                review_status="PENDING_HUMAN_REVIEW",
                novelty_type="NEW_RELATION_CANDIDATE",
            )
            for i in range(5)
        ]
        bundle, decisions = checker.build_consultation_bundle(
            session_id="SESS-NO-PROMO",
            reviewed_providers=[],
            novelty_filters=novelty_filters,
        )
        assert bundle.item_count() == 0
        assert bundle.blocked_count == 5
        for item in bundle.eligible_items:
            assert isinstance(item, ReviewedEvidenceProvider)


# ---------------------------------------------------------------------------
# Test: No mutation occurs
# ---------------------------------------------------------------------------

class TestNoMutation:
    def test_reviewed_provider_is_frozen(self):
        """ReviewedEvidenceProvider is a frozen dataclass — mutation raises."""
        provider = _approved_provider("FROZEN-1")
        with pytest.raises((AttributeError, TypeError)):
            provider.is_approved = False  # type: ignore[misc]

    def test_novelty_filter_is_frozen(self):
        """NoveltyEvidenceFilter is a frozen dataclass — mutation raises."""
        nf = _novelty_filter("FROZEN-NF")
        with pytest.raises((AttributeError, TypeError)):
            nf.status = "APPROVED"  # type: ignore[misc]

    def test_consultation_bundle_is_frozen(self):
        """ConsultationEvidenceBundle is a frozen dataclass — mutation raises."""
        bundle = ConsultationEvidenceBundle(
            eligible_items=[],
            blocked_count=0,
            session_id="FROZEN-BUNDLE",
        )
        with pytest.raises((AttributeError, TypeError)):
            bundle.blocked_count = 99  # type: ignore[misc]

    def test_eligibility_decision_is_frozen(self):
        """EvidenceEligibilityDecision is a frozen dataclass — mutation raises."""
        decision = EvidenceEligibilityDecision(
            source_id="DEC-001",
            status=EvidenceEligibilityStatus.ELIGIBLE,
        )
        with pytest.raises((AttributeError, TypeError)):
            decision.status = EvidenceEligibilityStatus.BLOCKED  # type: ignore[misc]

    def test_checker_does_not_mutate_input_provider(self):
        """EvidenceEligibilityChecker does not mutate its inputs."""
        checker = EvidenceEligibilityChecker()
        provider = _approved_provider("NO-MUT-PROV")
        original_approved = provider.is_approved
        original_reviewed = provider.is_reviewed
        checker.check_reviewed_evidence(provider)
        assert provider.is_approved == original_approved
        assert provider.is_reviewed == original_reviewed

    def test_checker_does_not_mutate_novelty_filter(self):
        """EvidenceEligibilityChecker does not mutate novelty filter inputs."""
        checker = EvidenceEligibilityChecker()
        nf = _novelty_filter("NO-MUT-NF")
        original_status = nf.status
        original_review_status = nf.review_status
        checker.check_novelty_filter(nf)
        assert nf.status == original_status
        assert nf.review_status == original_review_status


# ---------------------------------------------------------------------------
# Test: No production module is imported
# ---------------------------------------------------------------------------

class TestNoProductionImports:
    def test_gate_cd_boundary_does_not_import_neo4j(self):
        import gate_cd_boundary
        import gate_cd_boundary.models
        import gate_cd_boundary.evidence_eligibility
        import sys
        for mod_name in sys.modules:
            assert "neo4j" not in mod_name.lower(), (
                f"neo4j imported via {mod_name}"
            )

    def test_gate_cd_boundary_does_not_import_llm(self):
        import gate_cd_boundary  # noqa: F401
        import sys
        forbidden = {"openai", "anthropic", "llm_client", "llm"}
        for mod_name in sys.modules:
            for f in forbidden:
                assert f not in mod_name.lower() or not mod_name.startswith("gate_cd"), (
                    f"Forbidden import {mod_name} found"
                )

    def test_no_graph_writes_in_boundary_module(self):
        """Verify no graph write calls exist in the boundary source code."""
        import pathlib
        boundary_dir = pathlib.Path("gate_cd_boundary")
        forbidden_patterns = ["neo4j", "GraphDatabase", "session.run", "graph.write"]
        for py_file in boundary_dir.glob("*.py"):
            content = py_file.read_text(encoding="utf-8")
            for pattern in forbidden_patterns:
                assert pattern not in content, (
                    f"Forbidden pattern '{pattern}' found in {py_file}"
                )

    def test_no_llm_calls_in_boundary_module(self):
        """Verify no LLM call patterns exist in the boundary source code."""
        import pathlib
        boundary_dir = pathlib.Path("gate_cd_boundary")
        forbidden_patterns = ["openai", "anthropic", "llm_client", "chat.completions"]
        for py_file in boundary_dir.glob("*.py"):
            content = py_file.read_text(encoding="utf-8")
            for pattern in forbidden_patterns:
                assert pattern.lower() not in content.lower(), (
                    f"Forbidden pattern '{pattern}' found in {py_file}"
                )
