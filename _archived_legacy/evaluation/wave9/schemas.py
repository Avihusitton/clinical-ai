# -*- coding: utf-8 -*-
"""
evaluation/wave9/schemas.py
Pydantic/Dataclass schemas for Wave 9 evaluation records.
Refactored for strict taxonomy separation: fixture_domain, operating_mode,
submission_decision, safety_decision, execution_outcome, and difference_class.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field


FROZEN_DIFFERENCE_CLASSES = {
    "AGREEMENT",
    "LEGACY_ONLY_EVIDENCE",
    "SHADOW_ONLY_REVIEWED_EVIDENCE",
    "RANKING_DIFFERENCE",
    "UNCERTAINTY_DIFFERENCE",
    "SAFETY_BLOCK_DIFFERENCE",
    "FALLBACK_TRIGGERED",
    "SHADOW_ERROR",
    "SHADOW_TIMEOUT",
}


@dataclass
class FixtureRecord:
    case_id: str
    domain: str
    legacy_request: Dict[str, Any]
    legacy_result: Any
    shadow_flag_state: Dict[str, Any]
    shadow_input: Dict[str, Any]
    shadow_result_or_error: Dict[str, Any]
    expected_user_visible_result: Any
    expected_difference_class: str
    expected_audit_events: List[str]
    expected_telemetry: List[str]
    expected_redactions: List[str]
    expected_fallback: str


@dataclass
class EvaluationResultRecord:
    case_id: str
    fixture_domain: str
    operating_mode: str
    submission_decision: str
    safety_decision: str
    execution_outcome: str
    legacy_result_fingerprint: str
    user_visible_result_fingerprint: str
    exact_legacy_match: bool
    shadow_submitted: bool
    shadow_completed: bool
    difference_class: str
    fallback: str
    audit_event_types: List[str]
    telemetry_event_types: List[str]
    raw_query_leak_detected: bool


@dataclass
class DeterminismSummary:
    runs_executed: int
    total_fixtures: int
    deterministic_fixture_outcomes: int
    all_runs_identical: bool


@dataclass
class StressProfileSummary:
    queue_capacity: int
    runner_profile: str
    submissions_attempted: int
    submissions_accepted: int
    submissions_dropped: int
    queue_saturation_events: int
    worker_exceptions: int
    worker_survival: bool
    request_thread_waits: int
    retry_count: int
    raw_query_leaks: int


@dataclass
class OverheadSummary:
    mode_name: str
    iterations: int
    absolute_min_ns: int
    absolute_median_ns: float
    absolute_p90_ns: float
    absolute_p95_ns: float
    absolute_p99_ns: float
    absolute_max_ns: int
    incremental_median_ns: float
    incremental_p95_ns: float
    incremental_p99_ns: float
