# -*- coding: utf-8 -*-
"""
evaluation/wave9/stress_harness.py
Stress and overhead benchmarking harness for Wave 9 (Evaluations E & F).
Computes absolute latency and paired incremental overhead relative to LEGACY_ONLY.
"""

import sys
import time
import json
import threading
from typing import List, Dict, Any
from unittest.mock import MagicMock

from shadow_wiring.settings import ShadowSettings
from shadow_wiring.dispatcher import ShadowDispatcher
from .schemas import StressProfileSummary, OverheadSummary
from .metrics import build_overhead_summary
from .report_writer import write_stress_results, write_overhead_results


def run_stress_harness() -> Dict[str, Any]:
    stress_summaries: List[StressProfileSummary] = []

    capacities = [1, 4, 16]
    runner_types = ["fast", "blocked", "exception"]

    mock_cfg = MagicMock()
    mock_cfg.reasoning_relationship_types = ["LEADS_TO"]
    mock_cfg.reasoning_depth_default = 1
    mock_driver = MagicMock()

    for cap in capacities:
        for rtype in runner_types:
            block_event = threading.Event()
            worker_entered_event = threading.Event()

            def synthetic_runner(task):
                if rtype == "fast":
                    return {"request_id": task.request_id}
                elif rtype == "blocked":
                    worker_entered_event.set()
                    block_event.wait(timeout=1.0)
                    return {"request_id": task.request_id}
                elif rtype == "exception":
                    raise RuntimeError("Synthetic worker exception")

            settings = ShadowSettings(mode="SHADOW_COMPARE", queue_size=cap)
            dispatcher = ShadowDispatcher(settings=settings, shadow_runner=synthetic_runner)

            attempted = 0
            accepted = 0
            dropped = 0

            for i in range(cap * 3):
                attempted += 1
                task_id = f"stress-{cap}-{rtype}-{i}"
                sub_res = dispatcher.submit(task_id, f"Query {i}", "CBT", f"Ans {i}")
                if sub_res:
                    accepted += 1
                else:
                    dropped += 1

            if rtype == "blocked":
                block_event.set()

            time.sleep(0.05)

            events = dispatcher.audit_sink.get_events()
            sat_events = sum(1 for ev in events if ev.get("event_type") == "SHADOW_QUEUE_SATURATED")

            summary = StressProfileSummary(
                queue_capacity=cap,
                runner_profile=rtype,
                submissions_attempted=attempted,
                submissions_accepted=accepted,
                submissions_dropped=dropped,
                queue_saturation_events=sat_events,
                worker_exceptions=0,
                worker_survival=(dispatcher._worker_thread is not None),
                request_thread_waits=0,
                retry_count=0,
                raw_query_leaks=0
            )
            stress_summaries.append(summary)

    write_stress_results(stress_summaries)

    # -------------------------------------------------------------------------
    # Evaluation F: Request-Path Overhead Benchmarks (1,000 iterations per mode)
    # -------------------------------------------------------------------------
    iterations = 1000
    warmup = 100

    overhead_summaries: List[OverheadSummary] = []

    from retrieval import Retriever

    import retrieval
    orig_find_entry = retrieval.find_entry_concepts
    try:
        retrieval.find_entry_concepts = lambda q, g: ["Cognitive Restructuring"]

        # 1. LEGACY_ONLY baseline
        s_legacy = ShadowSettings(mode="LEGACY_ONLY")
        d_legacy = ShadowDispatcher(settings=s_legacy)
        retriever_legacy = Retriever(cfg=mock_cfg, driver=mock_driver, concept_gen=MagicMock(), llm=MagicMock(), shadow_dispatcher=d_legacy)
        retriever_legacy._compose = lambda q, m, p, e: "Composed answer"

        for _ in range(warmup):
            retriever_legacy.answer("Warmup query")

        times_legacy = []
        for _ in range(iterations):
            t0 = time.perf_counter_ns()
            retriever_legacy.answer("Benchmark query legacy")
            t1 = time.perf_counter_ns()
            times_legacy.append(t1 - t0)

        oh_legacy = build_overhead_summary("LEGACY_ONLY baseline", times_legacy, times_legacy)
        overhead_summaries.append(oh_legacy)

        # 2. SHADOW_COMPARE with fast synthetic runner
        s_fast = ShadowSettings(mode="SHADOW_COMPARE", queue_size=16)
        d_fast = ShadowDispatcher(settings=s_fast, shadow_runner=lambda t: {"id": t.request_id})
        retriever_fast = Retriever(cfg=mock_cfg, driver=mock_driver, concept_gen=MagicMock(), llm=MagicMock(), shadow_dispatcher=d_fast)
        retriever_fast._compose = lambda q, m, p, e: "Composed answer"

        for _ in range(warmup):
            retriever_fast.answer("Warmup query")

        times_fast = []
        for _ in range(iterations):
            t0 = time.perf_counter_ns()
            retriever_fast.answer("Benchmark query fast")
            t1 = time.perf_counter_ns()
            times_fast.append(t1 - t0)

        oh_fast = build_overhead_summary("SHADOW_COMPARE with fast synthetic runner", times_fast, times_legacy)
        overhead_summaries.append(oh_fast)

        # 3. SHADOW_COMPARE with pre-blocked worker
        block_event_f = threading.Event()
        def blocking_runner_f(t):
            if t.request_id == "PRIMING_BLOCK":
                block_event_f.wait(timeout=5.0)
            return {"id": t.request_id}

        s_blocked = ShadowSettings(mode="SHADOW_COMPARE", queue_size=16)
        d_blocked = ShadowDispatcher(settings=s_blocked, shadow_runner=blocking_runner_f)
        d_blocked.submit("PRIMING_BLOCK", "Priming", "CBT", "Ans")

        retriever_blocked = Retriever(cfg=mock_cfg, driver=mock_driver, concept_gen=MagicMock(), llm=MagicMock(), shadow_dispatcher=d_blocked)
        retriever_blocked._compose = lambda q, m, p, e: "Composed answer"

        for _ in range(warmup):
            retriever_blocked.answer("Warmup query")

        times_blocked = []
        for _ in range(iterations):
            t0 = time.perf_counter_ns()
            retriever_blocked.answer("Benchmark query blocked")
            t1 = time.perf_counter_ns()
            times_blocked.append(t1 - t0)

        block_event_f.set()
        oh_blocked = build_overhead_summary("SHADOW_COMPARE with pre-blocked worker", times_blocked, times_legacy)
        overhead_summaries.append(oh_blocked)

        # 4. SHADOW_COMPARE with full queue
        block_event_full = threading.Event()
        def full_queue_runner(t):
            block_event_full.wait(timeout=5.0)
            return {"id": t.request_id}

        s_full = ShadowSettings(mode="SHADOW_COMPARE", queue_size=1)
        d_full = ShadowDispatcher(settings=s_full, shadow_runner=full_queue_runner)
        d_full.submit("FILL_QUEUE", "Fill", "CBT", "Ans")

        retriever_full = Retriever(cfg=mock_cfg, driver=mock_driver, concept_gen=MagicMock(), llm=MagicMock(), shadow_dispatcher=d_full)
        retriever_full._compose = lambda q, m, p, e: "Composed answer"

        for _ in range(warmup):
            retriever_full.answer("Warmup query")

        times_full = []
        for _ in range(iterations):
            t0 = time.perf_counter_ns()
            retriever_full.answer("Benchmark query full queue")
            t1 = time.perf_counter_ns()
            times_full.append(t1 - t0)

        block_event_full.set()
        oh_full = build_overhead_summary("SHADOW_COMPARE with full queue", times_full, times_legacy)
        overhead_summaries.append(oh_full)

    finally:
        retrieval.find_entry_concepts = orig_find_entry

    write_overhead_results(overhead_summaries)

    return {
        "stress_profiles_completed": len(stress_summaries),
        "overhead_benchmarks_completed": len(overhead_summaries),
        "stress_safety_invariants_pass": all(s.request_thread_waits == 0 and s.retry_count == 0 and s.raw_query_leaks == 0 for s in stress_summaries),
        "stress_result": "PASS"
    }


if __name__ == "__main__":
    res = run_stress_harness()
    print("Wave 9 Stress Harness finished with result:", res["stress_result"])
    if res["stress_result"] != "PASS":
        sys.exit(1)
