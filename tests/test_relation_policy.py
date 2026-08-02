import pytest

from models.relation_policy import RelationDefinition, RelationPolicyRegistry, EdgeEvidence, PathCandidate

def test_policy_schema_rejects_unknown_fields():
    with pytest.raises(Exception):
        RelationDefinition(
            relation_type="TREATS",
            is_traversable=True,
            is_terminal=False,
            semantic_category="clinical",
            unknown_field="should_fail"
        )

def test_unknown_relations_fail_closed():
    registry = RelationPolicyRegistry(policies={})
    assert registry.is_allowed("UNKNOWN_RELATION") is False

def test_pending_is_excluded():
    registry = RelationPolicyRegistry(policies={"TREATS": RelationDefinition(relation_type="TREATS", is_traversable=True, is_terminal=False, semantic_category="clinical")})
    assert registry.evaluate_review_state("PENDING") == "excluded by default"

def test_rejected_is_blocked():
    registry = RelationPolicyRegistry(policies={"TREATS": RelationDefinition(relation_type="TREATS", is_traversable=True, is_terminal=False, semantic_category="clinical")})
    assert registry.evaluate_review_state("REJECTED") == "always blocked"

def test_approved_may_proceed():
    registry = RelationPolicyRegistry(policies={"TREATS": RelationDefinition(relation_type="TREATS", is_traversable=True, is_terminal=False, semantic_category="clinical")})
    assert registry.evaluate_review_state("APPROVED") == "eligible"

def test_navigation_only_relations_do_not_infer():
    nav_relation = RelationDefinition(relation_type="NAVIGATES_TO", is_traversable=False, is_terminal=False, semantic_category="navigation")
    assert not nav_relation.is_traversable

def test_exercise_cannot_bridge():
    exercise_rel = RelationDefinition(relation_type="EXERCISE", is_traversable=False, is_terminal=True, semantic_category="intervention")
    assert not exercise_rel.is_traversable

def test_exercise_may_be_terminal():
    exercise_rel = RelationDefinition(relation_type="EXERCISE", is_traversable=False, is_terminal=True, semantic_category="intervention")
    assert exercise_rel.is_terminal

def test_ordered_composition_is_enforced():
    registry = RelationPolicyRegistry(policies={
        "CHAIN": RelationDefinition(
            relation_type="CHAIN", 
            is_traversable=True, 
            is_terminal=False, 
            semantic_category="chain",
            ordered_composition=["CAUSES", "TREATS"]
        )
    })
    assert registry.validate_composition(["CAUSES", "TREATS"]) != registry.validate_composition(["TREATS", "CAUSES"])

def test_reverse_composition_is_not_assumed():
    registry = RelationPolicyRegistry(policies={})
    assert registry.is_reverse_assumed("TREATS") is False

def test_cycles_are_rejected():
    registry = RelationPolicyRegistry(policies={})
    candidate = PathCandidate(nodes=["A", "B", "A"], edges=["e1", "e2"])
    assert registry.has_cycle(candidate) is True

def test_self_loops_are_rejected():
    registry = RelationPolicyRegistry(policies={})
    candidate = PathCandidate(nodes=["A", "A"], edges=["e1"])
    assert registry.has_self_loop(candidate) is True

def test_missing_provenance_is_blocked():
    registry = RelationPolicyRegistry(policies={})
    with pytest.raises(Exception):
        EdgeEvidence(source_id="src1", extraction_method="method", confidence=0.9, provenance=None)
