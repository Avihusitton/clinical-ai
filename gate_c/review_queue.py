from typing import List
from .models import NoveltyCandidate, ReviewDecision

class ReviewQueue:
    """
    Deterministic queue to manage candidates pending human review.
    Enforces NO automatic approval or promotion.
    """
    def __init__(self):
        self._queue: List[NoveltyCandidate] = []
        self._decisions: List[ReviewDecision] = []

    def enqueue(self, candidate: NoveltyCandidate):
        # Every non-known candidate requires PENDING_HUMAN_REVIEW
        if candidate.review_status == "PENDING_HUMAN_REVIEW":
            self._queue.append(candidate)

    def get_pending(self) -> List[NoveltyCandidate]:
        return list(self._queue)

    def record_decision(self, decision: ReviewDecision):
        """
        Record a human review decision.
        Note: This does not automatically mutate external state.
        """
        self._decisions.append(decision)
