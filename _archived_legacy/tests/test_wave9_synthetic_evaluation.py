# -*- coding: utf-8 -*-
"""
tests/test_wave9_synthetic_evaluation.py
Unit and integration tests for Wave 9 evaluation harness and fixture accounting.
"""

import pytest
from evaluation.wave9.fixture_loader import load_shadow_fixtures, load_negative_redaction_fixtures
from evaluation.wave9.evaluation_harness import run_evaluation_harness


def test_fixture_loading_and_accounting():
    fixtures, domain_counts = load_shadow_fixtures()
    neg_cases = load_negative_redaction_fixtures()

    assert len(fixtures) == 140
    assert len(neg_cases) == 60
    assert sum(domain_counts.values()) == 140

    # Ensure all domains are accounted for
    expected_domains = ["shadow_disabled", "agreement", "controlled_difference", "failure_and_timeout", "security_and_redaction", "rollback_and_emergency", "israeli_pii"]
    for d in expected_domains:
        assert d in domain_counts
        assert domain_counts[d] > 0


def test_run_evaluation_harness_pass():
    res = run_evaluation_harness()
    assert res["harness_result"] == "PASS"
    assert res["fixtures_loaded"] == 140
    assert res["fixtures_accounted_for"] == 140
    assert res["legacy_exact_matches"] == 140
    assert res["user_visible_shadow_outputs"] == 0
    assert res["raw_query_leaks"] == 0
    assert res["redaction"]["israeli_pii_cases_queued"] == 0
