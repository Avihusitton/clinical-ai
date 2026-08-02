# -*- coding: utf-8 -*-
import time
from shadow_wiring.settings import ShadowSettings
from shadow_wiring.dispatcher import ShadowDispatcher


def test_dispatcher_legacy_only_does_not_queue():
    settings = ShadowSettings(mode="LEGACY_ONLY")
    dispatcher = ShadowDispatcher(settings=settings)
    res = dispatcher.submit("req-1", "What is CBT?", "CBT", "Legacy answer")
    assert res is False
    assert len(dispatcher.audit_sink.get_events()) == 1
    assert dispatcher.audit_sink.get_events()[0]["event_type"] == "AUDIT_MODE_EVALUATED"


def test_dispatcher_shadow_compare_queues_and_runs():
    executed = []

    def mock_runner(task):
        executed.append(task.request_id)
        return {"request_id": task.request_id, "verdict": "OFFICIAL_RAG_SERVED", "difference_class": "AGREEMENT"}

    settings = ShadowSettings(mode="SHADOW_COMPARE", queue_size=16)
    dispatcher = ShadowDispatcher(settings=settings, shadow_runner=mock_runner)

    res = dispatcher.submit("req-2", "Explain exposure therapy", "CBT", "Legacy CBT answer")
    assert res is True

    # Give worker time to process task
    time.sleep(0.2)
    assert "req-2" in executed
    events = dispatcher.audit_sink.get_events()
    compared = [e for e in events if e["event_type"] == "AUDIT_SHADOW_COMPARED"]
    assert len(compared) == 1
    assert compared[0]["payload"]["difference_class"] == "AGREEMENT"


def test_dispatcher_queue_saturation_drops_and_audits():
    settings = ShadowSettings(mode="SHADOW_COMPARE", queue_size=2)
    # Slow runner to hold queue
    def slow_runner(task):
        time.sleep(0.5)
        return {"request_id": task.request_id}

    dispatcher = ShadowDispatcher(settings=settings, shadow_runner=slow_runner)

    # Fill queue
    res1 = dispatcher.submit("req-s1", "Query 1", None, "Ans 1")
    res2 = dispatcher.submit("req-s2", "Query 2", None, "Ans 2")
    res3 = dispatcher.submit("req-s3", "Query 3", None, "Ans 3")
    res4 = dispatcher.submit("req-s4", "Query 4", None, "Ans 4")

    # At least one should be dropped due to queue saturation
    dropped_events = [e for e in dispatcher.audit_sink.get_events() if e["event_type"] == "SHADOW_QUEUE_SATURATED"]
    assert len(dropped_events) > 0
