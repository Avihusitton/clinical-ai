# -*- coding: utf-8 -*-
from unittest.mock import MagicMock
import threading
import time
import pytest
from retrieval import Retriever
from shadow_wiring.settings import ShadowSettings
from shadow_wiring.dispatcher import ShadowDispatcher


def test_retriever_legacy_flow_unaffected():
    mock_cfg = MagicMock()
    mock_cfg.reasoning_relationship_types = ["LEADS_TO"]
    mock_cfg.reasoning_depth_default = 1
    mock_driver = MagicMock()
    mock_concept_gen = MagicMock()

    r = Retriever(cfg=mock_cfg, driver=mock_driver, concept_gen=mock_concept_gen, llm=MagicMock())
    mock_concept_gen.find_candidates.return_value = []

    res = r.answer("שאלה לא מוכרת")
    assert "אין מספיק מידע בגרף" in res


def test_retriever_shadow_submission_non_blocking_event_sync():
    mock_cfg = MagicMock()
    mock_cfg.reasoning_relationship_types = ["LEADS_TO"]
    mock_cfg.reasoning_depth_default = 1
    mock_driver = MagicMock()
    mock_concept_gen = MagicMock()

    hold_event = threading.Event()

    def blocked_runner(task):
        hold_event.wait(timeout=2.0)
        return {"request_id": task.request_id}

    settings = ShadowSettings(mode="SHADOW_COMPARE")
    dispatcher = ShadowDispatcher(settings=settings, shadow_runner=blocked_runner)

    r = Retriever(cfg=mock_cfg, driver=mock_driver, concept_gen=mock_concept_gen, llm=MagicMock(), shadow_dispatcher=dispatcher)
    mock_concept_gen.find_candidates.return_value = []

    start = time.time()
    res = r.answer("שאלה ללא מושגים")
    elapsed = time.time() - start

    assert elapsed < 0.2
    assert "אין מספיק מידע בגרף" in res

    hold_event.set()


test_retriever_shadow_submission_non_blocking = test_retriever_shadow_submission_non_blocking_event_sync


def test_retriever_shadow_exception_suppressed():
    mock_cfg = MagicMock()
    mock_cfg.reasoning_relationship_types = ["LEADS_TO"]
    mock_cfg.reasoning_depth_default = 1
    mock_driver = MagicMock()
    mock_concept_gen = MagicMock()

    broken_dispatcher = MagicMock()
    broken_dispatcher.submit.side_effect = RuntimeError("Broken dispatcher!")

    r = Retriever(cfg=mock_cfg, driver=mock_driver, concept_gen=mock_concept_gen, llm=MagicMock(), shadow_dispatcher=broken_dispatcher)
    mock_concept_gen.find_candidates.return_value = []

    res = r.answer("שאלה לבדיקה")
    assert "אין מספיק מידע בגרף" in res


def test_retriever_shadow_sentinel_not_exposed():
    mock_cfg = MagicMock()
    mock_cfg.reasoning_relationship_types = ["LEADS_TO"]
    mock_cfg.reasoning_depth_default = 1
    mock_driver = MagicMock()
    mock_concept_gen = MagicMock()

    sentinel = "SHADOW_SECRET_SENTINEL_DO_NOT_RETURN"

    def sentinel_runner(task):
        return {"request_id": task.request_id, "output": sentinel}

    settings = ShadowSettings(mode="SHADOW_COMPARE")
    dispatcher = ShadowDispatcher(settings=settings, shadow_runner=sentinel_runner)

    r = Retriever(cfg=mock_cfg, driver=mock_driver, concept_gen=mock_concept_gen, llm=MagicMock(), shadow_dispatcher=dispatcher)
    mock_concept_gen.find_candidates.return_value = []

    res = r.answer("שאלה לבדיקה סנטינל")
    assert sentinel not in res
