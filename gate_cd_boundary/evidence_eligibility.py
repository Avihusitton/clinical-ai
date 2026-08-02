"""
gate_cd_boundary/evidence_eligibility.py
-----------------------------------------
Core boundary logic: determines which evidence items from Gate C
may legally cross into Gate D.

Rules (deterministic, no external dependencies):
  ALLOWED:
    - Approved official knowledge (ReviewedEvidenceProvider with is_approved=True, is_reviewed=True)
    - Reviewed relationships (is_reviewed=True)
    - Approved reviewed exercises (is_approved=True)

  BLOCKED:
    - DISCOVERY_ONLY novelty
    - PENDING_HUMAN_REVIEW novelty
    - Rejected novelty
    - Insufficient-evidence novelty
    - Unresolved contradictions (POSSIBLE_CONTRADICTION)

No production modules imported.  No Neo4j.  No LLM.  No graph writes.
"""
from __future__ import annotations

from typing import List, Tuple

from .models import (
    ReviewedEvidenceProvider,
    NoveltyEvidenceFilter,
    ConsultationEvidenceBundle,
    EvidenceEligibilityDecision,
    EvidenceEligibilityStatus,
    BlockedReason,
)


class EvidenceEligibilityChecker:
    """
    Deterministic, stateless boundary checker.

    Evaluates whether a ReviewedEvidenceProvider or NoveltyEvidenceFilter
    is eligible to be consumed by Gate D.

    Invariants:
    - No mutations are performed on any input object.
    - No external I/O is performed.
    - No production modules (Neo4j, LLM, graph writes) are used.
    - No Gate C candidate is automatically promoted.
    """

    def check_reviewed_evidence(
        self, provider: ReviewedEvidenceProvider
    ) -> EvidenceEligibilityDecision:
        """
        Check a ReviewedEvidenceProvider for eligibility.

        Eligible if and only if: is_approved=True AND is_reviewed=True.
        """
        if provider.is_eligible():
            return EvidenceEligibilityDecision(
                source_id=provider.source_id,
                status=EvidenceEligibilityStatus.ELIGIBLE,
                blocked_reason=None,
                notes="Approved and reviewed evidence; eligible for Gate D consumption.",
            )
        else:
            return EvidenceEligibilityDecision(
                source_id=provider.source_id,
                status=EvidenceEligibilityStatus.BLOCKED,
                blocked_reason=BlockedReason.PENDING_HUMAN_REVIEW,
                notes="Evidence is not fully approved and reviewed.",
            )

    def check_novelty_filter(
        self, novelty: NoveltyEvidenceFilter
    ) -> EvidenceEligibilityDecision:
        """
        Check a NoveltyEvidenceFilter for eligibility.

        Blocked if status=DISCOVERY_ONLY, or review_status is
        PENDING_HUMAN_REVIEW/REJECTED, or novelty_type indicates
        insufficient evidence or contradiction.
        """
        if novelty.is_blocked():
            reason = novelty.blocked_reason()
            return EvidenceEligibilityDecision(
                source_id=novelty.candidate_id,
                status=EvidenceEligibilityStatus.BLOCKED,
                blocked_reason=reason,
                notes=(
                    f"Novelty candidate blocked. "
                    f"status={novelty.status!r}, "
                    f"review_status={novelty.review_status!r}, "
                    f"novelty_type={novelty.novelty_type!r}"
                ),
            )
        return EvidenceEligibilityDecision(
            source_id=novelty.candidate_id,
            status=EvidenceEligibilityStatus.ELIGIBLE,
            blocked_reason=None,
            notes="Novelty candidate has passed human review; eligible for Gate D.",
        )

    def build_consultation_bundle(
        self,
        session_id: str,
        reviewed_providers: List[ReviewedEvidenceProvider],
        novelty_filters: List[NoveltyEvidenceFilter],
    ) -> Tuple[ConsultationEvidenceBundle, List[EvidenceEligibilityDecision]]:
        """
        Build an immutable ConsultationEvidenceBundle from a mix of
        ReviewedEvidenceProvider and NoveltyEvidenceFilter inputs.

        Returns:
            (bundle, decisions)
            - bundle: ConsultationEvidenceBundle containing only eligible items
            - decisions: list of EvidenceEligibilityDecision for audit purposes

        No mutations performed.  No automatic promotion of Gate C candidates.
        """
        decisions: List[EvidenceEligibilityDecision] = []
        eligible_items: List[ReviewedEvidenceProvider] = []
        blocked_count = 0

        # Evaluate reviewed evidence providers
        for provider in reviewed_providers:
            decision = self.check_reviewed_evidence(provider)
            decisions.append(decision)
            if decision.is_eligible:
                eligible_items.append(provider)
            else:
                blocked_count += 1

        # Evaluate novelty evidence filters
        for novelty in novelty_filters:
            decision = self.check_novelty_filter(novelty)
            decisions.append(decision)
            if not decision.is_eligible:
                blocked_count += 1
            # Novelty candidates are NEVER auto-promoted into eligible_items.
            # Even if somehow eligible, only ReviewedEvidenceProvider can be placed
            # into the bundle — Gate C candidates need explicit human promotion.

        bundle = ConsultationEvidenceBundle(
            eligible_items=eligible_items,
            blocked_count=blocked_count,
            session_id=session_id,
        )
        return bundle, decisions
