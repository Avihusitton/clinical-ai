"""
controlled_integration.adapters
--------------------------------
Isolated unidirectional adapters for each pipeline Gate and legacy retrieval.
"""

from .gate_b_adapter import GateBAdapter
from .gate_c_adapter import GateCAdapter
from .boundary_adapter import BoundaryAdapter
from .gate_d_adapter import GateDAdapter
from .legacy_adapter import LegacyRetrievalAdapter

__all__ = [
    "GateBAdapter",
    "GateCAdapter",
    "BoundaryAdapter",
    "GateDAdapter",
    "LegacyRetrievalAdapter",
]
