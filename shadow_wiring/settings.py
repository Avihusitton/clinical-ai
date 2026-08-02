# -*- coding: utf-8 -*-
import os
from dataclasses import dataclass

ALLOWED_MODES = {"LEGACY_ONLY", "SHADOW_COMPARE", "EMERGENCY_DISABLED"}


@dataclass
class ShadowSettings:
    mode: str = "LEGACY_ONLY"
    queue_size: int = 16
    emergency_disable: bool = False

    @classmethod
    def from_env(cls) -> "ShadowSettings":
        raw_mode = os.getenv("CLINICAL_AI_SHADOW_MODE", "LEGACY_ONLY").upper()
        if raw_mode not in ALLOWED_MODES:
            raw_mode = "LEGACY_ONLY"

        try:
            q_size = int(os.getenv("CLINICAL_AI_SHADOW_QUEUE_SIZE", "16"))
        except ValueError:
            q_size = 16

        emg_raw = os.getenv("CLINICAL_AI_EMERGENCY_DISABLE", "false").lower()
        emergency_disable = emg_raw in ("true", "1", "yes")

        if emergency_disable:
            raw_mode = "EMERGENCY_DISABLED"

        return cls(mode=raw_mode, queue_size=q_size, emergency_disable=emergency_disable)


def get_shadow_settings() -> ShadowSettings:
    return ShadowSettings.from_env()
