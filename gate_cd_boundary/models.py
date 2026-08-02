"""
gate_cd_boundary/models.py
--------------------------
Pure data models for the Gate C → Gate D boundary layer.

Rules enforced at the boundary:
  ALLOWED into Gate D:
    - approved official knowledge
    - reviewed relationships
    - approved reviewed exercises

  BLOCKED from Gate D:
    - DISCOVERY_ONLY novelty
    - PENDING_HUMAN_REVIEW novelty
    - rejected novelty
    - insufficient-evidence novelty
    - unresolved contradictions

No production modules imported.  No Neo4j.  No LLM.  No graph writes.
"""
from __future__ import annotations

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional


class EvidenceEligibilityStatus(str, Enum):
    """Eligibility verdict at the Gate C/D boundary."""
    ELIGIBLE = "ELIGIBLE"
    BLOCKED = "BLOCKED"


class BlockedReason(str, Enum):
    """Reason why evidence was blocked from crossing the boundary."""
    DISCOVERY_ONLY = "DISCOVERY_ONLY"
    PENDING_HUMAN_REVIEW = "PENDING_HUMAN_REVIEW"
    REJECTED_NOVELTY = "REJECTED_NOVELTY"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    UNRESOLVED_CONTRADICTION = "UNRESOLVED_CONTRADICTION"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"



@dataclass(frozen=True)
class ReviewedEvidenceProvider:
    """
    Represents an approved, reviewed evidence item that is eligible
    for consumption by Gate D.

    Only evidence that has passed human review and been explicitly approved
    may cross the Gate C → Gate D boundary.
    """
    source_id: str
    content_summary: str
    provenance: str
    is_approved: bool = True  # Must be True to be eligible
    is_reviewed: bool = True  # Must be True to be eligible

    def is_eligible(self) -> bool:
        """Returns True only if evidence is both approved and reviewed."""
        return self.is_approved and self.is_reviewed


@dataclass(frozen=True)
class NoveltyEvidenceFilter:
    """
    Represents a Gate C novelty candidate at the boundary.

    Tracks the novelty status fields that determine whether a candidate
    is allowed to cross into Gate D.

    Gate D may NOT consume:
      - DISCOVERY_ONLY novelty
      - PENDING_HUMAN_REVIEW novelty
      - rejected novelty
      - insufficient-evidence novelty
      - unresolved contradictions
    """
    candidate_id: str
    status: str          # e.g. "DISCOVERY_ONLY"
    review_status: str   # e.g. "PENDING_HUMAN_REVIEW", "APPROVED", "REJECTED"
    novelty_type: str    # e.g. "NEW_RELATION_CANDIDATE", "POSSIBLE_CONTRADICTION", etc.

    # Blocked statuses — exact string constants
    _BLOCKED_STATUSES: frozenset = field(
        default=frozenset({"DISCOVERY_ONLY"}),
        init=False,
        repr=False,
        compare=False,
    )
    _BLOCKED_REVIEW_STATUSES: frozenset = field(
        default=frozenset({"PENDING_HUMAN_REVIEW", "REJECTED"}),
        init=False,
        repr=False,
        compare=False,
    )
    _BLOCKED_NOVELTY_TYPES: frozenset = field(
        default=frozenset({
            "INSUFFICIENT_EVIDENCE",
            "POSSIBLE_CONTRADICTION",
            "OUT_OF_SCOPE",
        }),
        init=False,
        repr=False,
        compare=False,
    )

    def is_blocked(self) -> bool:
        """
        Returns True if this novelty candidate is ineligible to cross into Gate D.

        Blocked if ANY of:
          - status is DISCOVERY_ONLY
          - review_status is PENDING_HUMAN_REVIEW or REJECTED
          - novelty_type is INSUFFICIENT_EVIDENCE, POSSIBLE_CONTRADICTION, or OUT_OF_SCOPE
        """
        if self.status in self._BLOCKED_STATUSES:
            return True
        if self.review_status in self._BLOCKED_REVIEW_STATUSES:
            return True
        if self.novelty_type in self._BLOCKED_NOVELTY_TYPES:
            return True
        return False

    def blocked_reason(self) -> Optional[BlockedReason]:
        """Returns the primary blocking reason, or None if not blocked."""
        if self.status == "DISCOVERY_ONLY":
            return BlockedReason.DISCOVERY_ONLY
        if self.review_status == "PENDING_HUMAN_REVIEW":
            return BlockedReason.PENDING_HUMAN_REVIEW
        if self.review_status == "REJECTED":
            return BlockedReason.REJECTED_NOVELTY
        if self.novelty_type == "INSUFFICIENT_EVIDENCE":
            return BlockedReason.INSUFFICIENT_EVIDENCE
        if self.novelty_type == "POSSIBLE_CONTRADICTION":
            return BlockedReason.UNRESOLVED_CONTRADICTION
        if self.novelty_type == "OUT_OF_SCOPE":
            return BlockedReason.OUT_OF_SCOPE
        return None


@dataclass(frozen=True)
class ConsultationEvidenceBundle:
    """
    Represents the set of evidence that has been validated as eligible
    for use in a Gate D consultation.

    Only contains ReviewedEvidenceProvider entries that passed eligibility.
    Immutable — no mutation is possible after construction.
    """
    eligible_items: List[ReviewedEvidenceProvider] = field(default_factory=list)
    blocked_count: int = 0
    session_id: str = ""

    def item_count(self) -> int:
        """Returns the number of eligible evidence items."""
        return len(self.eligible_items)


@dataclass(frozen=True)
class EvidenceEligibilityDecision:
    """
    Decision record produced by the boundary eligibility check.
    Records why an item was allowed or blocked.
    Immutable — no mutation after construction.
    """
    source_id: str
    status: EvidenceEligibilityStatus
    blocked_reason: Optional[BlockedReason] = None
    notes: str = ""

    @property
    def is_eligible(self) -> bool:
        return self.status == EvidenceEligibilityStatus.ELIGIBLE

    @property
    def is_blocked(self) -> bool:
        return self.status == EvidenceEligibilityStatus.BLOCKED
