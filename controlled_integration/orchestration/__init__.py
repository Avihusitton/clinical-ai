"""
controlled_integration/orchestration
-------------------------------------
Pipeline orchestrator coordinating multi-gate integration flows safely and deterministically.
"""

from typing import Tuple, Dict, Any, Optional
from ..models import (
    IntegrationRequest, IntegrationDecision, IntegrationExplanation,
    OfficialEvidenceBundle, NoveltyDiscoveryBundle, ConsultationInputBundle,
    ConsultationOutputBundle
)
from ..adapters import GateBAdapter, GateCAdapter, BoundaryAdapter, GateDAdapter, LegacyRetrievalAdapter
from ..feature_flags import FeatureFlagEvaluator
from ..fallback import FallbackHandler
from ..audit import AuditLogger
from ..telemetry import TelemetryCollector, TelemetryRecorder
from ..security import SecurityPolicy
from ..exceptions import IntegrationException, BoundaryViolationError, PIIRejectedError

class IntegrationOrchestrator:
    """
    Master pipeline orchestrator.
    Evaluates operating mode, enforces PII/security policies, invokes gate adapters sequentially,
    enforces boundary safety, and manages fail-closed fallback.
    """
    def __init__(self):
        self.legacy = LegacyRetrievalAdapter()
        self.gate_b = GateBAdapter()
        self.gate_c = GateCAdapter()
        self.boundary = BoundaryAdapter()
        self.gate_d = GateDAdapter()
        self.evaluator = FeatureFlagEvaluator()
        self.fallback = FallbackHandler()
        self.audit = AuditLogger()
        self.telemetry = TelemetryCollector()
        self.security = SecurityPolicy()

    def process(
        self,
        request: IntegrationRequest
    ) -> Tuple[IntegrationDecision, IntegrationExplanation, Any]:
        """
        Executes end-to-end integration request safely.
        """
        self.audit.log_event(
            event_type="INTEGRATION_REQUEST_RECEIVED",
            request_id=request.request_id,
            session_id=request.context.session_id,
            details={"query_text": request.query_text, "user_role": request.context.user_role}
        )

        try:
            # Step 0: PII Security Scanner & Validation
            self.security.validate_input(request.query_text)

            # Step 1: Feature Flag & Operating Mode Evaluation
            mode, flags = self.evaluator.evaluate_mode(
                mode_override=request.operating_mode_override,
                flag_overrides=request.flag_overrides
            )

            self.audit.log_event(
                event_type="FEATURE_FLAGS_EVALUATED",
                request_id=request.request_id,
                session_id=request.context.session_id,
                details={"active_mode": mode, "flags": flags}
            )

            # Execution Path 1: LEGACY_ONLY or EMERGENCY_DISABLED
            if mode in ("LEGACY_ONLY", "EMERGENCY_DISABLED"):
                legacy_res = self.legacy.execute_legacy(request)
                decision = IntegrationDecision(
                    request_id=request.request_id,
                    verdict="LEGACY_SERVED",
                    active_mode=mode
                )
                explanation = IntegrationExplanation(
                    request_id=request.request_id,
                    decision_verdict="LEGACY_SERVED",
                    step_trace=["ingestion", "legacy_adapter"],
                    blocking_reasons=[]
                )
                self.telemetry.record_decision("LEGACY_SERVED")
                self.audit.log_allow(request.request_id, request.context.session_id, {"mode": mode, "verdict": "LEGACY_SERVED"})
                return decision, explanation, legacy_res

            # Execution Path 2: SHADOW_COMPARE
            if mode == "SHADOW_COMPARE":
                # Primary output is strictly legacy baseline
                legacy_res = self.legacy.execute_legacy(request)
                shadow_trace = ["ingestion", "legacy_adapter"]

                # Shadow execution in isolated try block to prevent altering primary result
                try:
                    official_bundle = self.gate_b.extract_official_evidence(request)
                    novelty_bundle = self.gate_c.evaluate_novelty(request)
                    input_bundle = self.boundary.filter_for_consultation(
                        session_id=request.context.session_id,
                        official_bundle=official_bundle,
                        novelty_bundle=novelty_bundle
                    )
                    _ = self.gate_d.process_consultation(request, input_bundle)
                    shadow_trace.append("shadow_graphrag_executed")
                    self.audit.log_event(
                        event_type="SHADOW_COMPARISON_COMPLETED",
                        request_id=request.request_id,
                        session_id=request.context.session_id,
                        details={"shadow_status": "SUCCESS"}
                    )
                except Exception as shadow_err:
                    shadow_trace.append(f"shadow_error: {str(shadow_err)}")
                    self.audit.log_event(
                        event_type="SHADOW_COMPARISON_FAILED",
                        request_id=request.request_id,
                        session_id=request.context.session_id,
                        details={"shadow_error": str(shadow_err)}
                    )

                decision = IntegrationDecision(
                    request_id=request.request_id,
                    verdict="LEGACY_SERVED",
                    active_mode="SHADOW_COMPARE"
                )
                explanation = IntegrationExplanation(
                    request_id=request.request_id,
                    decision_verdict="LEGACY_SERVED",
                    step_trace=shadow_trace,
                    blocking_reasons=[]
                )
                self.telemetry.record_decision("LEGACY_SERVED")
                self.audit.log_allow(request.request_id, request.context.session_id, {"mode": "SHADOW_COMPARE", "verdict": "LEGACY_SERVED"})
                return decision, explanation, legacy_res

            # Execution Path 3: OFFICIAL_RETRIEVAL_ONLY
            if mode == "OFFICIAL_RETRIEVAL_ONLY":
                official_bundle = self.gate_b.extract_official_evidence(request)
                decision = IntegrationDecision(
                    request_id=request.request_id,
                    verdict="OFFICIAL_RAG_SERVED",
                    active_mode=mode
                )
                explanation = IntegrationExplanation(
                    request_id=request.request_id,
                    decision_verdict="OFFICIAL_RAG_SERVED",
                    step_trace=["ingestion", "gate_b_adapter"],
                    score_breakdown={"confidence": official_bundle.confidence_score}
                )
                self.telemetry.record_decision("OFFICIAL_RAG_SERVED")
                self.audit.log_allow(request.request_id, request.context.session_id, {"mode": mode, "verdict": "OFFICIAL_RAG_SERVED"})
                return decision, explanation, official_bundle

            # Execution Path 4: THERAPIST_PILOT (Full pipeline via boundary screening)
            if mode == "THERAPIST_PILOT":
                # Check RBAC access for pilot query
                self.security.check_access(
                    user_role=request.context.user_role,
                    resource_id="pilot_query_advisor",
                    action="POST",
                    context=request.context
                )

                official_bundle = self.gate_b.extract_official_evidence(request)
                novelty_bundle = self.gate_c.evaluate_novelty(request)

                # Screen evidence through Gate C/D Boundary
                input_bundle = self.boundary.filter_for_consultation(
                    session_id=request.context.session_id,
                    official_bundle=official_bundle,
                    novelty_bundle=novelty_bundle
                )
                self.telemetry.record_blocked_evidence(input_bundle.blocked_novelty_count)

                consultation_output = self.gate_d.process_consultation(request, input_bundle)

                decision = IntegrationDecision(
                    request_id=request.request_id,
                    verdict="FULL_PILOT_SERVED",
                    active_mode=mode
                )
                explanation = IntegrationExplanation(
                    request_id=request.request_id,
                    decision_verdict="FULL_PILOT_SERVED",
                    step_trace=["ingestion", "gate_b", "gate_c", "gate_cd_boundary", "gate_d"],
                    boundary_summary={
                        "total_evaluated": len(official_bundle.official_entries) + len(novelty_bundle.candidates),
                        "eligible_count": len(input_bundle.eligible_official_evidence),
                        "blocked_count": input_bundle.blocked_novelty_count
                    }
                )
                self.telemetry.record_decision("FULL_PILOT_SERVED")
                self.audit.log_allow(request.request_id, request.context.session_id, {"mode": mode, "verdict": "FULL_PILOT_SERVED"})
                return decision, explanation, consultation_output

            # Default fallback for unhandled operating modes
            return self._fail_closed_fallback(request, f"Unhandled operating mode: {mode}")

        except Exception as exc:
            return self._fail_closed_fallback(request, str(exc))

    def _fail_closed_fallback(
        self,
        request: IntegrationRequest,
        reason: str
    ) -> Tuple[IntegrationDecision, IntegrationExplanation, Any]:
        """Executes fail-closed fallback to legacy retrieval."""
        event_type = "BOUNDARY_VIOLATION_BLOCKED" if ("Leak" in reason or "Boundary" in reason) else "INTEGRATION_ERROR"
        if "PII" in reason:
            event_type = "PII_REJECTED_BLOCKED"
        elif "denied access" in reason.lower() or "role" in reason.lower():
            event_type = "ACCESS_DENIED_BLOCKED"

        self.audit.log_block(
            request_id=request.request_id,
            session_id=request.context.session_id,
            details={"reason": reason, "event_type": event_type}
        )
        self.audit.log_fallback(
            request_id=request.request_id,
            session_id=request.context.session_id,
            details={"reason": reason, "trigger_rule": "RULE_4_FAIL_CLOSED"}
        )

        decision, fallback_res = self.fallback.execute_fallback(request, reason)
        explanation = IntegrationExplanation(
            request_id=request.request_id,
            decision_verdict="FALLBACK_TRIGGERED",
            step_trace=["error_handler", "fallback"],
            blocking_reasons=[reason]
        )
        self.telemetry.record_decision("FALLBACK_TRIGGERED")
        return decision, explanation, fallback_res
