# -*- coding: utf-8 -*-
from shadow_wiring.models import ShadowTaskPayload, ShadowComparisonResult


def test_shadow_task_payload_defaults():
    payload = ShadowTaskPayload(
        request_id="req-001",
        redacted_query_hash="hash-123",
        modality="ACT",
        legacy_result_hash="hash-456"
    )
    assert payload.request_id == "req-001"
    assert payload.redacted_query_hash == "hash-123"
    assert payload.modality == "ACT"
    assert payload.legacy_result_hash == "hash-456"
    assert payload.user_id_hash == "sha256:anonymous_therapist"


def test_shadow_comparison_result_defaults():
    res = ShadowComparisonResult(
        request_id="req-002",
        difference_class="AGREEMENT",
        legacy_latency_ms=12.5,
        shadow_latency_ms=14.1,
        shadow_verdict="OFFICIAL_RAG_SERVED",
        is_fallback=False
    )
    assert res.request_id == "req-002"
    assert res.difference_class == "AGREEMENT"
    assert res.is_fallback is False
