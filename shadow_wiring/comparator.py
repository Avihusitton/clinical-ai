# -*- coding: utf-8 -*-
from typing import Dict, Any
from .models import ShadowComparisonResult

DIFFERENCE_CLASSES = {
    "AGREEMENT",
    "LEGACY_ONLY_EVIDENCE",
    "SHADOW_ONLY_REVIEWED_EVIDENCE",
    "RANKING_DIFFERENCE",
    "UNCERTAINTY_DIFFERENCE",
    "SAFETY_BLOCK_DIFFERENCE",
    "FALLBACK_TRIGGERED",
    "SHADOW_ERROR",
    "SHADOW_TIMEOUT",
}


class ShadowComparator:
    @staticmethod
    def classify(legacy_result_hash: str, shadow_result: Dict[str, Any]) -> ShadowComparisonResult:
        request_id = shadow_result.get("request_id", "")
        error = shadow_result.get("error")

        if error == "PII_REJECTED" or shadow_result.get("pii_detected"):
            return ShadowComparisonResult(
                request_id=request_id,
                difference_class="SAFETY_BLOCK_DIFFERENCE",
                is_fallback=True,
                details={"reason": "PII_REJECTED"}
            )

        if error == "SHADOW_TIMEOUT":
            return ShadowComparisonResult(
                request_id=request_id,
                difference_class="SHADOW_TIMEOUT",
                is_fallback=True,
                details={"reason": "SHADOW_TIMEOUT"}
            )

        if error:
            return ShadowComparisonResult(
                request_id=request_id,
                difference_class="SHADOW_ERROR",
                is_fallback=True,
                details={"error": str(error)}
            )

        diff_class = shadow_result.get("difference_class", "AGREEMENT")
        if diff_class not in DIFFERENCE_CLASSES:
            diff_class = "AGREEMENT"

        return ShadowComparisonResult(
            request_id=request_id,
            difference_class=diff_class,
            shadow_verdict=shadow_result.get("verdict", "OFFICIAL_RAG_SERVED"),
            is_fallback=shadow_result.get("is_fallback", False),
            details=shadow_result.get("details", {})
        )
