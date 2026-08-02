"""
gate_cd_boundary/__init__.py
-----------------------------
Public interface for the Gate C → Gate D boundary layer.

Exposes only the four required public interfaces:
  ReviewedEvidenceProvider
  NoveltyEvidenceFilter
  ConsultationEvidenceBundle
  EvidenceEligibilityDecision

And supporting types:
  EvidenceEligibilityStatus
  BlockedReason
  EvidenceEligibilityChecker

No production modules imported.  No Neo4j.  No LLM.  No graph writes.
"""
from .models import (
    ReviewedEvidenceProvider,
    NoveltyEvidenceFilter,
    ConsultationEvidenceBundle,
    EvidenceEligibilityDecision,
    EvidenceEligibilityStatus,
    BlockedReason,
)
from .evidence_eligibility import EvidenceEligibilityChecker

__all__ = [
    # Required public interfaces
    "ReviewedEvidenceProvider",
    "NoveltyEvidenceFilter",
    "ConsultationEvidenceBundle",
    "EvidenceEligibilityDecision",
    # Supporting types
    "EvidenceEligibilityStatus",
    "BlockedReason",
    "EvidenceEligibilityChecker",
]
