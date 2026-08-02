# -*- coding: utf-8 -*-
"""
tests/test_wave9_synthetic_determinism.py
Unit tests for 3-run fixture evaluation determinism.
"""

import pytest
from evaluation.wave9.fixture_loader import load_shadow_fixtures
from evaluation.wave9.deterministic_runner import run_single_fixture


def test_fixture_outcomes_100_percent_deterministic():
    fixtures, _ = load_shadow_fixtures()
    assert len(fixtures) == 140

    run1 = [run_single_fixture(f) for f in fixtures]
    run2 = [run_single_fixture(f) for f in fixtures]
    run3 = [run_single_fixture(f) for f in fixtures]

    for r1, r2, r3 in zip(run1, run2, run3):
        assert r1.case_id == r2.case_id == r3.case_id
        assert r1.legacy_result_fingerprint == r2.legacy_result_fingerprint == r3.legacy_result_fingerprint
        assert r1.user_visible_result_fingerprint == r2.user_visible_result_fingerprint == r3.user_visible_result_fingerprint
        assert r1.exact_legacy_match == r2.exact_legacy_match == r3.exact_legacy_match
        assert r1.shadow_submitted == r2.shadow_submitted == r3.shadow_submitted
        assert r1.difference_class == r2.difference_class == r3.difference_class
        assert r1.audit_event_types == r2.audit_event_types == r3.audit_event_types
        assert r1.telemetry_event_types == r2.telemetry_event_types == r3.telemetry_event_types
