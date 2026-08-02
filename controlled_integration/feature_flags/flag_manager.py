"""
controlled_integration/feature_flags/flag_manager.py
------------------------------------------------------
Feature flag manager enforcing 5 operating modes, flag validation, emergency override, and fail-closed rules.
"""

import os
from typing import Dict, Any, Tuple, Optional, Set
from ..exceptions import FeatureFlagError

VALID_OPERATING_MODES: Set[str] = {
    "LEGACY_ONLY",
    "SHADOW_COMPARE",
    "OFFICIAL_RETRIEVAL_ONLY",
    "THERAPIST_PILOT",
    "EMERGENCY_DISABLED",
}

KNOWN_FLAG_KEYS: Set[str] = {
    "official_retrieval_enabled",
    "gate_b_reasoning_enabled",
    "gate_c_novelty_enabled",
    "gate_d_formatting_enabled",
    "audit_logging_enabled",
    "shadow_comparison_enabled",
    "therapist_pilot_access_enabled",
}

DEFAULT_FLAGS: Dict[str, Dict[str, bool]] = {
    "LEGACY_ONLY": {
        "official_retrieval_enabled": False,
        "gate_b_reasoning_enabled": False,
        "gate_c_novelty_enabled": False,
        "gate_d_formatting_enabled": False,
        "audit_logging_enabled": True,
        "shadow_comparison_enabled": False,
        "therapist_pilot_access_enabled": False,
    },
    "SHADOW_COMPARE": {
        "official_retrieval_enabled": True,
        "gate_b_reasoning_enabled": True,
        "gate_c_novelty_enabled": False,
        "gate_d_formatting_enabled": False,
        "audit_logging_enabled": True,
        "shadow_comparison_enabled": True,
        "therapist_pilot_access_enabled": False,
    },
    "OFFICIAL_RETRIEVAL_ONLY": {
        "official_retrieval_enabled": True,
        "gate_b_reasoning_enabled": False,
        "gate_c_novelty_enabled": False,
        "gate_d_formatting_enabled": False,
        "audit_logging_enabled": True,
        "shadow_comparison_enabled": False,
        "therapist_pilot_access_enabled": False,
    },
    "THERAPIST_PILOT": {
        "official_retrieval_enabled": True,
        "gate_b_reasoning_enabled": True,
        "gate_c_novelty_enabled": True,
        "gate_d_formatting_enabled": True,
        "audit_logging_enabled": True,
        "shadow_comparison_enabled": False,
        "therapist_pilot_access_enabled": True,
    },
    "EMERGENCY_DISABLED": {
        "official_retrieval_enabled": False,
        "gate_b_reasoning_enabled": False,
        "gate_c_novelty_enabled": False,
        "gate_d_formatting_enabled": False,
        "audit_logging_enabled": True,
        "shadow_comparison_enabled": False,
        "therapist_pilot_access_enabled": False,
    },
}

class FeatureFlagManager:
    """
    Evaluates feature flags and operating modes against control rules ERR_01 - ERR_07.
    """
    def __init__(self, default_mode: str = "LEGACY_ONLY"):
        self.default_mode = default_mode if default_mode in VALID_OPERATING_MODES else "LEGACY_ONLY"

    def is_emergency_disabled(self) -> bool:
        """Checks environment variables and sentinel file for emergency disable."""
        env_val = os.environ.get("CLINICAL_AI_EMERGENCY_DISABLE", "").strip().lower()
        if env_val in ("true", "1", "yes"):
            return True
        mode_env = os.environ.get("CLINICAL_AI_OPERATING_MODE", "").strip()
        if mode_env == "EMERGENCY_DISABLED":
            return True
        sentinel_path = os.path.join("data", "EMERGENCY_DISABLE.sentinel")
        if os.path.exists(sentinel_path):
            return True
        return False

    def evaluate_mode(
        self,
        mode_override: Optional[str] = None,
        flag_overrides: Optional[Dict[str, bool]] = None,
        raise_on_error: bool = True
    ) -> Tuple[str, Dict[str, bool]]:
        """
        Determines active operating mode and validated flags map.
        Fails closed to LEGACY_ONLY on invalid combinations or unknown keys unless raise_on_error=True.
        """
        # Step 1: Emergency check
        if self.is_emergency_disabled() or mode_override == "EMERGENCY_DISABLED":
            flags = dict(DEFAULT_FLAGS["EMERGENCY_DISABLED"])
            for k in flags:
                flags[k] = False
            return "EMERGENCY_DISABLED", flags

        requested_mode = mode_override or os.environ.get("CLINICAL_AI_OPERATING_MODE") or self.default_mode
        overrides = flag_overrides or {}

        # Rule ERR_07 / Invalid mode check:
        if requested_mode not in VALID_OPERATING_MODES:
            if raise_on_error:
                raise FeatureFlagError(f"Unknown operating mode: '{requested_mode}'", code="ERR_FF_03", details={"mode": requested_mode})
            return "LEGACY_ONLY", dict(DEFAULT_FLAGS["LEGACY_ONLY"])

        # Check for unknown flag keys (ERR_07)
        unknown_keys = set(overrides.keys()) - KNOWN_FLAG_KEYS
        if unknown_keys:
            if raise_on_error:
                raise FeatureFlagError(f"Unknown feature flag key(s): {unknown_keys}", code="ERR_FF_03", details={"unknown_keys": list(unknown_keys)})
            return "LEGACY_ONLY", dict(DEFAULT_FLAGS["LEGACY_ONLY"])

        # Merge base mode flags with overrides
        active_flags = dict(DEFAULT_FLAGS.get(requested_mode, DEFAULT_FLAGS["LEGACY_ONLY"]))
        active_flags.update(overrides)

        # Rule ERR_01: EMERGENCY_DISABLED forces sub-flags false
        if requested_mode == "EMERGENCY_DISABLED":
            for k in active_flags:
                if k != "audit_logging_enabled":
                    active_flags[k] = False
            return "EMERGENCY_DISABLED", active_flags

        # Rule ERR_02: LEGACY_ONLY mode isolation
        if requested_mode == "LEGACY_ONLY":
            for k in active_flags:
                if k != "audit_logging_enabled":
                    if active_flags[k] is True:
                        if raise_on_error:
                            raise FeatureFlagError(f"Flag '{k}' cannot be True in LEGACY_ONLY mode", code="ERR_FF_02")
                        return "LEGACY_ONLY", dict(DEFAULT_FLAGS["LEGACY_ONLY"])
            return "LEGACY_ONLY", active_flags

        # Rule ERR_03: Gate B requires Official Retrieval
        if active_flags.get("gate_b_reasoning_enabled") and not active_flags.get("official_retrieval_enabled"):
            if raise_on_error:
                raise FeatureFlagError("gate_b_reasoning_enabled requires official_retrieval_enabled=True", code="ERR_FF_02")
            return "LEGACY_ONLY", dict(DEFAULT_FLAGS["LEGACY_ONLY"])

        # Rule ERR_04: Gate C requires Gate B and Audit Logging
        if active_flags.get("gate_c_novelty_enabled") and not (active_flags.get("gate_b_reasoning_enabled") and active_flags.get("audit_logging_enabled")):
            if raise_on_error:
                raise FeatureFlagError("gate_c_novelty_enabled requires Gate B reasoning and audit logging", code="ERR_FF_02")
            return "LEGACY_ONLY", dict(DEFAULT_FLAGS["LEGACY_ONLY"])

        # Rule ERR_05: Gate D requires Gate B
        if active_flags.get("gate_d_formatting_enabled") and not active_flags.get("gate_b_reasoning_enabled"):
            if raise_on_error:
                raise FeatureFlagError("gate_d_formatting_enabled requires gate_b_reasoning_enabled=True", code="ERR_FF_02")
            return "LEGACY_ONLY", dict(DEFAULT_FLAGS["LEGACY_ONLY"])

        # Rule ERR_06: Therapist Pilot requires mode THERAPIST_PILOT and audit logging
        if active_flags.get("therapist_pilot_access_enabled") and not (requested_mode == "THERAPIST_PILOT" and active_flags.get("audit_logging_enabled")):
            if raise_on_error:
                raise FeatureFlagError("therapist_pilot_access_enabled requires THERAPIST_PILOT mode and audit logging", code="ERR_FF_02")
            return "LEGACY_ONLY", dict(DEFAULT_FLAGS["LEGACY_ONLY"])

        return requested_mode, active_flags

# Maintain FeatureFlagEvaluator alias for backward compatibility
FeatureFlagEvaluator = FeatureFlagManager
