"""
tests/test_controlled_integration_audit.py
--------------------------------------------
Unit tests for AuditLogger engine and IntegrationAuditEvent lifecycle.
Verifies immutable event logging, structured details, and request-id event queries.
"""

import pytest
import uuid
from controlled_integration.audit import AuditLogger
from controlled_integration.models import IntegrationAuditEvent


def test_audit_logger_log_event():
    """Verify log_event creates and stores an IntegrationAuditEvent."""
    logger = AuditLogger()
    req_id = f"req_{uuid.uuid4()}"
    sess_id = f"sess_{uuid.uuid4()}"

    event = logger.log_event(
        event_type="INTEGRATION_REQUEST_RECEIVED",
        request_id=req_id,
        session_id=sess_id,
        details={"query_length": 45, "environment": "internal_pilot"},
    )

    assert isinstance(event, IntegrationAuditEvent)
    assert event.event_type == "INTEGRATION_REQUEST_RECEIVED"
    assert event.request_id == req_id
    assert event.session_id == sess_id
    assert event.details["query_length"] == 45
    assert len(logger.events) == 1


def test_audit_logger_get_events_for_request():
    """Verify get_events_for_request filters events accurately by request_id."""
    logger = AuditLogger()
    target_req = "req_target_123"
    other_req = "req_other_999"

    logger.log_event("EVENT_A", target_req, "sess_1", {"step": 1})
    logger.log_event("EVENT_B", other_req, "sess_2", {"step": 1})
    logger.log_event("EVENT_C", target_req, "sess_1", {"step": 2})

    target_events = logger.get_events_for_request(target_req)
    assert len(target_events) == 2
    assert [e.event_type for e in target_events] == ["EVENT_A", "EVENT_C"]

    other_events = logger.get_events_for_request(other_req)
    assert len(other_events) == 1
    assert other_events[0].event_type == "EVENT_B"

    empty_events = logger.get_events_for_request("non_existent_req")
    assert len(empty_events) == 0


def test_audit_logger_event_immutability():
    """Verify IntegrationAuditEvent objects in audit log are immutable."""
    logger = AuditLogger()
    event = logger.log_event(
        event_type="SECURITY_EVENT",
        request_id="req_immut",
        session_id="sess_immut",
        details={"status": "PASSED"},
    )

    with pytest.raises((TypeError, AttributeError, Exception)):
        event.event_type = "MODIFIED_EVENT"  # type: ignore
