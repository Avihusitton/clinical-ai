"""
test_gate_c_explainability.py
------------------------------
Tests for ExplainabilityEngine:
- Returns a NoveltyDecision with a populated NoveltyExplanation.
- Decision field mirrors the NoveltyType value.
- Reasoning list is non-empty and serialisable.
- All 60 fixtures are exercised via the engine to confirm explanation structure.
"""
import json
import pytest
from pathlib import Path
from typing import List

from gate_c.models import (
    NoveltyCandidate,
    NoveltyType,
    EvidenceBundle,
    EvidenceItem,
    KnownKnowledgeCheck,
    ContradictionRecord,
)
from gate_c.explainability import ExplainabilityEngine
from gate_c.novelty_engine import (
    NoveltyEngine,
    DuplicateDetector,
    ContradictionDetector,
    ScopeValidator,
)
from gate_c.known_knowledge import KnownKnowledgeProvider

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
# Minimal mocks for engine construction
# ---------------------------------------------------------------------------

class _KKProvider(KnownKnowledgeProvider):
    def __init__(self, is_known: bool):
        self._is_known = is_known
    def check_candidate(self, candidate: NoveltyCandidate) -> KnownKnowledgeCheck:
        return KnownKnowledgeCheck(is_known=self._is_known, similarity_score=1.0 if self._is_known else 0.0)


class _DupDetector(DuplicateDetector):
    def __init__(self, is_dup: bool):
        self._is_dup = is_dup
    def is_duplicate(self, candidate: NoveltyCandidate) -> bool:
        return self._is_dup


class _ContraDetector(ContradictionDetector):
    def __init__(self, records: List[ContradictionRecord] = None):
        self._records = records or []
    def check_contradictions(self, candidate: NoveltyCandidate) -> List[ContradictionRecord]:
        return self._records


class _ScopeValidator(ScopeValidator):
    def __init__(self, in_scope: bool):
        self._in_scope = in_scope
    def is_in_scope(self, candidate: NoveltyCandidate) -> bool:
        return self._in_scope


class FixtureKKProvider(KnownKnowledgeProvider):
    def check_candidate(self, candidate: NoveltyCandidate) -> KnownKnowledgeCheck:
        f = candidate.metadata["fixture"]
        is_known = f["expected_novelty_type"] in ("EXACT_MATCH", "SEMANTIC_MATCH")
        return KnownKnowledgeCheck(is_known=is_known, similarity_score=1.0 if is_known else 0.0,
                                   existing_reference="ref" if is_known else None)


class FixtureDupDetector(DuplicateDetector):
    def is_duplicate(self, candidate: NoveltyCandidate) -> bool:
        return candidate.metadata["fixture"]["expected_novelty_type"] == "DUPLICATE"


class FixtureContraDetector(ContradictionDetector):
    def check_contradictions(self, candidate: NoveltyCandidate) -> List[ContradictionRecord]:
        f = candidate.metadata["fixture"]
        if f["expected_novelty_type"] == "CONTRADICTION" or f.get("contradictory_evidence"):
            return [ContradictionRecord(candidate_id=candidate.candidate_id,
                                        contradictory_evidence="c", reasoning="r")]
        return []


class FixtureScopeValidator(ScopeValidator):
    def is_in_scope(self, candidate: NoveltyCandidate) -> bool:
        f = candidate.metadata["fixture"]
        reasons = f["expected_blocking_reasons"]
        if ("OUTSIDE_REGISTRY" in reasons or "AUTONOMOUS_ACTION_NOT_PERMITTED" in reasons
                or f["expected_novelty_type"] == "EXERCISE_BRIDGE"):
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
    src = fixture.get("matched_official_entries", ["A"])[0] if fixture.get("matched_official_entries") else "A"
    tgt = fixture.get("matched_official_entries", ["A", "B"])[-1] if fixture.get("matched_official_entries") else "B"
    return NoveltyCandidate(
        candidate_id=fixture["case_id"],
        source_entity=src,
        target_entity=tgt,
        relation_type="RELATES_TO",
        evidence_bundle=bundle,
        metadata={"fixture": fixture},
    )


def _build_engine() -> NoveltyEngine:
    return NoveltyEngine(
        knowledge_provider=FixtureKKProvider(),
        duplicate_detector=FixtureDupDetector(),
        contradiction_detector=FixtureContraDetector(),
        scope_validator=FixtureScopeValidator(),
        threshold=0.5,
    )


def _simple_engine(is_known=False, is_dup=False, contradictions=None,
                   in_scope=True, threshold=0.5) -> NoveltyEngine:
    return NoveltyEngine(
        knowledge_provider=_KKProvider(is_known),
        duplicate_detector=_DupDetector(is_dup),
        contradiction_detector=_ContraDetector(contradictions),
        scope_validator=_ScopeValidator(in_scope),
        threshold=threshold,
    )


def _simple_candidate(candidate_id: str = "C1", provenance: str = "p",
                       phi: bool = False, confidence: float = 0.9) -> NoveltyCandidate:
    return NoveltyCandidate(
        candidate_id=candidate_id,
        source_entity="A",
        target_entity="B",
        relation_type="T",
        evidence_bundle=EvidenceBundle(
            items=[EvidenceItem(source_id="s", content="c", provenance=provenance, confidence=confidence)],
            contains_phi=phi,
        ),
    )


# ---------------------------------------------------------------------------
# Unit tests for ExplainabilityEngine directly
# ---------------------------------------------------------------------------

class TestExplainabilityEngine:
    def test_explain_returns_novelty_decision(self):
        engine = ExplainabilityEngine()
        candidate = _simple_candidate()
        decision = engine.explain(candidate, NoveltyType.KNOWN_KNOWLEDGE, ["matched known entry"])
        assert decision is not None

    def test_explain_novelty_type_set_correctly(self):
        engine = ExplainabilityEngine()
        candidate = _simple_candidate()
        for ntype in NoveltyType:
            decision = engine.explain(candidate, ntype, ["reason"])
            assert decision.novelty_type == ntype

    def test_explain_decision_string_matches_novelty_type_value(self):
        engine = ExplainabilityEngine()
        candidate = _simple_candidate()
        decision = engine.explain(candidate, NoveltyType.OUT_OF_SCOPE, ["PHI detected"])
        assert decision.explanation.decision == "OUT_OF_SCOPE"
        assert decision.explanation.decision == decision.novelty_type.value

    def test_explain_reasoning_list_preserved(self):
        engine = ExplainabilityEngine()
        candidate = _simple_candidate()
        reasons = ["reason A", "reason B", "reason C"]
        decision = engine.explain(candidate, NoveltyType.INSUFFICIENT_EVIDENCE, reasons)
        assert decision.explanation.reasoning == reasons

    def test_explain_candidate_id_propagated(self):
        engine = ExplainabilityEngine()
        candidate = _simple_candidate(candidate_id="TEST-99")
        decision = engine.explain(candidate, NoveltyType.NEW_RELATION_CANDIDATE, ["ok"])
        assert decision.explanation.candidate_id == "TEST-99"

    def test_explain_candidate_linked_on_decision(self):
        engine = ExplainabilityEngine()
        candidate = _simple_candidate()
        decision = engine.explain(candidate, NoveltyType.POSSIBLE_DUPLICATE, ["dup"])
        assert decision.candidate is candidate

    def test_reasoning_list_can_be_json_serialised(self):
        engine = ExplainabilityEngine()
        candidate = _simple_candidate()
        decision = engine.explain(
            candidate, NoveltyType.POSSIBLE_CONTRADICTION,
            ["Contradiction found: 2 records.", "Contradiction: conflicts with guideline"]
        )
        serialised = json.dumps(decision.explanation.reasoning)
        reloaded = json.loads(serialised)
        assert reloaded == decision.explanation.reasoning

    def test_empty_reasoning_list_accepted(self):
        engine = ExplainabilityEngine()
        candidate = _simple_candidate()
        decision = engine.explain(candidate, NoveltyType.KNOWN_KNOWLEDGE, [])
        assert decision.explanation.reasoning == []


# ---------------------------------------------------------------------------
# Integration: engine produces proper explanation for each decision type
# ---------------------------------------------------------------------------

class TestEngineExplanationIntegration:
    def test_phi_explanation_identifies_phi(self):
        engine = _simple_engine()
        cand = _simple_candidate(phi=True)
        decision = engine.process_candidate(cand)
        assert "Identifiable patient information" in " ".join(decision.explanation.reasoning)

    def test_provenance_explanation_identifies_missing_provenance(self):
        engine = _simple_engine()
        cand = _simple_candidate(provenance="")
        decision = engine.process_candidate(cand)
        assert "Missing provenance" in " ".join(decision.explanation.reasoning)

    def test_scope_explanation_identifies_out_of_scope(self):
        engine = _simple_engine(in_scope=False)
        cand = _simple_candidate()
        decision = engine.process_candidate(cand)
        assert "out of scope" in " ".join(decision.explanation.reasoning).lower()

    def test_known_knowledge_explanation_includes_reference(self):
        engine = _simple_engine(is_known=True)
        cand = _simple_candidate()
        decision = engine.process_candidate(cand)
        assert "known knowledge" in " ".join(decision.explanation.reasoning).lower()

    def test_duplicate_explanation_identifies_duplicate(self):
        engine = _simple_engine(is_dup=True)
        cand = _simple_candidate()
        decision = engine.process_candidate(cand)
        assert "duplicate" in " ".join(decision.explanation.reasoning).lower()

    def test_contradiction_explanation_counts_records(self):
        records = [
            ContradictionRecord(candidate_id="C1", contradictory_evidence="e", reasoning="r1"),
            ContradictionRecord(candidate_id="C1", contradictory_evidence="e", reasoning="r2"),
        ]
        engine = _simple_engine(contradictions=records)
        cand = _simple_candidate()
        decision = engine.process_candidate(cand)
        reasoning_text = " ".join(decision.explanation.reasoning)
        assert "Contradictory evidence found" in reasoning_text
        assert "2" in reasoning_text

    def test_insufficient_evidence_explanation_mentions_threshold(self):
        engine = _simple_engine(threshold=0.95)
        cand = _simple_candidate(confidence=0.3)
        decision = engine.process_candidate(cand)
        assert "threshold" in " ".join(decision.explanation.reasoning).lower()

    def test_new_relation_explanation_confirms_checks_passed(self):
        engine = _simple_engine()
        cand = _simple_candidate()
        decision = engine.process_candidate(cand)
        assert decision.novelty_type == NoveltyType.NEW_RELATION_CANDIDATE
        reasoning_text = " ".join(decision.explanation.reasoning)
        assert "passed" in reasoning_text.lower() or "deterministic" in reasoning_text.lower()


# ---------------------------------------------------------------------------
# All 60 fixtures — assert explanation structure and all 4 required fields
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("fixture", ALL_FIXTURES, ids=[f["case_id"] for f in ALL_FIXTURES])
def test_explainability_fixture_all_four_fields(fixture):
    """Every fixture must carry the four required metadata fields."""
    assert "expected_novelty_type" in fixture
    assert "expected_decision" in fixture
    assert "expected_blocking_reasons" in fixture
    assert isinstance(fixture["expected_blocking_reasons"], list)
    assert "expected_review_route" in fixture


@pytest.mark.parametrize("fixture", ALL_FIXTURES, ids=[f["case_id"] for f in ALL_FIXTURES])
def test_explainability_engine_returns_explanation_for_fixture(fixture):
    """
    After processing a fixture through the engine, the explanation must:
    - have decision == novelty_type.value
    - have a non-None reasoning list
    - have candidate_id matching the fixture case_id
    """
    candidate = _build_candidate_from_fixture(fixture)
    engine = _build_engine()
    decision = engine.process_candidate(candidate)

    assert decision.explanation is not None
    assert decision.explanation.candidate_id == fixture["case_id"]
    assert decision.explanation.decision == decision.novelty_type.value
    assert isinstance(decision.explanation.reasoning, list)
