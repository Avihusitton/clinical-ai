"""
controlled_integration/fallback
--------------------------------
Circuit breaker and fail-closed fallback handler routing to legacy retrieval baseline.
"""

from .fallback_handler import FallbackHandler

__all__ = ["FallbackHandler"]
