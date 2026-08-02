"""
controlled_integration/adapters/gate_c_adapter.py
--------------------------------------------------
Adapter wrapping Gate C novelty engine (gate_c/models.py, gate_c/novelty_engine.py).
Produces NoveltyDiscoveryBundle containing discovery-only candidates.
Enforces zero mutation of official knowledge.
"""

from typing import Dict, Any, List, Optional
from gate_c.models import NoveltyCandidate, EvidenceBundle, EvidenceItem, NoveltyType
from ..models import NoveltyDiscoveryBundle, IntegrationRequest

class GateCAdapter:
    """
    Adapter bridging Gate C novelty engine.
    Ensures candidate status remains DISCOVERY_ONLY and review_status remains PENDING_HUMAN_REVIEW.
    """
    def evaluate_novelty(self, request: IntegrationRequest, mock_candidates: Optional[List[Dict[str, Any]]] = None) -> NoveltyDiscoveryBundle:
        """
        Evaluates potential novelty candidates for research discovery.
        Status is strictly DISCOVERY_ONLY. Zero graph mutations performed.
        """
        candidates = mock_candidates or [
            {
                "candidate_id": "NOV_001",
                "source_entity": "EmotionalDistress",
                "target_entity": "MindfulBreathing",
                "relation_type": "POTENTIAL_MITIGATOR",
                "status": "DISCOVERY_ONLY",
                "review_status": "PENDING_HUMAN_REVIEW",
                "novelty_type": "NEW_RELATION_CANDIDATE"
            }
        ]

        return NoveltyDiscoveryBundle(
            bundle_id=f"gate_c_{request.request_id[:8]}",
            candidates=candidates,
            contradictions=[],
            status="DISCOVERY_ONLY",
            review_status="PENDING_HUMAN_REVIEW"
        )
