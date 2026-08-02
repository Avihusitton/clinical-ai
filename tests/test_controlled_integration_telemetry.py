"""
tests/test_controlled_integration_telemetry.py
------------------------------------------------
Unit tests for TelemetryRecorder.
Verifies decision metric counters, blocked evidence tracking, summary aggregation, and PII redaction.
"""

import pytest
from controlled_integration.telemetry import TelemetryRecorder
from controlled_integration.security import SecurityPolicy


def test_telemetry_recorder_initial_state():
    """Verify TelemetryRecorder initializes all metric counters to zero."""
    recorder = TelemetryRecorder()
    summary = recorder.get_summary()

    assert summary["total_requests"] == 0
    assert summary["legacy_served_count"] == 0
    assert summary["official_rag_served_count"] == 0
    assert summary["full_pilot_served_count"] == 0
    assert summary["fallback_count"] == 0
    assert summary["blocked_evidence_count"] == 0


def test_telemetry_recorder_decision_counts():
    """Verify TelemetryRecorder increments decision counters accurately."""
    recorder = TelemetryRecorder()

    recorder.record_decision("LEGACY_SERVED")
    recorder.record_decision("OFFICIAL_RAG_SERVED")
    recorder.record_decision("FULL_PILOT_SERVED")
    recorder.record_decision("FULL_PILOT_SERVED")
    recorder.record_decision("FALLBACK_TRIGGERED")

    summary = recorder.get_summary()
    assert summary["total_requests"] == 5
    assert summary["legacy_served_count"] == 1
    assert summary["official_rag_served_count"] == 1
    assert summary["full_pilot_served_count"] == 2
    assert summary["fallback_count"] == 1


def test_telemetry_recorder_blocked_evidence_count():
    """Verify record_blocked_evidence aggregates blocked novelty count."""
    recorder = TelemetryRecorder()

    recorder.record_blocked_evidence(2)
    recorder.record_blocked_evidence(5)

    summary = recorder.get_summary()
    assert summary["blocked_evidence_count"] == 7


def test_telemetry_zero_pii_guarantee():
    """Verify telemetry structures contain zero raw PII patterns."""
    recorder = TelemetryRecorder()
    recorder.record_decision("FULL_PILOT_SERVED")
    recorder.record_blocked_evidence(3)

    summary = recorder.get_summary()
    summary_str = str(summary)

    detected = SecurityPolicy.scan_pii(summary_str)
    assert len(detected) == 0, f"PII detected in telemetry output: {detected}"
