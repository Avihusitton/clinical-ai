"""
controlled_integration/feature_flags
-------------------------------------
Feature flag evaluator enforcing operating modes and prerequisite control rules.
"""

from .flag_manager import (
    FeatureFlagManager,
    FeatureFlagEvaluator,
    VALID_OPERATING_MODES,
    KNOWN_FLAG_KEYS,
    DEFAULT_FLAGS,
)
from ..exceptions import FeatureFlagError

__all__ = [
    "FeatureFlagManager",
    "FeatureFlagEvaluator",
    "FeatureFlagError",
    "VALID_OPERATING_MODES",
    "KNOWN_FLAG_KEYS",
    "DEFAULT_FLAGS",
]
