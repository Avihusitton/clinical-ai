"""
controlled_integration package
------------------------------
Isolated adapter layer connecting closed pipeline Gates without changing production retrieval.
"""

from .models import (
    IntegrationRequest,
    IntegrationContext,
    OfficialEvidenceBundle,
    NoveltyDiscoveryBundle,
    ConsultationInputBundle,
    ConsultationOutputBundle,
    IntegrationDecision,
    IntegrationExplanation,
    IntegrationAuditEvent,
)
from .exceptions import (
    IntegrationException,
    BoundaryViolationError,
    FeatureFlagError,
    PIIRejectedError,
    AccessDeniedError,
    RawNarrativeStoreForbiddenError,
)
from .orchestration import IntegrationOrchestrator

__all__ = [
    "IntegrationRequest",
    "IntegrationContext",
    "OfficialEvidenceBundle",
    "NoveltyDiscoveryBundle",
    "ConsultationInputBundle",
    "ConsultationOutputBundle",
    "IntegrationDecision",
    "IntegrationExplanation",
    "IntegrationAuditEvent",
    "IntegrationException",
    "BoundaryViolationError",
    "FeatureFlagError",
    "PIIRejectedError",
    "AccessDeniedError",
    "RawNarrativeStoreForbiddenError",
    "IntegrationOrchestrator",
]
