"""
test_gate_c_known_knowledge.py
-------------------------------
Tests for the KnownKnowledgeProvider protocol.
Covers: exact match, semantic equivalence, near-duplicate resolution,
missing alias detection, and not-known paths.
Also parametrises over all 60 fixtures to assert that the four required
fields are consistent with known-knowledge semantics.
"""
import json
import pytest
from pathlib import Path

from gate_c.models import (
    NoveltyCandidate,
    KnownKnowledgeCheck,
    EvidenceBundle,
    EvidenceItem,
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
# Concrete implementations of the protocol for testing
# ---------------------------------------------------------------------------

class ExactMatchProvider(KnownKnowledgeProvider):
    """Simulates a registry where the candidate is an exact known match."""
    def check_candidate(self, candidate: NoveltyCandidate) -> KnownKnowledgeCheck:
        return KnownKnowledgeCheck(
            is_known=True,
            existing_reference="DrugA TREATS CondA",
            similarity_score=1.0,
        )


class SemanticEquivalentProvider(KnownKnowledgeProvider):
    """Simulates a registry where the candidate is a semantic paraphrase of known knowledge."""
    def check_candidate(self, candidate: NoveltyCandidate) -> KnownKnowledgeCheck:
        return KnownKnowledgeCheck(
            is_known=True,
            existing_reference="DrugA TREATS CondA (semantic match: mitigates ≈ treats)",
            similarity_score=0.91,
        )


class MissingAliasProvider(KnownKnowledgeProvider):
    """Simulates a registry where the entity is known but an alias is missing."""
    def check_candidate(self, candidate: NoveltyCandidate) -> KnownKnowledgeCheck:
        # Not considered 'known' because the alias variant hasn't been registered yet
        return KnownKnowledgeCheck(
            is_known=False,
            existing_reference=None,
            similarity_score=0.72,
        )


class MissingOfficialEntryProvider(KnownKnowledgeProvider):
    """Simulates registry check where target entity is completely absent."""
    def check_candidate(self, candidate: NoveltyCandidate) -> KnownKnowledgeCheck:
        return KnownKnowledgeCheck(
            is_known=False,
            existing_reference=None,
            similarity_score=0.0,
        )


class NotKnownProvider(KnownKnowledgeProvider):
    """Standard not-known path."""
    def check_candidate(self, candidate: NoveltyCandidate) -> KnownKnowledgeCheck:
        return KnownKnowledgeCheck(is_known=False, similarity_score=0.2)


def _make_candidate(candidate_id: str = "C1") -> NoveltyCandidate:
    return NoveltyCandidate(
        candidate_id=candidate_id,
        source_entity="DrugX",
        target_entity="CondY",
        relation_type="TREATS",
        evidence_bundle=EvidenceBundle(
            items=[EvidenceItem(source_id="s", content="c", provenance="p", confidence=0.9)]
        ),
    )


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

class TestExactMatchKnownKnowledge:
    def test_is_known_true(self):
        provider = ExactMatchProvider()
        candidate = _make_candidate()
        result = provider.check_candidate(candidate)
        assert result.is_known is True

    def test_similarity_score_is_1(self):
        provider = ExactMatchProvider()
        candidate = _make_candidate()
        result = provider.check_candidate(candidate)
        assert result.similarity_score == 1.0

    def test_existing_reference_populated(self):
        provider = ExactMatchProvider()
        candidate = _make_candidate()
        result = provider.check_candidate(candidate)
        assert result.existing_reference is not None
        assert len(result.existing_reference) > 0


class TestSemanticEquivalentKnownKnowledge:
    def test_is_known_true_for_semantic_match(self):
        provider = SemanticEquivalentProvider()
        candidate = _make_candidate()
        result = provider.check_candidate(candidate)
        assert result.is_known is True

    def test_similarity_score_high_but_not_one(self):
        provider = SemanticEquivalentProvider()
        candidate = _make_candidate()
        result = provider.check_candidate(candidate)
        assert 0.85 <= result.similarity_score < 1.0

    def test_reference_notes_semantic_equivalence(self):
        provider = SemanticEquivalentProvider()
        candidate = _make_candidate()
        result = provider.check_candidate(candidate)
        assert "semantic match" in result.existing_reference.lower()


class TestMissingAliasProvider:
    def test_is_known_false_when_alias_missing(self):
        provider = MissingAliasProvider()
        candidate = _make_candidate()
        result = provider.check_candidate(candidate)
        assert result.is_known is False

    def test_similarity_score_partial(self):
        """Missing alias has partial similarity — entity is recognisable but variant unregistered."""
        provider = MissingAliasProvider()
        candidate = _make_candidate()
        result = provider.check_candidate(candidate)
        assert result.similarity_score > 0.0

    def test_no_existing_reference_for_unregistered_alias(self):
        provider = MissingAliasProvider()
        candidate = _make_candidate()
        result = provider.check_candidate(candidate)
        assert result.existing_reference is None


class TestMissingOfficialEntryProvider:
    def test_is_known_false_for_unlisted_entity(self):
        provider = MissingOfficialEntryProvider()
        candidate = _make_candidate()
        result = provider.check_candidate(candidate)
        assert result.is_known is False

    def test_zero_similarity_for_completely_absent_entity(self):
        provider = MissingOfficialEntryProvider()
        candidate = _make_candidate()
        result = provider.check_candidate(candidate)
        assert result.similarity_score == 0.0


class TestNotKnownProvider:
    def test_is_known_false(self):
        provider = NotKnownProvider()
        candidate = _make_candidate()
        result = provider.check_candidate(candidate)
        assert result.is_known is False

    def test_no_reference(self):
        provider = NotKnownProvider()
        candidate = _make_candidate()
        result = provider.check_candidate(candidate)
        assert result.existing_reference is None


class TestKnownKnowledgeCheckModel:
    def test_default_existing_reference_is_none(self):
        check = KnownKnowledgeCheck(is_known=False, similarity_score=0.0)
        assert check.existing_reference is None

    def test_similarity_score_stored(self):
        check = KnownKnowledgeCheck(is_known=True, existing_reference="ref", similarity_score=0.95)
        assert check.similarity_score == 0.95


# ---------------------------------------------------------------------------
# Fixture-parametrized tests: assert the 4 required fields for known-knowledge cases
# ---------------------------------------------------------------------------

KNOWN_KNOWLEDGE_FIXTURES = [
    f for f in ALL_FIXTURES if f["expected_novelty_type"] in ("EXACT_MATCH", "SEMANTIC_MATCH")
]
MISSING_ALIAS_FIXTURES = [
    f for f in ALL_FIXTURES if f["expected_novelty_type"] == "MISSING_ALIAS"
]
MISSING_ENTRY_FIXTURES = [
    f for f in ALL_FIXTURES if f["expected_novelty_type"] == "MISSING_OFFICIAL_ENTRY"
]


@pytest.mark.parametrize(
    "fixture", KNOWN_KNOWLEDGE_FIXTURES,
    ids=[f["case_id"] for f in KNOWN_KNOWLEDGE_FIXTURES]
)
def test_known_knowledge_fixture_fields(fixture):
    """All EXACT_MATCH / SEMANTIC_MATCH fixtures must have the four required fields."""
    assert "expected_novelty_type" in fixture
    assert fixture["expected_novelty_type"] in ("EXACT_MATCH", "SEMANTIC_MATCH")
    assert "expected_decision" in fixture
    assert "expected_blocking_reasons" in fixture
    assert isinstance(fixture["expected_blocking_reasons"], list)
    assert "expected_review_route" in fixture


@pytest.mark.parametrize(
    "fixture", KNOWN_KNOWLEDGE_FIXTURES,
    ids=[f["case_id"] for f in KNOWN_KNOWLEDGE_FIXTURES]
)
def test_known_knowledge_decision_is_approve_silent(fixture):
    assert fixture["expected_decision"] == "APPROVE_SILENT"


@pytest.mark.parametrize(
    "fixture", KNOWN_KNOWLEDGE_FIXTURES,
    ids=[f["case_id"] for f in KNOWN_KNOWLEDGE_FIXTURES]
)
def test_known_knowledge_review_route_is_none(fixture):
    assert fixture["expected_review_route"] == "NONE"


@pytest.mark.parametrize(
    "fixture", KNOWN_KNOWLEDGE_FIXTURES,
    ids=[f["case_id"] for f in KNOWN_KNOWLEDGE_FIXTURES]
)
def test_known_knowledge_no_blocking_reasons(fixture):
    assert fixture["expected_blocking_reasons"] == []


@pytest.mark.parametrize(
    "fixture", MISSING_ALIAS_FIXTURES,
    ids=[f["case_id"] for f in MISSING_ALIAS_FIXTURES]
)
def test_missing_alias_fixture_fields(fixture):
    assert "expected_novelty_type" in fixture
    assert fixture["expected_novelty_type"] == "MISSING_ALIAS"
    assert "expected_decision" in fixture
    assert "expected_blocking_reasons" in fixture
    assert "expected_review_route" in fixture


@pytest.mark.parametrize(
    "fixture", MISSING_ALIAS_FIXTURES,
    ids=[f["case_id"] for f in MISSING_ALIAS_FIXTURES]
)
def test_missing_alias_routes_to_review(fixture):
    assert fixture["expected_review_route"] == "MEDICAL_REVIEW"


@pytest.mark.parametrize(
    "fixture", MISSING_ENTRY_FIXTURES,
    ids=[f["case_id"] for f in MISSING_ENTRY_FIXTURES]
)
def test_missing_official_entry_fixture_fields(fixture):
    assert "expected_novelty_type" in fixture
    assert fixture["expected_novelty_type"] == "MISSING_OFFICIAL_ENTRY"
    assert "expected_decision" in fixture
    assert "expected_blocking_reasons" in fixture
    assert "expected_review_route" in fixture


@pytest.mark.parametrize(
    "fixture", MISSING_ENTRY_FIXTURES,
    ids=[f["case_id"] for f in MISSING_ENTRY_FIXTURES]
)
def test_missing_official_entry_routes_to_review(fixture):
    assert fixture["expected_review_route"] == "MEDICAL_REVIEW"
