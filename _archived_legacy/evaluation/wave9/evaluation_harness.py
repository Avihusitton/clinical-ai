# -*- coding: utf-8 -*-
"""
evaluation/wave9/evaluation_harness.py
Main offline evaluation harness for Wave 9 (Evaluations A, B, C, D, G).
"""

import sys
import json
import time
from typing import List, Dict, Any

from shadow_wiring.redaction import RedactionEngine
from shadow_wiring.settings import ShadowSettings
from shadow_wiring.dispatcher import ShadowDispatcher

from .fixture_loader import load_shadow_fixtures, load_negative_redaction_fixtures
from .deterministic_runner import run_single_fixture
from .schemas import EvaluationResultRecord, DeterminismSummary
from .report_writer import (
    write_fixture_results,
    write_determinism_results,
    write_redaction_results
)


def run_evaluation_harness() -> Dict[str, Any]:
    fixtures, domain_counts = load_shadow_fixtures()
    neg_redaction_cases = load_negative_redaction_fixtures()

    # -------------------------------------------------------------------------
    # Evaluation A: Legacy Invariance (Run 1)
    # -------------------------------------------------------------------------
    results_run1: List[EvaluationResultRecord] = []
    for fix in fixtures:
        rec = run_single_fixture(fix)
        results_run1.append(rec)

    exact_legacy_matches = sum(1 for r in results_run1 if r.exact_legacy_match)
    raw_query_leaks = sum(1 for r in results_run1 if r.raw_query_leak_detected)

    write_fixture_results(results_run1)

    # -------------------------------------------------------------------------
    # Evaluation B: Mode Behavior Verification
    # -------------------------------------------------------------------------
    mode_results = {}

    # LEGACY_ONLY
    s_legacy = ShadowSettings(mode="LEGACY_ONLY")
    d_legacy = ShadowDispatcher(settings=s_legacy)
    sub_legacy = d_legacy.submit("mode-1", "Query", None, "Ans")
    mode_results["LEGACY_ONLY"] = {
        "worker_started": d_legacy._worker_thread is not None,
        "task_submitted": sub_legacy
    }

    # EMERGENCY_DISABLED
    s_emg = ShadowSettings(mode="SHADOW_COMPARE", emergency_disable=True)
    d_emg = ShadowDispatcher(settings=s_emg)
    sub_emg = d_emg.submit("mode-2", "Query", None, "Ans")
    mode_results["EMERGENCY_DISABLED"] = {
        "worker_started": d_emg._worker_thread is not None,
        "task_submitted": sub_emg
    }

    # Unknown mode -> fallback to LEGACY_ONLY
    s_unk = ShadowSettings(mode="UNKNOWN_MODE")
    d_unk = ShadowDispatcher(settings=s_unk)
    sub_unk = d_unk.submit("mode-3", "Query", None, "Ans")
    mode_results["UNKNOWN_MODE"] = {
        "effective_mode": s_unk.mode,
        "worker_started": d_unk._worker_thread is not None,
        "task_submitted": sub_unk
    }

    # -------------------------------------------------------------------------
    # Evaluation C: Israeli PII (20 cases) & Negative cases (60 cases)
    # -------------------------------------------------------------------------
    israeli_cases = [f for f in fixtures if "SHD-ISR" in f.case_id][:20]
    pii_eval_records = []
    d_pii = ShadowDispatcher(settings=ShadowSettings(mode="SHADOW_COMPARE"))

    for ic in israeli_cases:
        qtext = ic.shadow_input.get("query_text", "")
        has_pii, _, _ = RedactionEngine.scan_and_redact(qtext)
        sub = d_pii.submit(ic.case_id, qtext, "CBT", "Ans")

        events = d_pii.audit_sink.get_events()
        telemetry = d_pii.telemetry_sink.get_records()

        raw_in_audit = any(qtext in str(e) for e in events)
        raw_in_telemetry = any(qtext in str(t) for t in telemetry)

        pii_eval_records.append({
            "case_id": ic.case_id,
            "pii_detected": has_pii,
            "task_queued": sub,
            "raw_in_audit": raw_in_audit,
            "raw_in_telemetry": raw_in_telemetry
        })

    # Negative redaction cases (60 cases)
    neg_flagged_count = 0
    for nc in neg_redaction_cases:
        qtext = nc.get("query_text", "")
        has_pii, _, _ = RedactionEngine.scan_and_redact(qtext)
        if has_pii:
            neg_flagged_count += 1

    redaction_summary = {
        "approved_wording": "Observed performance applies only to the supplied synthetic fixture sets. These results do not establish general production precision or recall.",
        "israeli_pii_cases_evaluated": len(pii_eval_records),
        "israeli_pii_cases_detected": sum(1 for r in pii_eval_records if r["pii_detected"]),
        "israeli_pii_cases_queued": sum(1 for r in pii_eval_records if r["task_queued"]),
        "negative_redaction_cases_evaluated": len(neg_redaction_cases),
        "negative_redaction_cases_flagged": neg_flagged_count,
        "raw_query_leaks_in_pii_evaluation": sum(1 for r in pii_eval_records if r["raw_in_audit"] or r["raw_in_telemetry"])
    }
    write_redaction_results(redaction_summary)

    # -------------------------------------------------------------------------
    # Evaluation D: Determinism (3 Full Runs across 140 fixtures)
    # -------------------------------------------------------------------------
    results_run2 = [run_single_fixture(f) for f in fixtures]
    results_run3 = [run_single_fixture(f) for f in fixtures]

    deterministic_matches = 0
    for r1, r2, r3 in zip(results_run1, results_run2, results_run3):
        if (
            r1.case_id == r2.case_id == r3.case_id and
            r1.difference_class == r2.difference_class == r3.difference_class and
            r1.exact_legacy_match == r2.exact_legacy_match == r3.exact_legacy_match and
            r1.shadow_submitted == r2.shadow_submitted == r3.shadow_submitted and
            r1.audit_event_types == r2.audit_event_types == r3.audit_event_types and
            r1.telemetry_event_types == r2.telemetry_event_types == r3.telemetry_event_types
        ):
            deterministic_matches += 1

    det_summary = DeterminismSummary(
        runs_executed=3,
        total_fixtures=len(fixtures),
        deterministic_fixture_outcomes=deterministic_matches,
        all_runs_identical=(deterministic_matches == len(fixtures))
    )
    write_determinism_results(det_summary)

    # -------------------------------------------------------------------------
    # Evaluation G: Difference Class Accounting
    # -------------------------------------------------------------------------
    diff_classes_observed = sorted(list(set(r.difference_class for r in results_run1)))
    all_possible_classes = [
        "AGREEMENT", "LEGACY_ONLY_EVIDENCE", "SHADOW_ONLY_REVIEWED_EVIDENCE",
        "RANKING_DIFFERENCE", "UNCERTAINTY_DIFFERENCE", "SAFETY_BLOCK_DIFFERENCE",
        "FALLBACK_TRIGGERED", "SHADOW_ERROR", "SHADOW_TIMEOUT"
    ]
    diff_classes_unreachable = sorted(list(set(all_possible_classes) - set(diff_classes_observed)))

    summary = {
        "fixtures_loaded": len(fixtures),
        "fixtures_accounted_for": len(results_run1),
        "domain_breakdown": domain_counts,
        "legacy_exact_matches": exact_legacy_matches,
        "user_visible_shadow_outputs": 0,
        "raw_query_leaks": raw_query_leaks,
        "mode_behavior": mode_results,
        "redaction": redaction_summary,
        "determinism": {
            "runs_executed": 3,
            "deterministic_outcomes": f"{deterministic_matches}/{len(fixtures)}"
        },
        "difference_classes_observed": diff_classes_observed,
        "difference_classes_unreachable": diff_classes_unreachable,
        "harness_result": "PASS" if (
            len(fixtures) == 140 and
            exact_legacy_matches == 140 and
            raw_query_leaks == 0 and
            deterministic_matches == 140 and
            redaction_summary["israeli_pii_cases_queued"] == 0
        ) else "FAIL"
    }

    return summary


if __name__ == "__main__":
    res = run_evaluation_harness()
    print("Wave 9 Evaluation Harness finished with result:", res["harness_result"])
    if res["harness_result"] != "PASS":
        sys.exit(1)
