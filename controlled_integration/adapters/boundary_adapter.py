"""
controlled_integration/adapters/boundary_adapter.py
---------------------------------------------------
Adapter wrapping Gate C/D boundary interfaces (gate_cd_boundary/models.py, gate_cd_boundary/evidence_eligibility.py).
Enforces eligibility screening. Ensures Gate D NEVER consumes unreviewed Gate C novelty.
"""

from typing import List, Dict, Any, Tuple, Optional
from gate_cd_boundary.models import ReviewedEvidenceProvider, NoveltyEvidenceFilter
from gate_cd_boundary.evidence_eligibility import EvidenceEligibilityChecker
from ..models import OfficialEvidenceBundle, NoveltyDiscoveryBundle, ConsultationInputBundle
from ..exceptions import UnreviewedNoveltyLeakError

class BoundaryAdapter:
    """
    Boundary adapter screening evidence before it can cross from Gate C/B into Gate D.
    Stateless, deterministic, zero side effects.
    """
    def __init__(self):
        self.checker = EvidenceEligibilityChecker()

    def filter_for_consultation(
        self,
        session_id: str,
        official_bundle: OfficialEvidenceBundle,
        novelty_bundle: Optional[NoveltyDiscoveryBundle] = None
    ) -> ConsultationInputBundle:
        """
        Filters evidence items through Gate C/D boundary checker.
        Rejects all unreviewed novelty candidates.
        """
        reviewed_providers: List[ReviewedEvidenceProvider] = []
        for entry in official_bundle.official_entries:
            is_approved = entry.get("is_approved")
            if is_approved is None:
                is_approved = (entry.get("review_state", "APPROVED") == "APPROVED")

            is_reviewed = entry.get("is_reviewed")
            if is_reviewed is None:
                is_reviewed = (entry.get("review_state", "APPROVED") == "APPROVED")

            reviewed_providers.append(
                ReviewedEvidenceProvider(
                    source_id=entry.get("source_id", "UNKNOWN"),
                    content_summary=entry.get("content_summary", ""),
                    provenance=entry.get("provenance", "Official Method"),
                    is_approved=bool(is_approved),
                    is_reviewed=bool(is_reviewed)
                )
            )

        novelty_filters: List[NoveltyEvidenceFilter] = []
        if novelty_bundle:
            for cand in novelty_bundle.candidates:
                nf = NoveltyEvidenceFilter(
                    candidate_id=cand.get("candidate_id", "NOV_UNKNOWN"),
                    status=cand.get("status", "DISCOVERY_ONLY"),
                    review_status=cand.get("review_status", "PENDING_HUMAN_REVIEW"),
                    novelty_type=cand.get("novelty_type", "NEW_RELATION_CANDIDATE")
                )
                novelty_filters.append(nf)
                # Strict check: If novelty item attempts unreviewed bypass, raise exception
                if (nf.is_blocked() and cand.get("force_leak", False)) or (cand.get("status") == "DISCOVERY_ONLY" and cand.get("force_leak", False)):
                    raise UnreviewedNoveltyLeakError(
                        candidate_id=nf.candidate_id,
                        status=nf.status,
                        review_status=nf.review_status
                    )

        bundle, decisions = self.checker.build_consultation_bundle(
            session_id=session_id,
            reviewed_providers=reviewed_providers,
            novelty_filters=novelty_filters
        )

        eligible_dicts = [
            {
                "source_id": item.source_id,
                "content_summary": item.content_summary,
                "provenance": item.provenance,
                "is_approved": item.is_approved,
                "is_reviewed": item.is_reviewed
            }
            for item in bundle.eligible_items
        ]

        decision_dicts = [
            {
                "source_id": d.source_id,
                "status": d.status.value if hasattr(d.status, "value") else str(d.status),
                "blocked_reason": d.blocked_reason.value if (d.blocked_reason and hasattr(d.blocked_reason, "value")) else (str(d.blocked_reason) if d.blocked_reason else None),
                "notes": d.notes
            }
            for d in decisions
        ]

        return ConsultationInputBundle(
            session_id=session_id,
            eligible_official_evidence=eligible_dicts,
            blocked_novelty_count=bundle.blocked_count,
            boundary_decisions=decision_dicts,
            is_validated=True
        )
