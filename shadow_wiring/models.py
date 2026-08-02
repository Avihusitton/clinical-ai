# -*- coding: utf-8 -*-
from dataclasses import dataclass, field
from typing import Optional, Any, Dict, List
import time
import uuid


@dataclass(frozen=True)
class ShadowTaskPayload:
    request_id: str
    redacted_query_hash: str
    modality: Optional[str]
    legacy_result_hash: str
    timestamp: float = field(default_factory=time.time)
    user_id_hash: str = "sha256:anonymous_therapist"


@dataclass(frozen=True)
class ShadowComparisonResult:
    comparison_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    request_id: str = ""
    difference_class: str = "AGREEMENT"
    legacy_latency_ms: float = 0.0
    shadow_latency_ms: float = 0.0
    shadow_verdict: str = "OFFICIAL_RAG_SERVED"
    is_fallback: bool = False
    timestamp: float = field(default_factory=time.time)
    details: Dict[str, Any] = field(default_factory=dict)
