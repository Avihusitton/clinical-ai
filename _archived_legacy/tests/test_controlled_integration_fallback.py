"""
tests/test_controlled_integration_fallback.py
-----------------------------------------------
Unit tests for FallbackHandler and LegacyRetrievalAdapter.
Verifies fail-closed fallback routing, legacy baseline responses, and reason tracking.
"""

import pytest
import uuid
from controlled_integration.models import IntegrationRequest, IntegrationContext, IntegrationDecision
from controlled_integration.adapters.legacy_adapter import LegacyRetrievalAdapter
from controlled_integration.fallback import FallbackHandler


def test_legacy_retrieval_adapter():
    """Verify LegacyRetrievalAdapter returns deterministic legacy baseline without side effects."""
    adapter = LegacyRetrievalAdapter()
    ctx = IntegrationContext(session_id="s_leg_1", user_id="u_leg_1", user_role="ROLE_INTERNAL_THERAPIST")
    req = IntegrationRequest(
        request_id="req_leg_100",
        query_text="Legacy test query",
        context=ctx,
    )

    res = adapter.execute_legacy(req)

    assert res["request_id"] == "req_leg_100"
    assert res["query_text"] == "Legacy test query"
    assert res["response_type"] == "LEGACY_BASELINE"
    assert res["source"] == "retrieval.py"
    assert res["is_fallback"] is False


def test_fallback_handler_execution():
    """Verify FallbackHandler returns FALLBACK_TRIGGERED IntegrationDecision and attaches fallback reason."""
    handler = FallbackHandler()
    ctx = IntegrationContext(session_id="s_fb_1", user_id="u_fb_1", user_role="ROLE_INTERNAL_THERAPIST")
    req = IntegrationRequest(
        request_id="req_fb_200",
        query_text="Faulted RAG query",
        context=ctx,
    )

    reason_str = "Simulated Graph DB Timeout"
    decision, res = handler.execute_fallback(req, reason=reason_str)

    assert isinstance(decision, IntegrationDecision)
    assert decision.request_id == "req_fb_200"
    assert decision.verdict == "FALLBACK_TRIGGERED"
    assert decision.active_mode == "LEGACY_ONLY"
    assert res["fallback_reason"] == reason_str
    assert res["response_type"] == "LEGACY_BASELINE"


def test_fallback_handler_multiple_reasons():
    """Verify FallbackHandler cleanly handles various system error reasons."""
    handler = FallbackHandler()
    ctx = IntegrationContext(session_id="s_fb_2", user_id="u_fb_2", user_role="ROLE_INTERNAL_THERAPIST")
    req = IntegrationRequest(
        request_id="req_fb_201",
        query_text="Subsystem error query",
        context=ctx,
    )

    error_reasons = [
        "ConnectionRefusedError to Vector Index",
        "BoundaryViolationError: unreviewed novelty detected",
        "SchemaValidationError in response payload",
    ]

    for reason in error_reasons:
        decision, res = handler.execute_fallback(req, reason=reason)
        assert decision.verdict == "FALLBACK_TRIGGERED"
        assert res["fallback_reason"] == reason
