# -*- coding: utf-8 -*-
import os
from shadow_wiring.settings import ShadowSettings, get_shadow_settings


def test_default_settings():
    s = ShadowSettings()
    assert s.mode == "LEGACY_ONLY"
    assert s.queue_size == 16
    assert s.emergency_disable is False


def test_env_override():
    os.environ["CLINICAL_AI_SHADOW_MODE"] = "SHADOW_COMPARE"
    os.environ["CLINICAL_AI_SHADOW_QUEUE_SIZE"] = "32"
    s = ShadowSettings.from_env()
    assert s.mode == "SHADOW_COMPARE"
    assert s.queue_size == 32

    # Clean up
    os.environ.pop("CLINICAL_AI_SHADOW_MODE", None)
    os.environ.pop("CLINICAL_AI_SHADOW_QUEUE_SIZE", None)


def test_unknown_mode_fails_closed():
    os.environ["CLINICAL_AI_SHADOW_MODE"] = "INVALID_MODE"
    s = ShadowSettings.from_env()
    assert s.mode == "LEGACY_ONLY"
    os.environ.pop("CLINICAL_AI_SHADOW_MODE", None)


def test_emergency_disable_overrides_shadow_compare():
    os.environ["CLINICAL_AI_SHADOW_MODE"] = "SHADOW_COMPARE"
    os.environ["CLINICAL_AI_EMERGENCY_DISABLE"] = "true"
    s = ShadowSettings.from_env()
    assert s.mode == "EMERGENCY_DISABLED"
    assert s.emergency_disable is True

    os.environ.pop("CLINICAL_AI_SHADOW_MODE", None)
    os.environ.pop("CLINICAL_AI_EMERGENCY_DISABLE", None)
