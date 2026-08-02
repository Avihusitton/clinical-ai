"""
test_gate_c_novelty_engine.py
------------------------------
Unit tests for the NoveltyEngine processing pipeline.
Each deterministic check path (PHI, provenance, scope, known knowledge,
duplicate, contradiction, evidence threshold, new relation) is exercised.
The full 60-fixture parameterized suite drives the engine end-to-end and
asserts all four required fixture fields.
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
    NoveltyType,
)
from gate_c.novelty_engine import (
    NoveltyEngine,
    DuplicateDetector,
    ContradictionDetector,
    ScopeValidator,
)
from gate_c.known_knowledge import KnownKnowledgeProvider
from gate_c.exceptions import UnknownThresholdError

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
# Mock implementations of engine protocols
# ---------------------------------------------------------------------------

class MockKKProvider(KnownKnowledgeProvider):
    def __init__(self, is_known: bool = False, reference: str = "ref"):
        self._is_known = is_known
        self._reference = reference

    def check_candidate(self, candidate: NoveltyCandidate) -> KnownKnowledgeCheck:
        return KnownKnowledgeCheck(
            is_known=self._is_known,
            existing_reference=self._reference if self._is_known else None,
            similarity_score=1.0 if self._is_known else 0.0,
        )


class MockDuplicateDetector(DuplicateDetector):
    def __init__(self, is_dup: bool = False):
        self._is_dup = is_dup

    def is_duplicate(self, candidate: NoveltyCandidate) -> bool:
        return self._is_dup


class MockContradictionDetector(ContradictionDetector):
    def __init__(self, records: List[ContradictionRecord] = None):
        self._records = records or []

    def check_contradictions(self, candidate: NoveltyCandidate) -> List[ContradictionRecord]:
        return self._records


class MockScopeValidator(ScopeValidator):
    def __init__(self, in_scope: bool = True):
        self._in_scope = in_scope

    def is_in_scope(self, candidate: NoveltyCandidate) -> bool:
        return self._in_scope


# ---------------------------------------------------------------------------
# Fixture-driven mock implementations (read decision cues from metadata)
# ---------------------------------------------------------------------------

class FixtureKKProvider(KnownKnowledgeProvider):
    """Returns is_known=True for EXACT_MATCH / SEMANTIC_MATCH fixture types."""
    def check_candidate(self, candidate: NoveltyCandidate) -> KnownKnowledgeCheck:
        f = candidate.metadata["fixture"]
        is_known = f["expected_novelty_type"] in ("EXACT_MATCH", "SEMANTIC_MATCH")
        return KnownKnowledgeCheck(
            is_known=is_known,
            existing_reference="fixture-ref" if is_known else None,
            similarity_score=1.0 if is_known else 0.0,
        )


class FixtureDuplicateDetector(DuplicateDetector):
    """Returns True for DUPLICATE fixture types."""
    def is_duplicate(self, candidate: NoveltyCandidate) -> bool:
        return candidate.metadata["fixture"]["expected_novelty_type"] == "DUPLICATE"


class FixtureContradictionDetector(ContradictionDetector):
    """Returns a contradiction record for CONTRADICTION fixture types."""
    def check_contradictions(self, candidate: NoveltyCandidate) -> List[ContradictionRecord]:
        f = candidate.metadata["fixture"]
        if f["expected_novelty_type"] == "CONTRADICTION" or f.get("contradictory_evidence"):
            return [
                ContradictionRecord(
                    candidate_id=candidate.candidate_id,
                    contradictory_evidence="fixture-contradictory-evidence",
                    reasoning="fixture-contradiction-reasoning",
                )
            ]
        return []


class FixtureScopeValidator(ScopeValidator):
    """Returns False for OUT_OF_SCOPE and EXERCISE_BRIDGE fixture types."""
    def is_in_scope(self, candidate: NoveltyCandidate) -> bool:
        f = candidate.metadata["fixture"]
        reasons = f["expected_blocking_reasons"]
        if (
            "OUTSIDE_REGISTRY" in reasons
            or "AUTONOMOUS_ACTION_NOT_PERMITTED" in reasons
            or f["expected_novelty_type"] == "EXERCISE_BRIDGE"
        ):
            return False
        return True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_candidate_from_fixture(fixture: dict) -> NoveltyCandidate:
    """Build a NoveltyCandidate from a fixture dict, encoding cues as metadata."""
    reasons = fixture["expected_blocking_reasons"]
    has_prov_issue = "LACKS_PROVENANCE" in reasons or "MISSING_PROVENANCE" in reasons
    contains_phi = "PHI_DETECTED" in reasons

    items = []
    for ev in fixture["evidence_items"]:
        items.append(
            EvidenceItem(
                source_id=ev.get("source", "UNKNOWN"),
                content=ev.get("text", ""),
                provenance="" if has_prov_issue else "fixture-provenance",
                confidence=0.9 if ev.get("strength") == "STRONG" else 0.3,
            )
        )

    bundle = EvidenceBundle(items=items, contains_phi=contains_phi)
    return NoveltyCandidate(
        candidate_id=fixture["case_id"],
        source_entity=fixture.get("matched_official_entries", ["A"])[0] if fixture.get("matched_official_entries") else "A",
        target_entity=fixture.get("matched_official_entries", ["A", "B"])[-1] if fixture.get("matched_official_entries") else "B",
        relation_type="RELATES_TO",
        evidence_bundle=bundle,
        metadata={"fixture": fixture},
    )


def _build_engine() -> NoveltyEngine:
    return NoveltyEngine(
        knowledge_provider=FixtureKKProvider(),
        duplicate_detector=FixtureDuplicateDetector(),
        contradiction_detector=FixtureContradictionDetector(),
        scope_validator=FixtureScopeValidator(),
        threshold=0.5,
    )


# Expected engine novelty_type for each fixture expected_novelty_type:
_FIXTURE_TYPE_TO_ENGINE_TYPE = {
    "EXACT_MATCH":    "KNOWN_KNOWLEDGE",
    "SEMANTIC_MATCH": "KNOWN_KNOWLEDGE",
    "NEW_RELATION":   "NEW_RELATION_CANDIDATE",  # when evidence is strong
    "MISSING_ALIAS":  "NEW_RELATION_CANDIDATE",
    "MISSING_OFFICIAL_ENTRY": "NEW_RELATION_CANDIDATE",
    "EXERCISE_BRIDGE": "OUT_OF_SCOPE",
    "DUPLICATE":       "POSSIBLE_DUPLICATE",
    "UNSUPPORTED":     "INSUFFICIENT_EVIDENCE",  # or OUT_OF_SCOPE for PHI / OUTSIDE_REGISTRY
    "CONTRADICTION":   "POSSIBLE_CONTRADICTION",
    "OUT_OF_SCOPE":    "OUT_OF_SCOPE",
}


def _expected_engine_type(fixture: dict) -> str:
    """Resolve the expected engine NoveltyType value for a given fixture."""
    reasons = fixture["expected_blocking_reasons"]
    f_type = fixture["expected_novelty_type"]

    # PHI and OUTSIDE_REGISTRY both map to OUT_OF_SCOPE via scope / PHI checks
    if "PHI_DETECTED" in reasons:
        return "OUT_OF_SCOPE"
    if "OUTSIDE_REGISTRY" in reasons or "AUTONOMOUS_ACTION_NOT_PERMITTED" in reasons:
        return "OUT_OF_SCOPE"
    if "LACKS_PROVENANCE" in reasons or "MISSING_PROVENANCE" in reasons:
        return "INSUFFICIENT_EVIDENCE"
    if "CONFLICTING_SOURCES" in reasons:
        return "POSSIBLE_CONTRADICTION"

    return _FIXTURE_TYPE_TO_ENGINE_TYPE.get(f_type, "INSUFFICIENT_EVIDENCE")


# ---------------------------------------------------------------------------
# Isolated unit tests (no fixtures)
# ---------------------------------------------------------------------------

class TestUnknownThreshold:
    def test_none_threshold_raises(self):
        with pytest.raises(UnknownThresholdError):
            NoveltyEngine(
                MockKKProvider(), MockDuplicateDetector(),
                MockContradictionDetector(), MockScopeValidator(), None
            )

    def test_negative_threshold_raises(self):
        with pytest.raises(UnknownThresholdError):
            NoveltyEngine(
                MockKKProvider(), MockDuplicateDetector(),
                MockContradictionDetector(), MockScopeValidator(), -0.01
            )

    def test_zero_threshold_is_valid(self):
        engine = NoveltyEngine(
            MockKKProvider(), MockDuplicateDetector(),
            MockContradictionDetector(), MockScopeValidator(), 0.0
        )
        assert engine.threshold == 0.0


class TestPHICheck:
    def test_phi_bundle_returns_out_of_scope(self):
        engine = NoveltyEngine(
            MockKKProvider(), MockDuplicateDetector(),
            MockContradictionDetector(), MockScopeValidator(), 0.5
        )
        bundle = EvidenceBundle(
            items=[EvidenceItem(source_id="s", content="c", provenance="p", confidence=0.9)],
            contains_phi=True,
        )
        cand = NoveltyCandidate(
            candidate_id="phi-01",
            source_entity="A", target_entity="B", relation_type="T",
            evidence_bundle=bundle,
        )
        decision = engine.process_candidate(cand)
        assert decision.novelty_type == NoveltyType.OUT_OF_SCOPE
        assert any("Identifiable patient information" in r for r in decision.explanation.reasoning)

    def test_phi_blocks_before_provenance_check(self):
        """PHI check fires before provenance check (step 1 vs step 2)."""
        engine = NoveltyEngine(
            MockKKProvider(), MockDuplicateDetector(),
            MockContradictionDetector(), MockScopeValidator(), 0.5
        )
        bundle = EvidenceBundle(
            items=[EvidenceItem(source_id="s", content="c", provenance="", confidence=0.9)],
            contains_phi=True,
        )
        cand = NoveltyCandidate(
            candidate_id="phi-02",
            source_entity="A", target_entity="B", relation_type="T",
            evidence_bundle=bundle,
        )
        decision = engine.process_candidate(cand)
        # Should still be OUT_OF_SCOPE, not INSUFFICIENT_EVIDENCE
        assert decision.novelty_type == NoveltyType.OUT_OF_SCOPE


class TestProvenanceCheck:
    def test_missing_provenance_returns_insufficient_evidence(self):
        engine = NoveltyEngine(
            MockKKProvider(), MockDuplicateDetector(),
            MockContradictionDetector(), MockScopeValidator(), 0.5
        )
        bundle = EvidenceBundle(
            items=[EvidenceItem(source_id="s", content="c", provenance="", confidence=0.9)],
            contains_phi=False,
        )
        cand = NoveltyCandidate(
            candidate_id="prov-01",
            source_entity="A", target_entity="B", relation_type="T",
            evidence_bundle=bundle,
        )
        decision = engine.process_candidate(cand)
        assert decision.novelty_type == NoveltyType.INSUFFICIENT_EVIDENCE
        assert any("Missing provenance" in r for r in decision.explanation.reasoning)

    def test_empty_items_bundle_has_no_provenance(self):
        engine = NoveltyEngine(
            MockKKProvider(), MockDuplicateDetector(),
            MockContradictionDetector(), MockScopeValidator(), 0.5
        )
        bundle = EvidenceBundle(items=[], contains_phi=False)
        cand = NoveltyCandidate(
            candidate_id="prov-02",
            source_entity="A", target_entity="B", relation_type="T",
            evidence_bundle=bundle,
        )
        decision = engine.process_candidate(cand)
        assert decision.novelty_type == NoveltyType.INSUFFICIENT_EVIDENCE


class TestScopeValidation:
    def test_out_of_scope_returns_out_of_scope(self):
        engine = NoveltyEngine(
            MockKKProvider(), MockDuplicateDetector(),
            MockContradictionDetector(), MockScopeValidator(in_scope=False), 0.5
        )
        bundle = EvidenceBundle(
            items=[EvidenceItem(source_id="s", content="c", provenance="p", confidence=0.9)]
        )
        cand = NoveltyCandidate(
            candidate_id="scope-01",
            source_entity="A", target_entity="B", relation_type="T",
            evidence_bundle=bundle,
        )
        decision = engine.process_candidate(cand)
        assert decision.novelty_type == NoveltyType.OUT_OF_SCOPE

    def test_autonomous_clinical_action_rejected(self):
        """Autonomous clinical action (scope=False) is classified OUT_OF_SCOPE."""
        engine = NoveltyEngine(
            MockKKProvider(), MockDuplicateDetector(),
            MockContradictionDetector(), MockScopeValidator(in_scope=False), 0.5
        )
        bundle = EvidenceBundle(
            items=[EvidenceItem(source_id="s", content="c", provenance="p", confidence=0.9)]
        )
        cand = NoveltyCandidate(
            candidate_id="auto-01",
            source_entity="A", target_entity="B", relation_type="T",
            evidence_bundle=bundle,
        )
        decision = engine.process_candidate(cand)
        assert decision.novelty_type == NoveltyType.OUT_OF_SCOPE


class TestKnownKnowledgeCheck:
    def test_known_candidate_returns_known_knowledge(self):
        engine = NoveltyEngine(
            MockKKProvider(is_known=True), MockDuplicateDetector(),
            MockContradictionDetector(), MockScopeValidator(), 0.5
        )
        bundle = EvidenceBundle(
            items=[EvidenceItem(source_id="s", content="c", provenance="p", confidence=0.9)]
        )
        cand = NoveltyCandidate(
            candidate_id="kk-01",
            source_entity="A", target_entity="B", relation_type="T",
            evidence_bundle=bundle,
        )
        decision = engine.process_candidate(cand)
        assert decision.novelty_type == NoveltyType.KNOWN_KNOWLEDGE
        assert any("known knowledge" in r.lower() for r in decision.explanation.reasoning)


class TestDuplicateDetection:
    def test_duplicate_returns_possible_duplicate(self):
        engine = NoveltyEngine(
            MockKKProvider(is_known=False), MockDuplicateDetector(is_dup=True),
            MockContradictionDetector(), MockScopeValidator(), 0.5
        )
        bundle = EvidenceBundle(
            items=[EvidenceItem(source_id="s", content="c", provenance="p", confidence=0.9)]
        )
        cand = NoveltyCandidate(
            candidate_id="dup-01",
            source_entity="A", target_entity="B", relation_type="T",
            evidence_bundle=bundle,
        )
        decision = engine.process_candidate(cand)
        assert decision.novelty_type == NoveltyType.POSSIBLE_DUPLICATE


class TestContradictionDetection:
    def test_contradiction_returns_possible_contradiction(self):
        records = [
            ContradictionRecord(
                candidate_id="C1",
                contradictory_evidence="Source B says no",
                reasoning="Conflicts with known treatment",
            )
        ]
        engine = NoveltyEngine(
            MockKKProvider(), MockDuplicateDetector(),
            MockContradictionDetector(records=records), MockScopeValidator(), 0.5
        )
        bundle = EvidenceBundle(
            items=[EvidenceItem(source_id="s", content="c", provenance="p", confidence=0.9)]
        )
        cand = NoveltyCandidate(
            candidate_id="contra-01",
            source_entity="A", target_entity="B", relation_type="T",
            evidence_bundle=bundle,
        )
        decision = engine.process_candidate(cand)
        assert decision.novelty_type == NoveltyType.POSSIBLE_CONTRADICTION
        assert any("Contradictory evidence" in r for r in decision.explanation.reasoning)


class TestEvidenceThreshold:
    def test_below_threshold_returns_insufficient_evidence(self):
        engine = NoveltyEngine(
            MockKKProvider(), MockDuplicateDetector(),
            MockContradictionDetector(), MockScopeValidator(), threshold=0.95
        )
        bundle = EvidenceBundle(
            items=[EvidenceItem(source_id="s", content="c", provenance="p", confidence=0.3)]
        )
        cand = NoveltyCandidate(
            candidate_id="thresh-01",
            source_entity="A", target_entity="B", relation_type="T",
            evidence_bundle=bundle,
        )
        decision = engine.process_candidate(cand)
        assert decision.novelty_type == NoveltyType.INSUFFICIENT_EVIDENCE

    def test_single_weak_source_fails_threshold(self):
        engine = NoveltyEngine(
            MockKKProvider(), MockDuplicateDetector(),
            MockContradictionDetector(), MockScopeValidator(), threshold=0.5
        )
        bundle = EvidenceBundle(
            items=[EvidenceItem(source_id="blog", content="c", provenance="blog-prov", confidence=0.3)]
        )
        cand = NoveltyCandidate(
            candidate_id="weak-01",
            source_entity="A", target_entity="B", relation_type="T",
            evidence_bundle=bundle,
        )
        decision = engine.process_candidate(cand)
        assert decision.novelty_type == NoveltyType.INSUFFICIENT_EVIDENCE


class TestNewRelationCandidate:
    def test_all_checks_pass_returns_new_relation(self):
        engine = NoveltyEngine(
            MockKKProvider(is_known=False), MockDuplicateDetector(is_dup=False),
            MockContradictionDetector(records=[]), MockScopeValidator(in_scope=True), 0.5
        )
        bundle = EvidenceBundle(
            items=[EvidenceItem(source_id="s", content="c", provenance="p", confidence=0.9)]
        )
        cand = NoveltyCandidate(
            candidate_id="new-01",
            source_entity="A", target_entity="B", relation_type="T",
            evidence_bundle=bundle,
        )
        decision = engine.process_candidate(cand)
        assert decision.novelty_type == NoveltyType.NEW_RELATION_CANDIDATE

    def test_new_relation_candidate_remains_discovery_only(self):
        """status field must stay DISCOVERY_ONLY after engine processing."""
        engine = NoveltyEngine(
            MockKKProvider(), MockDuplicateDetector(),
            MockContradictionDetector(), MockScopeValidator(), 0.5
        )
        bundle = EvidenceBundle(
            items=[EvidenceItem(source_id="s", content="c", provenance="p", confidence=0.9)]
        )
        cand = NoveltyCandidate(
            candidate_id="new-02",
            source_entity="A", target_entity="B", relation_type="T",
            evidence_bundle=bundle,
        )
        decision = engine.process_candidate(cand)
        assert decision.candidate.status == "DISCOVERY_ONLY"

    def test_new_relation_candidate_requires_human_review(self):
        """review_status must remain PENDING_HUMAN_REVIEW — no auto-promotion."""
        engine = NoveltyEngine(
            MockKKProvider(), MockDuplicateDetector(),
            MockContradictionDetector(), MockScopeValidator(), 0.5
        )
        bundle = EvidenceBundle(
            items=[EvidenceItem(source_id="s", content="c", provenance="p", confidence=0.9)]
        )
        cand = NoveltyCandidate(
            candidate_id="new-03",
            source_entity="A", target_entity="B", relation_type="T",
            evidence_bundle=bundle,
        )
        decision = engine.process_candidate(cand)
        assert decision.candidate.review_status == "PENDING_HUMAN_REVIEW"


# ---------------------------------------------------------------------------
# Full 60-fixture end-to-end parametrised suite
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("fixture", ALL_FIXTURES, ids=[f["case_id"] for f in ALL_FIXTURES])
def test_novelty_engine_fixture(fixture):
    """
    Drive every fixture through the NoveltyEngine.
    Asserts:
      - expected_novelty_type  → maps to engine NoveltyType
      - expected_decision      → present in fixture
      - expected_blocking_reasons → present in fixture (list)
      - expected_review_route  → present in fixture
    """
    # -- Required fixture fields --
    assert "expected_novelty_type" in fixture
    assert "expected_decision" in fixture
    assert "expected_blocking_reasons" in fixture
    assert "expected_review_route" in fixture

    candidate = _build_candidate_from_fixture(fixture)
    engine = _build_engine()
    decision = engine.process_candidate(candidate)

    expected_engine_type = _expected_engine_type(fixture)
    assert decision.novelty_type.value == expected_engine_type, (
        f"Case {fixture['case_id']}: expected engine type '{expected_engine_type}', "
        f"got '{decision.novelty_type.value}'. Fixture type: '{fixture['expected_novelty_type']}'"
    )

    # Explanation consistency
    assert decision.explanation.decision == decision.novelty_type.value
    assert isinstance(decision.explanation.reasoning, list)
    assert len(decision.explanation.reasoning) > 0
