"""
tests/test_controlled_integration_flags.py
--------------------------------------------
Unit tests for FeatureFlagEvaluator and feature flag error handling.
Verifies all 5 operating modes, prerequisite rules ERR_01-ERR_04, and invalid flag combinations.
"""

import pytest
from controlled_integration.feature_flags import FeatureFlagEvaluator, VALID_OPERATING_MODES
from controlled_integration.exceptions import FeatureFlagError


def test_default_operating_mode():
    """Verify default operating mode is LEGACY_ONLY."""
    evaluator = FeatureFlagEvaluator()
    assert evaluator.default_mode == "LEGACY_ONLY"
    mode, flags = evaluator.evaluate_mode()
    assert mode == "LEGACY_ONLY"
    assert flags["official_retrieval_enabled"] is False
    assert flags["audit_logging_enabled"] is True


def test_all_valid_operating_modes():
    """Verify all 5 valid operating modes are recognized."""
    expected_modes = {
        "LEGACY_ONLY",
        "SHADOW_COMPARE",
        "OFFICIAL_RETRIEVAL_ONLY",
        "THERAPIST_PILOT",
        "EMERGENCY_DISABLED",
    }
    assert VALID_OPERATING_MODES == expected_modes

    evaluator = FeatureFlagEvaluator()
    for mode_name in expected_modes:
        mode, _ = evaluator.evaluate_mode(mode_override=mode_name)
        assert mode == mode_name


def test_rule_err_01_emergency_disabled_forces_subflags_false():
    """Rule ERR_01: EMERGENCY_DISABLED forces all sub-flags to False."""
    evaluator = FeatureFlagEvaluator()
    overrides = {
        "official_retrieval_enabled": True,
        "gate_b_reasoning_enabled": True,
        "audit_logging_enabled": True,
    }
    mode, flags = evaluator.evaluate_mode(
        mode_override="EMERGENCY_DISABLED",
        flag_overrides=overrides,
    )
    assert mode == "EMERGENCY_DISABLED"
    for k, v in flags.items():
        assert v is False, f"Flag {k} should be False in EMERGENCY_DISABLED mode"


def test_rule_err_02_legacy_only_forces_subflags_false():
    """Rule ERR_02: LEGACY_ONLY forces feature sub-flags false except audit logging."""
    evaluator = FeatureFlagEvaluator()
    mode, flags = evaluator.evaluate_mode(mode_override="LEGACY_ONLY")
    assert mode == "LEGACY_ONLY"
    assert flags["official_retrieval_enabled"] is False
    assert flags["gate_b_reasoning_enabled"] is False
    assert flags["gate_c_novelty_enabled"] is False
    assert flags["gate_d_formatting_enabled"] is False
    assert flags["audit_logging_enabled"] is True


def test_rule_err_03_gate_b_requires_official_retrieval():
    """Rule ERR_03: gate_b_reasoning_enabled requires official_retrieval_enabled=True."""
    evaluator = FeatureFlagEvaluator()
    with pytest.raises(FeatureFlagError) as exc_info:
        evaluator.evaluate_mode(
            mode_override="THERAPIST_PILOT",
            flag_overrides={
                "gate_b_reasoning_enabled": True,
                "official_retrieval_enabled": False,
            },
        )
    assert "gate_b_reasoning_enabled requires official_retrieval_enabled=True" in str(exc_info.value)


def test_rule_err_04_gate_c_requires_gate_b_and_audit():
    """Rule ERR_04: gate_c_novelty_enabled requires Gate B reasoning and audit logging."""
    evaluator = FeatureFlagEvaluator()
    
    # Missing Gate B
    with pytest.raises(FeatureFlagError):
        evaluator.evaluate_mode(
            mode_override="THERAPIST_PILOT",
            flag_overrides={
                "gate_c_novelty_enabled": True,
                "gate_b_reasoning_enabled": False,
                "audit_logging_enabled": True,
            },
        )

    # Missing Audit Logging
    with pytest.raises(FeatureFlagError):
        evaluator.evaluate_mode(
            mode_override="THERAPIST_PILOT",
            flag_overrides={
                "gate_c_novelty_enabled": True,
                "gate_b_reasoning_enabled": True,
                "audit_logging_enabled": False,
            },
        )


def test_invalid_operating_mode_raises_error():
    """Verify unknown operating mode raises FeatureFlagError."""
    evaluator = FeatureFlagEvaluator()
    with pytest.raises(FeatureFlagError) as exc_info:
        evaluator.evaluate_mode(mode_override="INVALID_UNSUPPORTED_MODE")
    assert "Unknown operating mode: 'INVALID_UNSUPPORTED_MODE'" in str(exc_info.value)


def test_valid_flag_overrides_in_therapist_pilot():
    """Verify valid flag overrides work in THERAPIST_PILOT mode."""
    evaluator = FeatureFlagEvaluator()
    valid_flags = {
        "official_retrieval_enabled": True,
        "gate_b_reasoning_enabled": True,
        "gate_c_novelty_enabled": True,
        "audit_logging_enabled": True,
    }
    mode, flags = evaluator.evaluate_mode(
        mode_override="THERAPIST_PILOT",
        flag_overrides=valid_flags,
    )
    assert mode == "THERAPIST_PILOT"
    for k, v in valid_flags.items():
        assert flags[k] == v
