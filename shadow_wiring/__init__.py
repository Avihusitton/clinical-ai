# -*- coding: utf-8 -*-
"""
shadow_wiring: Off-Critical-Path Shadow Execution Package.
Implements safe, non-blocking shadow retrieval comparison and auditing.
"""

from .settings import ShadowSettings, get_shadow_settings
from .models import ShadowTaskPayload, ShadowComparisonResult
from .redaction import RedactionEngine
from .dispatcher import ShadowDispatcher, get_shadow_dispatcher
from .comparator import ShadowComparator
from .audit_sink import AuditSink
from .telemetry_sink import TelemetrySink

__all__ = [
    "ShadowSettings",
    "get_shadow_settings",
    "ShadowTaskPayload",
    "ShadowComparisonResult",
    "RedactionEngine",
    "ShadowDispatcher",
    "get_shadow_dispatcher",
    "ShadowComparator",
    "AuditSink",
    "TelemetrySink",
]
