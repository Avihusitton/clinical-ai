from typing import List
from .models import NoveltyCandidate, NoveltyType, NoveltyExplanation, NoveltyDecision

class ExplainabilityEngine:
    """
    Constructs deterministic explanations for novelty decisions.
    """
    def explain(self, candidate: NoveltyCandidate, novelty_type: NoveltyType, reasons: List[str]) -> NoveltyDecision:
        explanation = NoveltyExplanation(
            candidate_id=candidate.candidate_id,
            decision=novelty_type.value,
            reasoning=reasons
        )
        return NoveltyDecision(
            candidate=candidate,
            novelty_type=novelty_type,
            explanation=explanation
        )
