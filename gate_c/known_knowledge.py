from typing import Protocol
from .models import NoveltyCandidate, KnownKnowledgeCheck

class KnownKnowledgeProvider(Protocol):
    """
    Protocol for dependency-injected known knowledge checking.
    Abstracts away specific graph or database dependencies.
    """
    def check_candidate(self, candidate: NoveltyCandidate) -> KnownKnowledgeCheck:
        ...
