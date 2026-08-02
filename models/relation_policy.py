from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from enum import Enum

class DecisionStatus(Enum):
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"

@dataclass
class BlockingReason:
    code: str
    description: str

@dataclass
class ExplanationPayload:
    accepted_path: Optional[Dict[str, Any]] = None
    rejected_path: Optional[Dict[str, Any]] = None

@dataclass
class PathDecision:
    status: DecisionStatus
    final_score: float
    explanation: ExplanationPayload

@dataclass
class RelationDefinition:
    relation_type: str
    is_traversable: bool
    is_terminal: bool
    semantic_category: str
    ordered_composition: Optional[List[str]] = None

@dataclass
class EdgeEvidence:
    source_id: str
    extraction_method: str
    confidence: float

@dataclass
class PathCandidate:
    nodes: List[str]
    edges: List[str]

@dataclass
class DirectScoreComponents:
    source_confidence: float
    review_confidence: float
    relation_specificity: float
    context_fit: float
    provenance_factor: float
    path_specificity: float

class RelationPolicyRegistry:
    def __init__(self, policies: Dict[str, RelationDefinition] = None):
        self.policies = policies or {}

    def get_policy(self, relation_type: str) -> Optional[RelationDefinition]:
        return self.policies.get(relation_type)

    def is_allowed(self, relation_type: str) -> bool:
        return relation_type in self.policies

    def validate_unknown(self, relation_type: str) -> bool:
        return relation_type in self.policies
        
    def evaluate_review_state(self, state: str) -> str:
        if state == "APPROVED": return "eligible"
        if state == "PENDING": return "excluded by default"
        if state == "REJECTED": return "always blocked"
        return "blocked"

    def validate_review_state(self, relation_type: str, state: str) -> bool:
        return state == "APPROVED"
        
    def validate_navigation_only(self, relation_type: str) -> bool:
        policy = self.get_policy(relation_type)
        if policy and not policy.is_traversable:
            return False
        return True

    def validate_exercise_bridge(self, node_type: str, is_bridge: bool) -> bool:
        if node_type == "Exercise" and is_bridge:
            return False
        return True

    def validate_composition(self, rels: List[str]) -> bool:
        for policy in self.policies.values():
            if policy.ordered_composition == rels:
                return True
        return False

    def validate_ordered_composition(self, source_rel: str, target_rel: str) -> bool:
        return True
        
    def is_reverse_assumed(self, relation_type: str) -> bool:
        return False
        
    def has_cycle(self, path: PathCandidate) -> bool:
        return len(path.nodes) != len(set(path.nodes))
        
    def has_self_loop(self, path: PathCandidate) -> bool:
        return len(path.nodes) > 1 and path.nodes[0] == path.nodes[1]

    def validate_cycles(self, path: PathCandidate) -> bool:
        return len(path.nodes) == len(set(path.nodes))

    def validate_provenance(self, has_provenance: bool) -> bool:
        return has_provenance
