"""
controlled_integration/fallback/fallback_handler.py
----------------------------------------------------
Circuit breaker and fail-closed fallback handler routing to legacy retrieval baseline or tiered degradation.
"""

from typing import Dict, Any, Tuple, List, Optional
from ..models import IntegrationRequest, IntegrationDecision
from ..adapters.legacy_adapter import LegacyRetrievalAdapter

class FallbackHandler:
    """
    Executes fail-closed fallback to legacy retrieval baseline or tiered degradation outputs.
    """
    def __init__(self):
        self.legacy_adapter = LegacyRetrievalAdapter()

    def execute_fallback(
        self,
        request: IntegrationRequest,
        reason: str,
        trigger_rule: str = "RULE_1_SYSTEM_FAIL",
        tier: int = 4
    ) -> Tuple[IntegrationDecision, Dict[str, Any]]:
        """
        Executes legacy retrieval and constructs a FALLBACK_TRIGGERED IntegrationDecision and response payload.
        """
        legacy_res = self.legacy_adapter.execute_legacy(request)

        fallback_payload = {
            "query_id": request.request_id,
            "fallback_reason": reason,
            "response_type": "LEGACY_BASELINE",
            "is_fallback": False,
            "status": "FALLBACK_LEGACY" if tier == 4 else ("EMERGENCY_STATIC" if tier == 5 else "DEGRADED"),
            "operating_mode_active": "EMERGENCY_DISABLED" if tier == 5 else "LEGACY_ONLY",
            "tier_executed": f"TIER_{tier}_LEGACY_BASELINE" if tier == 4 else f"TIER_{tier}_EMERGENCY",
            "fallback_flags": {
                "legacy_fallback_used": True,
                "novelty_suppressed": True,
                "autonomous_advice_suppressed": True,
                "fallback_reason": reason,
                "trigger_rule": trigger_rule,
            },
            "content": legacy_res if isinstance(legacy_res, dict) else {"text": str(legacy_res)},
            "audit_trace_id": f"trace-{request.request_id}-fallback"
        }

        decision = IntegrationDecision(
            request_id=request.request_id,
            verdict="FALLBACK_TRIGGERED",
            active_mode="EMERGENCY_DISABLED" if tier == 5 else "LEGACY_ONLY"
        )
        return decision, fallback_payload

    def execute_raw_evidence_fallback(
        self,
        request: IntegrationRequest,
        evidence_chunks: List[Dict[str, Any]],
        reason: str
    ) -> Tuple[IntegrationDecision, Dict[str, Any]]:
        """
        Tier 2 Fallback: Advisory formatting error -> return raw verified evidence chunks only.
        """
        fallback_payload = {
            "query_id": request.request_id,
            "status": "DEGRADED",
            "operating_mode_active": request.operating_mode_override or "THERAPIST_PILOT",
            "tier_executed": "TIER_2_RAW_EVIDENCE_ONLY",
            "fallback_flags": {
                "legacy_fallback_used": False,
                "novelty_suppressed": True,
                "autonomous_advice_suppressed": True,
                "fallback_reason": reason,
                "output_type": "RAW_EVIDENCE_ONLY"
            },
            "content": {
                "disclaimer": "ATTENTION: Advisory formatting unavailable. Presenting verified source evidence chunks for human therapist review.",
                "evidence_chunks": evidence_chunks
            },
            "audit_trace_id": f"trace-{request.request_id}-tier2"
        }
        decision = IntegrationDecision(
            request_id=request.request_id,
            verdict="FALLBACK_TRIGGERED",
            active_mode="THERAPIST_PILOT"
        )
        return decision, fallback_payload

    def execute_emergency_fallback(
        self,
        request: IntegrationRequest,
        reason: str
    ) -> Tuple[IntegrationDecision, Dict[str, Any]]:
        """
        Tier 5 Fallback: Master kill-switch mode -> static emergency response notice.
        """
        return self.execute_fallback(request, reason=reason, trigger_rule="RULE_4_FAIL_CLOSED", tier=5)
