import pytest

from models.second_order_reasoner import SecondOrderReasoner
from models.relation_policy import DirectScoreComponents, PathCandidate

def test_context_fit_is_deterministic_and_injected():
    reasoner = SecondOrderReasoner()
    score1 = reasoner.calculate_context_fit("node_a", "node_b", context="test")
    score2 = reasoner.calculate_context_fit("node_a", "node_b", context="test")
    assert score1 == score2
    assert score1 is not None

def test_effective_degree_excludes_non_traversable_edges():
    reasoner = SecondOrderReasoner()
    edges = [
        {"type": "TREATS", "is_traversable": True, "review_state": "APPROVED"},
        {"type": "NAVIGATES", "is_traversable": False, "review_state": "APPROVED"},
        {"type": "CAUSES", "is_traversable": True, "review_state": "PENDING"}
    ]
    assert reasoner.calculate_effective_degree(edges) == 1

def test_hub_penalty_is_monotonic():
    reasoner = SecondOrderReasoner(free_degree=2, alpha=0.5, minimum_factor=0.1)
    penalty3 = reasoner.calculate_hub_penalty(effective_degree=3)
    penalty4 = reasoner.calculate_hub_penalty(effective_degree=4)
    assert penalty4 <= penalty3

def test_hub_penalty_respects_free_degree():
    reasoner = SecondOrderReasoner(free_degree=5, alpha=0.5, minimum_factor=0.1)
    penalty = reasoner.calculate_hub_penalty(effective_degree=3)
    assert penalty == 1.0

def test_hub_penalty_respects_minimum_factor():
    reasoner = SecondOrderReasoner(free_degree=1, alpha=0.9, minimum_factor=0.1)
    penalty = reasoner.calculate_hub_penalty(effective_degree=100)
    assert penalty >= 0.1

def test_duplicate_paths_collapse_deterministically():
    reasoner = SecondOrderReasoner()
    path1 = PathCandidate(nodes=["A", "B", "C"], edges=["e1", "e2"])
    path2 = PathCandidate(nodes=["A", "B", "C"], edges=["e1", "e2"])
    collapsed = reasoner.collapse_duplicates([path1, path2])
    assert len(collapsed) == 1

def test_ties_resolve_deterministically():
    reasoner = SecondOrderReasoner()
    path1 = PathCandidate(nodes=["A", "B"], edges=["e1"])
    path2 = PathCandidate(nodes=["A", "C"], edges=["e2"])
    resolved = reasoner.resolve_ties([path1, path2], scores=[0.8, 0.8])
    assert len(resolved) == 1
    assert resolved[0] in [path1, path2]

def test_explanation_includes_every_score_component():
    reasoner = SecondOrderReasoner()
    explanation = reasoner.generate_accepted_explanation(
        path=PathCandidate(nodes=["A", "B"], edges=["e1"]),
        score_components=DirectScoreComponents(
            source_confidence=0.9,
            review_confidence=0.9,
            relation_specificity=0.8,
            context_fit=0.7,
            provenance_factor=1.0,
            path_specificity=0.6
        ),
        final_score=0.75,
        hub_penalty=1.0
    )
    assert "source_confidence" in explanation["score_components"]
    assert "review_confidence" in explanation["score_components"]
    assert "relation_specificity" in explanation["score_components"]
    assert "context_fit" in explanation["score_components"]
    assert "provenance_factor" in explanation["score_components"]
    assert "path_specificity" in explanation["score_components"]

def test_rejected_explanation_includes_blocking_reasons():
    reasoner = SecondOrderReasoner()
    explanation = reasoner.generate_rejected_explanation(
        path=PathCandidate(nodes=["A", "B"], edges=["e1"]),
        blocking_reasons=[{"code": "ERR_01", "description": "Blocked"}]
    )
    assert "blocking_reasons" in explanation
    assert len(explanation["blocking_reasons"]) > 0
