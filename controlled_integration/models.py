"""
controlled_integration/models.py
--------------------------------
Pure data models and dataclasses defining integration entities.
No production imports, no network I/O, no database side effects.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import uuid

@dataclass(frozen=True)
class IntegrationContext:
    """Execution context and metadata for an integration request."""
    session_id: str
    user_id: str
    user_role: str
    environment: str = "DEV"
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

@dataclass(frozen=True)
class IntegrationRequest:
    """Top-level request container entering the integration pipeline."""
    request_id: str
    query_text: str
    context: IntegrationContext
    operating_mode_override: Optional[str] = None
    flag_overrides: Dict[str, bool] = field(default_factory=dict)

@dataclass(frozen=True)
class OfficialEvidenceBundle:
    """Verified official guidelines and approved graph traversals (Gate A/B)."""
    bundle_id: str
    official_entries: List[Dict[str, Any]] = field(default_factory=list)
    traversed_paths: List[Dict[str, Any]] = field(default_factory=list)
    confidence_score: float = 1.0
    provenance_valid: bool = True

@dataclass(frozen=True)
class NoveltyDiscoveryBundle:
    """Discovery-only novelty candidates and contradictions (Gate C)."""
    bundle_id: str
    candidates: List[Dict[str, Any]] = field(default_factory=list)
    contradictions: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "DISCOVERY_ONLY"
    review_status: str = "PENDING_HUMAN_REVIEW"

@dataclass(frozen=True)
class ConsultationInputBundle:
    """Screened evidence bundle passing Gate C/D boundary, ready for Gate D."""
    session_id: str
    eligible_official_evidence: List[Dict[str, Any]] = field(default_factory=list)
    blocked_novelty_count: int = 0
    boundary_decisions: List[Dict[str, Any]] = field(default_factory=list)
    is_validated: bool = True

@dataclass(frozen=True)
class ConsultationOutputBundle:
    """Structured clinical consultation response produced by Gate D."""
    request_summary: str
    official_entries: List[Dict[str, Any]] = field(default_factory=list)
    interpretations: List[Dict[str, Any]] = field(default_factory=list)
    alternatives: List[Dict[str, Any]] = field(default_factory=list)
    uncertainties: List[Dict[str, Any]] = field(default_factory=list)
    safety_boundaries: List[Dict[str, Any]] = field(default_factory=list)
    therapist_decision_required: bool = True

@dataclass(frozen=True)
class IntegrationDecision:
    """Top-level decision verdict detailing how the request was fulfilled."""
    request_id: str
    verdict: str  # LEGACY_SERVED, OFFICIAL_RAG_SERVED, FULL_PILOT_SERVED, FALLBACK_TRIGGERED
    active_mode: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

@dataclass(frozen=True)
class IntegrationExplanation:
    """Diagnostic explanation payload for audit, debugging, and review."""
    request_id: str
    decision_verdict: str
    step_trace: List[str] = field(default_factory=list)
    blocking_reasons: List[str] = field(default_factory=list)
    score_breakdown: Dict[str, float] = field(default_factory=dict)
    boundary_summary: Dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class IntegrationAuditEvent:
    """Immutable audit event record emitted during pipeline execution."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = "INTEGRATION_EVENT"
    request_id: str = ""
    session_id: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
