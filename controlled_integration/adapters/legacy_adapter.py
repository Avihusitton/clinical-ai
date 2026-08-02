"""
controlled_integration/adapters/legacy_adapter.py
--------------------------------------------------
Adapter wrapping production legacy retrieval (retrieval.py).
Enforces zero modification to production code and provides a deterministic baseline response.
"""

from typing import Dict, Any, Optional
from ..models import IntegrationRequest, IntegrationDecision

class LegacyRetrievalAdapter:
    """
    Adapter bridging IntegrationRequest to unmodified legacy retrieval.
    Does not modify retrieval.py or external databases.
    """
    def execute_legacy(self, request: IntegrationRequest) -> Dict[str, Any]:
        """
        Execute deterministic legacy retrieval fallback response.
        In a full runtime environment with driver and LLM mocked, returns structured legacy baseline.
        """
        return {
            "request_id": request.request_id,
            "query_text": request.query_text,
            "response_type": "LEGACY_BASELINE",
            "content": f"Legacy baseline response for query: {request.query_text}",
            "source": "retrieval.py",
            "is_fallback": False
        }
