# Overhead Methodology & Benchmark Report — Wave 9.1

## Methodology

Local request-path overhead is measured across 1,000 iterations per mode using high-resolution monotonic timestamps (`time.perf_counter_ns()`). Warmup iterations (100 runs) are excluded from statistics.

Both **Absolute Latency** and **Paired Incremental Overhead** (relative to `LEGACY_ONLY` baseline for each iteration) are reported separately.

> [!NOTE]
> Measurements are local synthetic microbenchmarks and do not predict production latency.

## Measurement Accounting

1. **`LEGACY_ONLY` baseline**: Baseline request execution.
2. **`SHADOW_COMPARE` (fast runner)**: Asynchronous task dispatch with fast worker execution.
3. **`SHADOW_COMPARE` (pre-blocked worker)**: Task dispatch when worker thread is blocked.
4. **`SHADOW_COMPARE` (full queue)**: Task dispatch when queue capacity is saturated (drop path).

---
*Generated for Wave 9.1 Evaluation Integrity Repair.*
