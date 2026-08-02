# -*- coding: utf-8 -*-
"""
evaluation/wave9/metrics.py
Computes statistical metrics (percentiles) for absolute latency and incremental overhead.
"""

import math
from typing import List, Dict, Any, Tuple
from .schemas import OverheadSummary


def calculate_percentiles_raw(values: List[int]) -> Tuple[int, float, float, float, float, int]:
    if not values:
        return 0, 0.0, 0.0, 0.0, 0.0, 0

    sorted_vals = sorted(values)
    n = len(sorted_vals)

    def percentile(p: float) -> float:
        k = (n - 1) * p
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return float(sorted_vals[int(k)])
        d0 = sorted_vals[int(f)] * (c - k)
        d1 = sorted_vals[int(c)] * (k - f)
        return float(d0 + d1)

    return (
        sorted_vals[0],
        percentile(0.50),
        percentile(0.90),
        percentile(0.95),
        percentile(0.99),
        sorted_vals[-1]
    )


def build_overhead_summary(
    mode_name: str,
    absolute_values: List[int],
    legacy_baseline_values: List[int]
) -> OverheadSummary:
    abs_min, abs_med, abs_p90, abs_p95, abs_p99, abs_max = calculate_percentiles_raw(absolute_values)

    # Paired iteration deltas for incremental overhead
    if legacy_baseline_values and len(legacy_baseline_values) == len(absolute_values):
        paired_deltas = [abs_v - leg_v for abs_v, leg_v in zip(absolute_values, legacy_baseline_values)]
        _, inc_med, _, inc_p95, inc_p99, _ = calculate_percentiles_raw(paired_deltas)
    else:
        inc_med, inc_p95, inc_p99 = 0.0, 0.0, 0.0

    return OverheadSummary(
        mode_name=mode_name,
        iterations=len(absolute_values),
        absolute_min_ns=abs_min,
        absolute_median_ns=abs_med,
        absolute_p90_ns=abs_p90,
        absolute_p95_ns=abs_p95,
        absolute_p99_ns=abs_p99,
        absolute_max_ns=abs_max,
        incremental_median_ns=inc_med,
        incremental_p95_ns=inc_p95,
        incremental_p99_ns=inc_p99
    )
