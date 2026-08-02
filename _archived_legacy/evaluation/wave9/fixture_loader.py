# -*- coding: utf-8 -*-
"""
evaluation/wave9/fixture_loader.py
Loads frozen synthetic test fixtures for Wave 9 evaluation and performs domain accounting.
"""

import os
import json
from typing import List, Dict, Any, Tuple
from .schemas import FixtureRecord


def get_fixture_paths() -> Tuple[str, str]:
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    shadow_cases_path = os.path.join(base_dir, "tests", "fixtures", "shadow_wiring", "shadow_cases.jsonl")
    neg_cases_path = os.path.join(base_dir, "tests", "fixtures", "shadow_wiring", "redaction_negative_cases.jsonl")
    return shadow_cases_path, neg_cases_path


def load_shadow_fixtures() -> Tuple[List[FixtureRecord], Dict[str, int]]:
    shadow_path, _ = get_fixture_paths()
    if not os.path.exists(shadow_path):
        raise FileNotFoundError(f"Shadow fixtures file not found: {shadow_path}")

    fixtures: List[FixtureRecord] = []
    domain_counts: Dict[str, int] = {
        "shadow_disabled": 0,
        "agreement": 0,
        "controlled_difference": 0,
        "failure_and_timeout": 0,
        "security_and_redaction": 0,
        "rollback_and_emergency": 0,
        "israeli_pii": 0
    }

    with open(shadow_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            data = json.loads(line)
            cid = data.get("case_id", "")

            # Classify domain based on case ID prefix or metadata
            if "SHD-ISR" in cid:
                domain = "israeli_pii"
            elif "SHD-DIS" in cid:
                domain = "shadow_disabled"
            elif "SHD-AGR" in cid:
                domain = "agreement"
            elif "SHD-DIF" in cid:
                domain = "controlled_difference"
            elif "SHD-ERR" in cid or "SHD-FLT" in cid or "SHD-TO" in cid:
                domain = "failure_and_timeout"
            elif "SHD-SEC" in cid or "SHD-RED" in cid:
                domain = "security_and_redaction"
            elif "SHD-EMG" in cid or "SHD-RLB" in cid:
                domain = "rollback_and_emergency"
            else:
                domain = "security_and_redaction"

            domain_counts[domain] = domain_counts.get(domain, 0) + 1

            rec = FixtureRecord(
                case_id=cid,
                domain=domain,
                legacy_request=data.get("legacy_request", {}),
                legacy_result=data.get("legacy_result"),
                shadow_flag_state=data.get("shadow_flag_state", {}),
                shadow_input=data.get("shadow_input", {}),
                shadow_result_or_error=data.get("shadow_result_or_error", {}),
                expected_user_visible_result=data.get("expected_user_visible_result"),
                expected_difference_class=data.get("expected_difference_class", "AGREEMENT"),
                expected_audit_events=data.get("expected_audit_events", []),
                expected_telemetry=data.get("expected_telemetry", []),
                expected_redactions=data.get("expected_redactions", []),
                expected_fallback=data.get("expected_fallback", "NONE")
            )
            fixtures.append(rec)

    return fixtures, domain_counts


def load_negative_redaction_fixtures() -> List[Dict[str, Any]]:
    _, neg_path = get_fixture_paths()
    if not os.path.exists(neg_path):
        raise FileNotFoundError(f"Negative redaction cases file not found: {neg_path}")

    cases: List[Dict[str, Any]] = []
    with open(neg_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                cases.append(json.loads(line))
    return cases
