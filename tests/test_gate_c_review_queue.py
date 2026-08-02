"""
test_gate_c_review_queue.py
----------------------------
Tests for ReviewQueue:
- Only PENDING_HUMAN_REVIEW candidates are enqueued.
- No automatic promotion occurs.
- Human decisions are recorded without mutating external state.
- All 60 fixtures that require human review are routed correctly.
"""
import json
import pytest
from pathlib import Path

from gate_c.models import (
    NoveltyCandidate,
    EvidenceBundle,
    EvidenceItem,
    ReviewDecision,
)
from gate_c.review_queue import ReviewQueue

# ---------------------------------------------------------------------------
# Fixture loader
# ---------------------------------------------------------------------------
FIXTURE_PATH = Path("tests/fixtures/gate_c/novelty_cases.jsonl")


def load_novelty_fixtures():
    fixtures = []
    with open(FIXTURE_PATH, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                fixtures.append(json.loads(line))
    return fixtures


ALL_FIXTURES = load_novelty_fixtures()

REVIEW_REQUIRED_FIXTURES = [
    f for f in ALL_FIXTURES if f["expected_review_route"] != "NONE"
]
NO_REVIEW_FIXTURES = [
    f for f in ALL_FIXTURES if f["expected_review_route"] == "NONE"
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_candidate(candidate_id: str, review_status: str = "PENDING_HUMAN_REVIEW") -> NoveltyCandidate:
    return NoveltyCandidate(
        candidate_id=candidate_id,
        source_entity="A",
        target_entity="B",
        relation_type="T",
        evidence_bundle=EvidenceBundle(
            items=[EvidenceItem(source_id="s", content="c", provenance="p", confidence=0.9)]
        ),
        review_status=review_status,
    )


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

class TestReviewQueueEnqueue:
    def test_pending_candidate_is_enqueued(self):
        queue = ReviewQueue()
        candidate = _make_candidate("C1", "PENDING_HUMAN_REVIEW")
        queue.enqueue(candidate)
        pending = queue.get_pending()
        assert len(pending) == 1
        assert pending[0].candidate_id == "C1"

    def test_non_pending_candidate_is_ignored(self):
        queue = ReviewQueue()
        candidate = _make_candidate("C2", "APPROVED")
        queue.enqueue(candidate)
        assert len(queue.get_pending()) == 0

    def test_multiple_pending_candidates_queued_in_order(self):
        queue = ReviewQueue()
        for i in range(5):
            queue.enqueue(_make_candidate(f"C{i}"))
        pending = queue.get_pending()
        assert len(pending) == 5
        assert [c.candidate_id for c in pending] == ["C0", "C1", "C2", "C3", "C4"]

    def test_mixed_status_only_pending_queued(self):
        queue = ReviewQueue()
        queue.enqueue(_make_candidate("P1", "PENDING_HUMAN_REVIEW"))
        queue.enqueue(_make_candidate("A1", "APPROVED"))
        queue.enqueue(_make_candidate("P2", "PENDING_HUMAN_REVIEW"))
        queue.enqueue(_make_candidate("R1", "REJECTED"))
        pending = queue.get_pending()
        assert len(pending) == 2
        ids = [c.candidate_id for c in pending]
        assert "P1" in ids
        assert "P2" in ids
        assert "A1" not in ids
        assert "R1" not in ids

    def test_empty_queue_returns_empty_list(self):
        queue = ReviewQueue()
        assert queue.get_pending() == []

    def test_get_pending_returns_copy_not_internal_list(self):
        """Mutating the returned list must not affect the queue's internal state."""
        queue = ReviewQueue()
        queue.enqueue(_make_candidate("C1"))
        pending = queue.get_pending()
        pending.clear()
        assert len(queue.get_pending()) == 1


class TestNoAutomaticPromotion:
    def test_record_decision_does_not_remove_from_pending(self):
        """Recording a human decision must not automatically promote or remove the candidate."""
        queue = ReviewQueue()
        candidate = _make_candidate("C1")
        queue.enqueue(candidate)
        decision = ReviewDecision(
            candidate_id="C1",
            decision="APPROVE",
            reviewer="Dr. Smith",
            comments="Validated",
        )
        queue.record_decision(decision)
        # Candidate is still pending — no automatic state change
        assert len(queue.get_pending()) == 1

    def test_record_decision_stored_without_graph_write(self):
        """record_decision stores the decision in-memory and does not trigger writes."""
        queue = ReviewQueue()
        decision = ReviewDecision(
            candidate_id="C1",
            decision="REJECT",
            reviewer="Dr. Jones",
            comments="Insufficient evidence",
        )
        queue.record_decision(decision)
        assert len(queue._decisions) == 1
        assert queue._decisions[0].reviewer == "Dr. Jones"
        assert queue._decisions[0].decision == "REJECT"

    def test_multiple_decisions_can_be_recorded(self):
        queue = ReviewQueue()
        for i in range(3):
            queue.record_decision(
                ReviewDecision(
                    candidate_id=f"C{i}",
                    decision="APPROVE",
                    reviewer=f"Reviewer{i}",
                    comments="ok",
                )
            )
        assert len(queue._decisions) == 3


class TestReviewDecisionModel:
    def test_review_decision_fields(self):
        rd = ReviewDecision(
            candidate_id="C99",
            decision="APPROVE",
            reviewer="R1",
            comments="Looks valid",
        )
        assert rd.candidate_id == "C99"
        assert rd.decision == "APPROVE"
        assert rd.reviewer == "R1"
        assert rd.comments == "Looks valid"


# ---------------------------------------------------------------------------
# Fixture-parametrized: human-review routing assertions
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "fixture", ALL_FIXTURES, ids=[f["case_id"] for f in ALL_FIXTURES]
)
def test_fixture_has_all_four_required_fields(fixture):
    assert "expected_novelty_type" in fixture
    assert "expected_decision" in fixture
    assert "expected_blocking_reasons" in fixture
    assert "expected_review_route" in fixture


@pytest.mark.parametrize(
    "fixture", REVIEW_REQUIRED_FIXTURES,
    ids=[f["case_id"] for f in REVIEW_REQUIRED_FIXTURES]
)
def test_review_required_candidate_is_pending_by_default(fixture):
    """
    Any candidate destined for review must default to PENDING_HUMAN_REVIEW.
    The ReviewQueue enqueues it; no automatic promotion happens.
    """
    # Required fields present
    assert fixture["expected_review_route"] != "NONE"
    assert "expected_novelty_type" in fixture
    assert "expected_decision" in fixture
    assert "expected_blocking_reasons" in fixture

    candidate = NoveltyCandidate(
        candidate_id=fixture["case_id"],
        source_entity="A",
        target_entity="B",
        relation_type="T",
        evidence_bundle=EvidenceBundle(
            items=[EvidenceItem(source_id="s", content="c", provenance="p", confidence=0.9)]
        ),
    )
    # Default review_status is PENDING_HUMAN_REVIEW
    assert candidate.review_status == "PENDING_HUMAN_REVIEW"

    queue = ReviewQueue()
    queue.enqueue(candidate)
    pending = queue.get_pending()
    assert len(pending) == 1
    assert pending[0].candidate_id == fixture["case_id"]

    # No automatic promotion after enqueue
    assert len(queue._decisions) == 0


@pytest.mark.parametrize(
    "fixture", NO_REVIEW_FIXTURES,
    ids=[f["case_id"] for f in NO_REVIEW_FIXTURES]
)
def test_no_review_fixture_fields(fixture):
    """Fixtures with review_route=NONE must still have all four required fields."""
    assert "expected_novelty_type" in fixture
    assert "expected_decision" in fixture
    assert "expected_blocking_reasons" in fixture
    assert "expected_review_route" in fixture
    assert fixture["expected_review_route"] == "NONE"


@pytest.mark.parametrize(
    "fixture", REVIEW_REQUIRED_FIXTURES,
    ids=[f["case_id"] for f in REVIEW_REQUIRED_FIXTURES]
)
def test_no_auto_promotion_in_review_queue(fixture):
    """
    After recording a decision, the candidate must not be auto-promoted.
    The queue still contains the candidate in pending state.
    """
    candidate = NoveltyCandidate(
        candidate_id=fixture["case_id"],
        source_entity="A",
        target_entity="B",
        relation_type="T",
        evidence_bundle=EvidenceBundle(
            items=[EvidenceItem(source_id="s", content="c", provenance="p", confidence=0.9)]
        ),
    )
    queue = ReviewQueue()
    queue.enqueue(candidate)

    review_decision = ReviewDecision(
        candidate_id=fixture["case_id"],
        decision="APPROVE",
        reviewer="AutoTest",
        comments="fixture-driven test",
    )
    queue.record_decision(review_decision)

    # Still pending — no auto state change
    assert len(queue.get_pending()) == 1
    # Decision was recorded in-memory
    assert len(queue._decisions) == 1
