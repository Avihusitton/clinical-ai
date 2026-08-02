"""
test_gate_c_models.py
---------------------
Tests for Gate C Pydantic models and their invariants.
Also validates that every fixture in novelty_cases.jsonl has the four
required fields: expected_novelty_type, expected_decision,
expected_blocking_reasons, expected_review_route.
"""
import json
import pytest
from pathlib import Path

from gate_c.models import (
    NoveltyCandidate,
    NoveltyType,
    KnownKnowledgeCheck,
    EvidenceBundle,
    EvidenceItem,
    ContradictionRecord,
    NoveltyScoreComponents,
    NoveltyDecision,
    ReviewDecision,
    NoveltyExplanation,
)

# ---------------------------------------------------------------------------
# Fixture loader (used by several test files – defined centrally here)
# ---------------------------------------------------------------------------
FIXTURE_PATH = Path("tests/fixtures/gate_c/novelty_cases.jsonl")


def load_novelty_fixtures():
    """Load all 60 Gate C novelty fixtures from disk."""
    fixtures = []
    with open(FIXTURE_PATH, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                fixtures.append(json.loads(line))
    return fixtures


ALL_FIXTURES = load_novelty_fixtures()


# ---------------------------------------------------------------------------
# Model unit tests
# ---------------------------------------------------------------------------

class TestEvidenceItem:
    def test_fields_stored_correctly(self):
        item = EvidenceItem(
            source_id="src-1",
            content="Drug X treats Condition Y",
            provenance="PubMed:12345",
            confidence=0.95,
        )
        assert item.source_id == "src-1"
        assert item.content == "Drug X treats Condition Y"
        assert item.provenance == "PubMed:12345"
        assert item.confidence == 0.95

    def test_zero_confidence_allowed(self):
        item = EvidenceItem(source_id="s", content="c", provenance="p", confidence=0.0)
        assert item.confidence == 0.0

    def test_max_confidence_allowed(self):
        item = EvidenceItem(source_id="s", content="c", provenance="p", confidence=1.0)
        assert item.confidence == 1.0


class TestEvidenceBundle:
    def test_has_provenance_all_present(self):
        bundle = EvidenceBundle(
            items=[
                EvidenceItem(source_id="1", content="t", provenance="p1", confidence=0.9),
                EvidenceItem(source_id="2", content="t", provenance="p2", confidence=0.8),
            ]
        )
        assert bundle.has_provenance is True

    def test_has_provenance_one_missing(self):
        bundle = EvidenceBundle(
            items=[
                EvidenceItem(source_id="1", content="t", provenance="p1", confidence=0.9),
                EvidenceItem(source_id="2", content="t", provenance="", confidence=0.8),
            ]
        )
        assert bundle.has_provenance is False

    def test_has_provenance_empty_items_fails_closed(self):
        bundle = EvidenceBundle(items=[])
        assert bundle.has_provenance is False

    def test_phi_default_false(self):
        bundle = EvidenceBundle(items=[])
        assert bundle.contains_phi is False

    def test_phi_can_be_set_true(self):
        bundle = EvidenceBundle(items=[], contains_phi=True)
        assert bundle.contains_phi is True


class TestNoveltyCandidate:
    def test_default_status_is_discovery_only(self):
        candidate = NoveltyCandidate(
            candidate_id="C1",
            source_entity="A",
            target_entity="B",
            relation_type="TREATS",
            evidence_bundle=EvidenceBundle(items=[]),
        )
        assert candidate.status == "DISCOVERY_ONLY"

    def test_default_review_status_pending_human_review(self):
        candidate = NoveltyCandidate(
            candidate_id="C1",
            source_entity="A",
            target_entity="B",
            relation_type="TREATS",
            evidence_bundle=EvidenceBundle(items=[]),
        )
        assert candidate.review_status == "PENDING_HUMAN_REVIEW"

    def test_default_metadata_empty(self):
        candidate = NoveltyCandidate(
            candidate_id="C1",
            source_entity="A",
            target_entity="B",
            relation_type="TREATS",
            evidence_bundle=EvidenceBundle(items=[]),
        )
        assert candidate.metadata == {}

    def test_status_field_is_frozen(self):
        """status is declared frozen=True — cannot be mutated after creation."""
        candidate = NoveltyCandidate(
            candidate_id="C1",
            source_entity="A",
            target_entity="B",
            relation_type="TREATS",
            evidence_bundle=EvidenceBundle(items=[]),
        )
        with pytest.raises(Exception):
            candidate.status = "PROMOTED"  # type: ignore[misc]

    def test_metadata_accepts_arbitrary_dict(self):
        candidate = NoveltyCandidate(
            candidate_id="C1",
            source_entity="A",
            target_entity="B",
            relation_type="TREATS",
            evidence_bundle=EvidenceBundle(items=[]),
            metadata={"key": "value", "num": 42},
        )
        assert candidate.metadata["key"] == "value"
        assert candidate.metadata["num"] == 42


class TestKnownKnowledgeCheck:
    def test_known_true(self):
        check = KnownKnowledgeCheck(is_known=True, existing_reference="Ref1", similarity_score=0.99)
        assert check.is_known is True
        assert check.existing_reference == "Ref1"
        assert check.similarity_score == 0.99

    def test_known_false_no_reference(self):
        check = KnownKnowledgeCheck(is_known=False, similarity_score=0.1)
        assert check.is_known is False
        assert check.existing_reference is None


class TestContradictionRecord:
    def test_fields(self):
        rec = ContradictionRecord(
            candidate_id="C1",
            contradictory_evidence="Source B says otherwise",
            reasoning="Conflict with established guideline",
        )
        assert rec.candidate_id == "C1"
        assert "otherwise" in rec.contradictory_evidence
        assert "guideline" in rec.reasoning


class TestNoveltyScoreComponents:
    def test_fields(self):
        sc = NoveltyScoreComponents(evidence_score=0.8, uniqueness_score=0.7, confidence_score=0.9)
        assert sc.evidence_score == 0.8
        assert sc.uniqueness_score == 0.7
        assert sc.confidence_score == 0.9


class TestReviewDecision:
    def test_fields(self):
        rd = ReviewDecision(candidate_id="C1", decision="APPROVE", reviewer="Dr. Smith", comments="Looks valid")
        assert rd.candidate_id == "C1"
        assert rd.decision == "APPROVE"
        assert rd.reviewer == "Dr. Smith"
        assert rd.comments == "Looks valid"


class TestNoveltyExplanation:
    def test_fields(self):
        exp = NoveltyExplanation(
            candidate_id="C1",
            decision="NEW_RELATION_CANDIDATE",
            reasoning=["reason1", "reason2"],
        )
        assert exp.candidate_id == "C1"
        assert exp.decision == "NEW_RELATION_CANDIDATE"
        assert exp.reasoning == ["reason1", "reason2"]


class TestNoveltyDecision:
    def test_decision_links_explanation_to_candidate(self):
        bundle = EvidenceBundle(items=[])
        candidate = NoveltyCandidate(
            candidate_id="C1",
            source_entity="A",
            target_entity="B",
            relation_type="TREATS",
            evidence_bundle=bundle,
        )
        explanation = NoveltyExplanation(
            candidate_id="C1",
            decision="KNOWN_KNOWLEDGE",
            reasoning=["matches known entry"],
        )
        decision = NoveltyDecision(
            candidate=candidate,
            novelty_type=NoveltyType.KNOWN_KNOWLEDGE,
            explanation=explanation,
        )
        assert decision.novelty_type == NoveltyType.KNOWN_KNOWLEDGE
        assert decision.explanation.decision == "KNOWN_KNOWLEDGE"
        assert decision.candidate.candidate_id == "C1"


class TestNoveltyTypeEnum:
    def test_all_required_members_exist(self):
        required = {
            "NEW_RELATION_CANDIDATE",
            "MISSING_OFFICIAL_ENTRY",
            "MISSING_ALIAS",
            "POSSIBLE_CONTRADICTION",
            "POSSIBLE_DUPLICATE",
            "INSUFFICIENT_EVIDENCE",
            "KNOWN_KNOWLEDGE",
            "OUT_OF_SCOPE",
        }
        actual = {member.value for member in NoveltyType}
        assert required.issubset(actual)


# ---------------------------------------------------------------------------
# Fixture integrity checks: all 60 cases must have the 4 required fields
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("fixture", ALL_FIXTURES, ids=[f["case_id"] for f in ALL_FIXTURES])
def test_fixture_has_expected_novelty_type(fixture):
    assert "expected_novelty_type" in fixture, (
        f"Fixture {fixture.get('case_id')} is missing 'expected_novelty_type'"
    )
    assert isinstance(fixture["expected_novelty_type"], str)
    assert fixture["expected_novelty_type"] != ""


@pytest.mark.parametrize("fixture", ALL_FIXTURES, ids=[f["case_id"] for f in ALL_FIXTURES])
def test_fixture_has_expected_decision(fixture):
    assert "expected_decision" in fixture, (
        f"Fixture {fixture.get('case_id')} is missing 'expected_decision'"
    )
    assert isinstance(fixture["expected_decision"], str)
    assert fixture["expected_decision"] != ""


@pytest.mark.parametrize("fixture", ALL_FIXTURES, ids=[f["case_id"] for f in ALL_FIXTURES])
def test_fixture_has_expected_blocking_reasons(fixture):
    assert "expected_blocking_reasons" in fixture, (
        f"Fixture {fixture.get('case_id')} is missing 'expected_blocking_reasons'"
    )
    assert isinstance(fixture["expected_blocking_reasons"], list)


@pytest.mark.parametrize("fixture", ALL_FIXTURES, ids=[f["case_id"] for f in ALL_FIXTURES])
def test_fixture_has_expected_review_route(fixture):
    assert "expected_review_route" in fixture, (
        f"Fixture {fixture.get('case_id')} is missing 'expected_review_route'"
    )
    assert isinstance(fixture["expected_review_route"], str)
    assert fixture["expected_review_route"] != ""


def test_fixture_count_is_60():
    assert len(ALL_FIXTURES) == 60, (
        f"Expected 60 fixtures, found {len(ALL_FIXTURES)}"
    )
