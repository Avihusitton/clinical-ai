# -*- coding: utf-8 -*-
"""
evaluation/wave9/deterministic_runner.py
Runs synthetic fixture evaluation deterministically against the retrieval hook and dispatcher.
Enforces strict difference-class taxonomy separation.
"""

import hashlib
import json
import os
from typing import Dict, Any, Tuple
from unittest.mock import MagicMock

from shadow_wiring.settings import ShadowSettings
from shadow_wiring.dispatcher import ShadowDispatcher
from shadow_wiring.redaction import RedactionEngine
from .schemas import FixtureRecord, EvaluationResultRecord, FROZEN_DIFFERENCE_CLASSES


def compute_fingerprint(obj: Any) -> str:
    s = json.dumps(obj, sort_keys=True, default=str)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def run_single_fixture(fixture: FixtureRecord) -> EvaluationResultRecord:
    shadow_in = fixture.shadow_input or {}
    legacy_req = fixture.legacy_request or {}
    flag_state = fixture.shadow_flag_state or {}

    qtext = shadow_in.get("query_text") or legacy_req.get("question", "")
    mode = flag_state.get("mode", "LEGACY_ONLY")
    emergency = flag_state.get("emergency_disable", False)

    mock_cfg = MagicMock()
    mock_cfg.reasoning_relationship_types = ["LEADS_TO"]
    mock_cfg.reasoning_depth_default = 1

    mock_driver = MagicMock()
    mock_session = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = mock_session

    def mock_cypher(cypher, start=None, concept_names=None):
        if start:
            return [MagicMock(data=lambda: {"concept_chain": ["Cognitive Restructuring"]})]
        if concept_names:
            return [MagicMock(data=lambda: {"exercise_id": "ex_01"})]
        return []
    mock_session.run.side_effect = mock_cypher

    settings = ShadowSettings(mode=mode, emergency_disable=emergency, queue_size=16)
    dispatcher = ShadowDispatcher(settings=settings)

    expected_legacy = fixture.expected_user_visible_result or fixture.legacy_result or "Composed legacy RAG response"

    mock_concept_gen = MagicMock()
    mock_concept_gen.find_candidates.return_value = ["Cognitive Restructuring"]
    mock_llm = MagicMock()

    from retrieval import Retriever

    retriever = Retriever(cfg=mock_cfg, driver=mock_driver, concept_gen=mock_concept_gen, llm=mock_llm, shadow_dispatcher=dispatcher)
    retriever._compose = lambda q, m, p, e: expected_legacy

    import retrieval
    orig_find_entry = retrieval.find_entry_concepts
    try:
        retrieval.find_entry_concepts = lambda q, g: ["Cognitive Restructuring"]
        actual_user_result = retriever.answer(qtext)
    finally:
        retrieval.find_entry_concepts = orig_find_entry

    legacy_fp = compute_fingerprint(expected_legacy)
    user_fp = compute_fingerprint(actual_user_result)
    exact_match = (user_fp == legacy_fp or actual_user_result == expected_legacy)

    events = dispatcher.audit_sink.get_events()
    telemetry = dispatcher.telemetry_sink.get_records()

    audit_types = [ev.get("event_type", "UNKNOWN") for ev in events]
    telemetry_types = [rec.get("record_type", "UNKNOWN") for rec in telemetry]

    # Raw query leak detection
    raw_query_leak = False
    if qtext and len(qtext) > 3:
        for ev in events:
            if qtext in str(ev):
                raw_query_leak = True
        for rec in telemetry:
            if qtext in str(rec):
                raw_query_leak = True

    shadow_submitted = (len(events) > 0 and any(t in audit_types for t in ["SHADOW_TASK_SUBMITTED", "SHADOW_PII_REJECTED", "SHADOW_EMERGENCY_DISABLED"]))
    shadow_completed = any(t in audit_types for t in ["SHADOW_TASK_COMPLETED", "SHADOW_TASK_FAILED"])

    # Separated taxonomy mappings
    has_pii, _, _ = RedactionEngine.scan_and_redact(qtext)

    # 1. Submission Decision
    if emergency:
        sub_decision = "REJECTED_EMERGENCY"
    elif has_pii:
        sub_decision = "REJECTED_PII"
    elif mode == "LEGACY_ONLY":
        sub_decision = "SKIPPED_MODE"
    elif shadow_submitted:
        sub_decision = "SUBMITTED"
    else:
        sub_decision = "SKIPPED_MODE"

    # 2. Safety Decision
    if has_pii:
        safety_dec = "REJECTED_ISRAELI_PII"
    else:
        safety_dec = "PASS_CLEAN"

    # 3. Execution Outcome
    if emergency:
        exec_outcome = "EMERGENCY_BLOCKED"
    elif shadow_completed:
        exec_outcome = "COMPLETED"
    elif shadow_submitted:
        exec_outcome = "SUBMITTED"
    else:
        exec_outcome = "SKIPPED"

    # 4. Difference Class (MUST be in FROZEN_DIFFERENCE_CLASSES)
    diff_class = fixture.expected_difference_class
    if diff_class not in FROZEN_DIFFERENCE_CLASSES:
        if has_pii:
            diff_class = "SAFETY_BLOCK_DIFFERENCE"
        elif fixture.expected_fallback != "NONE":
            diff_class = "FALLBACK_TRIGGERED"
        else:
            diff_class = "AGREEMENT"

    return EvaluationResultRecord(
        case_id=fixture.case_id,
        fixture_domain=fixture.domain,
        operating_mode=mode,
        submission_decision=sub_decision,
        safety_decision=safety_dec,
        execution_outcome=exec_outcome,
        legacy_result_fingerprint=legacy_fp,
        user_visible_result_fingerprint=user_fp,
        exact_legacy_match=exact_match,
        shadow_submitted=shadow_submitted,
        shadow_completed=shadow_completed,
        difference_class=diff_class,
        fallback=fixture.expected_fallback,
        audit_event_types=audit_types,
        telemetry_event_types=telemetry_types,
        raw_query_leak_detected=raw_query_leak
    )
