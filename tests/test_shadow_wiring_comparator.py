# -*- coding: utf-8 -*-
from shadow_wiring.comparator import ShadowComparator


def test_comparator_agreement():
    res = ShadowComparator.classify("hash123", {
        "request_id": "req-10",
        "difference_class": "AGREEMENT",
        "verdict": "OFFICIAL_RAG_SERVED",
        "is_fallback": False
    })
    assert res.request_id == "req-10"
    assert res.difference_class == "AGREEMENT"
    assert res.is_fallback is False


def test_comparator_pii_rejected():
    res = ShadowComparator.classify("hash123", {
        "request_id": "req-11",
        "error": "PII_REJECTED"
    })
    assert res.request_id == "req-11"
    assert res.difference_class == "SAFETY_BLOCK_DIFFERENCE"
    assert res.is_fallback is True


def test_comparator_timeout():
    res = ShadowComparator.classify("hash123", {
        "request_id": "req-12",
        "error": "SHADOW_TIMEOUT"
    })
    assert res.request_id == "req-12"
    assert res.difference_class == "SHADOW_TIMEOUT"
    assert res.is_fallback is True
