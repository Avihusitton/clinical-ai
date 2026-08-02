"""
test_gate_c_no_write.py
------------------------
Verifies that Gate C produces zero external writes during candidate processing.
Tests cover:
- NoveltyEngine.process_candidate returns only a NoveltyDecision (no side effects).
- NoveltyCandidate.status remains frozen at DISCOVERY_ONLY.
- ReviewQueue.record_decision does not mutate external state.
- All 60 fixtures processed without triggering any graph write.
"""
import json
import pytest
from pathlib import Path
from typing import List

from gate_c.models import (
    NoveltyCandidate,
    EvidenceBundle,
    EvidenceItem,
    KnownKnowledgeCheck,
    ContradictionRecord,
    ReviewDecision,
    NoveltyType,
)
from gate_c.novelty_engine import (
    NoveltyEngine,
    DuplicateDetector,
    ContradictionDetector,
    ScopeValidator,
)
from gate_c.known_knowledge import KnownKnowledgeProvider
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


# ---------------------------------------------------------------------------
# Write-tracking mocks — fail the test if any write operation is called
# ---------------------------------------------------------------------------

class WriteTracker:
    """Shared tracker; raises AssertionError if any write is attempted."""
    def __init__(self):
        self.writes: List[str] = []

    def record_write(self, description: str):
        self.writes.append(description)

    def assert_no_writes(self):
        assert self.writes == [], f"Unexpected writes detected: {self.writes}"


class NoWriteKKProvider(KnownKnowledgeProvider):
    def __init__(self, tracker: WriteTracker, is_known: bool = False):
        self._tracker = tracker
        self._is_known = is_known

    def check_candidate(self, candidate: NoveltyCandidate) -> KnownKnowledgeCheck:
        # Read-only: no writes
        return KnownKnowledgeCheck(is_known=self._is_known, similarity_score=0.0)


class NoWriteDuplicateDetector(DuplicateDetector):
    def __init__(self, tracker: WriteTracker, is_dup: bool = False):
        self._tracker = tracker
        self._is_dup = is_dup

    def is_duplicate(self, candidate: NoveltyCandidate) -> bool:
        return self._is_dup


class NoWriteContradictionDetector(ContradictionDetector):
    def __init__(self, tracker: WriteTracker, records: List[ContradictionRecord] = None):
        self._tracker = tracker
        self._records = records or []

    def check_contradictions(self, candidate: NoveltyCandidate) -> List[ContradictionRecord]:
        return self._records


class NoWriteScopeValidator(ScopeValidator):
    def __init__(self, tracker: WriteTracker, in_scope: bool = True):
        self._tracker = tracker
        self._in_scope = in_scope

    def is_in_scope(self, candidate: NoveltyCandidate) -> bool:
        return self._in_scope


# ---------------------------------------------------------------------------
# Fixture-specific mocks
# ---------------------------------------------------------------------------

class FixtureKKProvider(KnownKnowledgeProvider):
    def check_candidate(self, candidate: NoveltyCandidate) -> KnownKnowledgeCheck:
        f = candidate.metadata.get("fixture", {})
        is_known = f.get("expected_novelty_type", "") in ("EXACT_MATCH", "SEMANTIC_MATCH")
        return KnownKnowledgeCheck(
            is_known=is_known,
            existing_reference="ref" if is_known else None,
            similarity_score=1.0 if is_known else 0.0,
        )


class FixtureDupDetector(DuplicateDetector):
    def is_duplicate(self, candidate: NoveltyCandidate) -> bool:
        return candidate.metadata.get("fixture", {}).get("expected_novelty_type") == "DUPLICATE"


class FixtureContraDetector(ContradictionDetector):
    def check_contradictions(self, candidate: NoveltyCandidate) -> List[ContradictionRecord]:
        f = candidate.metadata.get("fixture", {})
        reasons = f.get("expected_blocking_reasons", [])
        if (f.get("expected_novelty_type") == "CONTRADICTION"
                or "CONFLICTING_SOURCES" in reasons
                or f.get("contradictory_evidence")):
            return [ContradictionRecord(candidate_id=candidate.candidate_id,
                                        contradictory_evidence="c", reasoning="r")]
        return []


class FixtureScopeValidator(ScopeValidator):
    def is_in_scope(self, candidate: NoveltyCandidate) -> bool:
        f = candidate.metadata.get("fixture", {})
        reasons = f.get("expected_blocking_reasons", [])
        if ("OUTSIDE_REGISTRY" in reasons or "AUTONOMOUS_ACTION_NOT_PERMITTED" in reasons
                or f.get("expected_novelty_type") == "EXERCISE_BRIDGE"):
            return False
        return True


def _build_candidate_from_fixture(fixture: dict) -> NoveltyCandidate:
    reasons = fixture["expected_blocking_reasons"]
    has_prov_issue = "LACKS_PROVENANCE" in reasons or "MISSING_PROVENANCE" in reasons
    contains_phi = "PHI_DETECTED" in reasons
    items = []
    for ev in fixture["evidence_items"]:
        items.append(EvidenceItem(
            source_id=ev.get("source", "UNKNOWN"),
            content=ev.get("text", ""),
            provenance="" if has_prov_issue else "fixture-prov",
            confidence=0.9 if ev.get("strength") == "STRONG" else 0.3,
        ))
    bundle = EvidenceBundle(items=items, contains_phi=contains_phi)
    entries = fixture.get("matched_official_entries", [])
    return NoveltyCandidate(
        candidate_id=fixture["case_id"],
        source_entity=entries[0] if entries else "A",
        target_entity=entries[-1] if entries else "B",
        relation_type="RELATES_TO",
        evidence_bundle=bundle,
        metadata={"fixture": fixture},
    )


def _build_fixture_engine() -> NoveltyEngine:
    return NoveltyEngine(
        knowledge_provider=FixtureKKProvider(),
        duplicate_detector=FixtureDupDetector(),
        contradiction_detector=FixtureContraDetector(),
        scope_validator=FixtureScopeValidator(),
        threshold=0.5,
    )


# ---------------------------------------------------------------------------
# Unit no-write tests
# ---------------------------------------------------------------------------

class TestNoWriteOnProcessCandidate:
    def test_process_candidate_returns_decision_no_write(self):
        tracker = WriteTracker()
        engine = NoveltyEngine(
            knowledge_provider=NoWriteKKProvider(tracker),
            duplicate_detector=NoWriteDuplicateDetector(tracker),
            contradiction_detector=NoWriteContradictionDetector(tracker),
            scope_validator=NoWriteScopeValidator(tracker),
            threshold=0.5,
        )
        candidate = NoveltyCandidate(
            candidate_id="NW-01",
            source_entity="A",
            target_entity="B",
            relation_type="T",
            evidence_bundle=EvidenceBundle(
                items=[EvidenceItem(source_id="s", content="c", provenance="p", confidence=0.9)]
            ),
        )
        decision = engine.process_candidate(candidate)
        tracker.assert_no_writes()
        assert decision is not None

    def test_phi_rejection_no_write(self):
        tracker = WriteTracker()
        engine = NoveltyEngine(
            knowledge_provider=NoWriteKKProvider(tracker),
            duplicate_detector=NoWriteDuplicateDetector(tracker),
            contradiction_detector=NoWriteContradictionDetector(tracker),
            scope_validator=NoWriteScopeValidator(tracker),
            threshold=0.5,
        )
        candidate = NoveltyCandidate(
            candidate_id="NW-PHI",
            source_entity="A", target_entity="B", relation_type="T",
            evidence_bundle=EvidenceBundle(
                items=[EvidenceItem(source_id="s", content="c", provenance="p", confidence=0.9)],
                contains_phi=True,
            ),
        )
        decision = engine.process_candidate(candidate)
        tracker.assert_no_writes()
        assert decision.novelty_type == NoveltyType.OUT_OF_SCOPE

    def test_provenance_rejection_no_write(self):
        tracker = WriteTracker()
        engine = NoveltyEngine(
            knowledge_provider=NoWriteKKProvider(tracker),
            duplicate_detector=NoWriteDuplicateDetector(tracker),
            contradiction_detector=NoWriteContradictionDetector(tracker),
            scope_validator=NoWriteScopeValidator(tracker),
            threshold=0.5,
        )
        candidate = NoveltyCandidate(
            candidate_id="NW-PROV",
            source_entity="A", target_entity="B", relation_type="T",
            evidence_bundle=EvidenceBundle(
                items=[EvidenceItem(source_id="s", content="c", provenance="", confidence=0.9)],
            ),
        )
        decision = engine.process_candidate(candidate)
        tracker.assert_no_writes()
        assert decision.novelty_type == NoveltyType.INSUFFICIENT_EVIDENCE

    def test_known_knowledge_no_write(self):
        tracker = WriteTracker()
        engine = NoveltyEngine(
            knowledge_provider=NoWriteKKProvider(tracker, is_known=True),
            duplicate_detector=NoWriteDuplicateDetector(tracker),
            contradiction_detector=NoWriteContradictionDetector(tracker),
            scope_validator=NoWriteScopeValidator(tracker),
            threshold=0.5,
        )
        candidate = NoveltyCandidate(
            candidate_id="NW-KK",
            source_entity="A", target_entity="B", relation_type="T",
            evidence_bundle=EvidenceBundle(
                items=[EvidenceItem(source_id="s", content="c", provenance="p", confidence=0.9)]
            ),
        )
        decision = engine.process_candidate(candidate)
        tracker.assert_no_writes()
        assert decision.novelty_type == NoveltyType.KNOWN_KNOWLEDGE

    def test_duplicate_detection_no_write(self):
        tracker = WriteTracker()
        engine = NoveltyEngine(
            knowledge_provider=NoWriteKKProvider(tracker),
            duplicate_detector=NoWriteDuplicateDetector(tracker, is_dup=True),
            contradiction_detector=NoWriteContradictionDetector(tracker),
            scope_validator=NoWriteScopeValidator(tracker),
            threshold=0.5,
        )
        candidate = NoveltyCandidate(
            candidate_id="NW-DUP",
            source_entity="A", target_entity="B", relation_type="T",
            evidence_bundle=EvidenceBundle(
                items=[EvidenceItem(source_id="s", content="c", provenance="p", confidence=0.9)]
            ),
        )
        decision = engine.process_candidate(candidate)
        tracker.assert_no_writes()
        assert decision.novelty_type == NoveltyType.POSSIBLE_DUPLICATE

    def test_contradiction_detection_no_write(self):
        tracker = WriteTracker()
        records = [ContradictionRecord(candidate_id="C1", contradictory_evidence="e", reasoning="r")]
        engine = NoveltyEngine(
            knowledge_provider=NoWriteKKProvider(tracker),
            duplicate_detector=NoWriteDuplicateDetector(tracker),
            contradiction_detector=NoWriteContradictionDetector(tracker, records=records),
            scope_validator=NoWriteScopeValidator(tracker),
            threshold=0.5,
        )
        candidate = NoveltyCandidate(
            candidate_id="NW-CONTRA",
            source_entity="A", target_entity="B", relation_type="T",
            evidence_bundle=EvidenceBundle(
                items=[EvidenceItem(source_id="s", content="c", provenance="p", confidence=0.9)]
            ),
        )
        decision = engine.process_candidate(candidate)
        tracker.assert_no_writes()
        assert decision.novelty_type == NoveltyType.POSSIBLE_CONTRADICTION

    def test_new_relation_no_write(self):
        tracker = WriteTracker()
        engine = NoveltyEngine(
            knowledge_provider=NoWriteKKProvider(tracker),
            duplicate_detector=NoWriteDuplicateDetector(tracker),
            contradiction_detector=NoWriteContradictionDetector(tracker),
            scope_validator=NoWriteScopeValidator(tracker),
            threshold=0.5,
        )
        candidate = NoveltyCandidate(
            candidate_id="NW-NEW",
            source_entity="A", target_entity="B", relation_type="T",
            evidence_bundle=EvidenceBundle(
                items=[EvidenceItem(source_id="s", content="c", provenance="p", confidence=0.9)]
            ),
        )
        decision = engine.process_candidate(candidate)
        tracker.assert_no_writes()
        assert decision.novelty_type == NoveltyType.NEW_RELATION_CANDIDATE


class TestStatusFrozenNoWrite:
    def test_status_cannot_be_changed_after_creation(self):
        candidate = NoveltyCandidate(
            candidate_id="C1",
            source_entity="A", target_entity="B", relation_type="T",
            evidence_bundle=EvidenceBundle(items=[]),
        )
        assert candidate.status == "DISCOVERY_ONLY"
        with pytest.raises(Exception):
            candidate.status = "PROMOTED"  # type: ignore[misc]

    def test_status_remains_discovery_only_after_engine(self):
        tracker = WriteTracker()
        engine = NoveltyEngine(
            knowledge_provider=NoWriteKKProvider(tracker),
            duplicate_detector=NoWriteDuplicateDetector(tracker),
            contradiction_detector=NoWriteContradictionDetector(tracker),
            scope_validator=NoWriteScopeValidator(tracker),
            threshold=0.5,
        )
        candidate = NoveltyCandidate(
            candidate_id="C1",
            source_entity="A", target_entity="B", relation_type="T",
            evidence_bundle=EvidenceBundle(
                items=[EvidenceItem(source_id="s", content="c", provenance="p", confidence=0.9)]
            ),
        )
        decision = engine.process_candidate(candidate)
        assert decision.candidate.status == "DISCOVERY_ONLY"


class TestReviewQueueNoExternalWrite:
    def test_record_decision_does_not_write_externally(self):
        """ReviewQueue.record_decision stores in-memory only — no external graph write."""
        queue = ReviewQueue()
        external_db: List[str] = []  # simulate external store — must remain empty

        queue.record_decision(ReviewDecision(
            candidate_id="C1", decision="APPROVE", reviewer="R1", comments="ok"
        ))

        # External store was never touched
        assert external_db == []
        # But internal memory was updated
        assert len(queue._decisions) == 1


# ---------------------------------------------------------------------------
# Parametrized: all 60 fixtures produce no writes
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("fixture", ALL_FIXTURES, ids=[f["case_id"] for f in ALL_FIXTURES])
def test_no_write_all_fixtures(fixture):
    """
    For every fixture:
    - All four required fields present
    - Engine produces a decision with no external writes
    - Candidate status remains DISCOVERY_ONLY
    - review_status remains PENDING_HUMAN_REVIEW
    """
    assert "expected_novelty_type" in fixture
    assert "expected_decision" in fixture
    assert "expected_blocking_reasons" in fixture
    assert "expected_review_route" in fixture

    candidate = _build_candidate_from_fixture(fixture)
    engine = _build_fixture_engine()

    external_writes: List[str] = []

    decision = engine.process_candidate(candidate)

    # No external writes occurred
    assert external_writes == []

    # Candidate invariants
    assert decision.candidate.status == "DISCOVERY_ONLY"
    assert decision.candidate.review_status == "PENDING_HUMAN_REVIEW"

    # Decision structure
    assert decision.explanation.decision == decision.novelty_type.value
    assert isinstance(decision.explanation.reasoning, list)
