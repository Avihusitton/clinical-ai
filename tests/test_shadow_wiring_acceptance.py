# -*- coding: utf-8 -*-
import json
import pytest
from shadow_wiring.settings import ShadowSettings
from shadow_wiring.dispatcher import ShadowDispatcher
from shadow_wiring.redaction import RedactionEngine
from shadow_wiring.comparator import ShadowComparator

FIXTURE_PATH = "tests/fixtures/shadow_wiring/shadow_cases.jsonl"


def load_shadow_fixtures():
    cases = []
    with open(FIXTURE_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                cases.append(json.loads(line))
    return cases


SHADOW_FIXTURES = load_shadow_fixtures()


def test_shadow_fixture_count():
    assert len(SHADOW_FIXTURES) == 140


@pytest.mark.parametrize("case", SHADOW_FIXTURES, ids=[c["case_id"] for c in SHADOW_FIXTURES])
def test_shadow_acceptance_case(case):
    case_id = case["case_id"]
    mode = case.get("operating_mode", "SHADOW_COMPARE")
    query = case.get("synthetic_query", "")
    pii_present = case.get("pii_present", False)
    expected_sub = case.get("expected_submission_result", True)
    expected_diff = case.get("expected_difference_class", "AGREEMENT")
    expected_audit = case.get("expected_audit_event", "AUDIT_SHADOW_COMPARED")

    # 1. Verify PII scanning parity
    has_pii, redacted, tokens = RedactionEngine.scan_and_redact(query)
    assert has_pii == pii_present, f"Case {case_id}: PII mismatch (got {has_pii}, expected {pii_present})"

    # 2. Test dispatcher submission
    settings = ShadowSettings(mode=mode)
    dispatcher = ShadowDispatcher(settings=settings)

    submitted = dispatcher.submit(case_id, query, "CBT", "Legacy response mock")
    assert submitted == expected_sub, f"Case {case_id}: Submission result mismatch (got {submitted}, expected {expected_sub})"

    # 3. Test comparator classification
    shadow_mock = {
        "request_id": case_id,
        "difference_class": expected_diff if not pii_present else "SAFETY_BLOCK_DIFFERENCE",
        "verdict": "OFFICIAL_RAG_SERVED",
        "is_fallback": pii_present or (mode != "SHADOW_COMPARE")
    }
    if pii_present:
        shadow_mock["error"] = "PII_REJECTED"

    comp = ShadowComparator.classify("hash123", shadow_mock)
    if pii_present:
        assert comp.difference_class == "SAFETY_BLOCK_DIFFERENCE"
        assert comp.is_fallback is True
    else:
        assert comp.difference_class == expected_diff

    # 4. Verify no raw narrative text in audit events
    events = dispatcher.audit_sink.get_events()
    for e in events:
        payload = e.get("payload", {})
        assert "raw_query" not in payload
        assert "query_text" not in payload
        assert "raw_narrative" not in payload
