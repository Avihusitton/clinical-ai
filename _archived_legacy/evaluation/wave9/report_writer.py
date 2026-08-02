# -*- coding: utf-8 -*-
"""
evaluation/wave9/report_writer.py
Writes raw execution and benchmarking artifacts to disk.
"""

import os
import json
from typing import List, Dict, Any
from dataclasses import asdict
from .schemas import EvaluationResultRecord, DeterminismSummary, StressProfileSummary, OverheadSummary


def get_target_dir() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "tests"))


def write_fixture_results(records: List[EvaluationResultRecord]) -> str:
    target_path = os.path.join(get_target_dir(), "WAVE_9_FIXTURE_RESULTS.jsonl")
    with open(target_path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(asdict(r), ensure_ascii=False) + "\n")
    return target_path


def write_determinism_results(summary: DeterminismSummary) -> str:
    target_path = os.path.join(get_target_dir(), "WAVE_9_DETERMINISM_RESULTS.json")
    with open(target_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(asdict(summary), indent=2, ensure_ascii=False))
    return target_path


def write_stress_results(summaries: List[StressProfileSummary]) -> str:
    target_path = os.path.join(get_target_dir(), "WAVE_9_STRESS_RESULTS.json")
    data = [asdict(s) for s in summaries]
    with open(target_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(data, indent=2, ensure_ascii=False))
    return target_path


def write_overhead_results(summaries: List[OverheadSummary]) -> str:
    target_path = os.path.join(get_target_dir(), "WAVE_9_OVERHEAD_RESULTS.json")
    data = [asdict(s) for s in summaries]
    with open(target_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(data, indent=2, ensure_ascii=False))
    return target_path


def write_redaction_results(redaction_data: Dict[str, Any]) -> str:
    target_path = os.path.join(get_target_dir(), "WAVE_9_REDACTION_RESULTS.json")
    with open(target_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(redaction_data, indent=2, ensure_ascii=False))
    return target_path
