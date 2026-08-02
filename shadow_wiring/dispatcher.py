# -*- coding: utf-8 -*-
import queue
import threading
import logging
from typing import Optional, Callable, Dict, Any
from .settings import ShadowSettings, get_shadow_settings
from .models import ShadowTaskPayload
from .redaction import RedactionEngine
from .audit_sink import AuditSink
from .telemetry_sink import TelemetrySink
from .comparator import ShadowComparator

log = logging.getLogger("shadow_wiring.dispatcher")


class ShadowDispatcher:
    def __init__(self, settings: Optional[ShadowSettings] = None, shadow_runner: Optional[Callable] = None):
        self.settings = settings or get_shadow_settings()
        self.shadow_runner = shadow_runner
        self._queue: queue.Queue = queue.Queue(maxsize=self.settings.queue_size)
        self.audit_sink = AuditSink()
        self.telemetry_sink = TelemetrySink()
        self._worker_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._shutdown_flag = False

    def _ensure_worker_started(self):
        if self._worker_thread is None or not self._worker_thread.is_alive():
            with self._lock:
                if self._worker_thread is None or not self._worker_thread.is_alive():
                    self._worker_thread = threading.Thread(
                        target=self._worker_loop,
                        name="ShadowWorkerThread",
                        daemon=True
                    )
                    self._worker_thread.start()

    def submit(self, request_id: str, query_text: str, modality: Optional[str], legacy_result: str, user_id: str = "") -> bool:
        """
        Non-blocking off-critical-path submission.
        Returns True if queued, False if skipped/dropped.
        """
        # Mode check
        if self.settings.mode != "SHADOW_COMPARE" or self.settings.emergency_disable:
            self.audit_sink.record_event("AUDIT_MODE_EVALUATED", {"mode": self.settings.mode})
            return False

        # Scan for PII
        has_pii, _, detected = RedactionEngine.scan_and_redact(query_text)
        if has_pii:
            self.audit_sink.record_event("AUDIT_PII_REJECTED", {
                "request_id": request_id,
                "detected_pii_count": len(detected)
            })
            self.telemetry_sink.record_metric("pii_rejected", 1, {"request_id": request_id})
            return False

        query_hash = RedactionEngine.hash_text(query_text)
        legacy_hash = RedactionEngine.hash_text(legacy_result)
        user_hash = RedactionEngine.hash_user_id(user_id)

        payload = ShadowTaskPayload(
            request_id=request_id,
            redacted_query_hash=query_hash,
            modality=modality,
            legacy_result_hash=legacy_hash,
            user_id_hash=user_hash
        )

        self._ensure_worker_started()

        try:
            # Non-blocking put
            self._queue.put_nowait(payload)
            self.telemetry_sink.record_metric("task_queued", 1, {"request_id": request_id})
            return True
        except queue.Full:
            # DROP_SHADOW_TASK_AND_AUDIT
            self.audit_sink.record_event("SHADOW_QUEUE_SATURATED", {
                "request_id": request_id,
                "queue_size": self.settings.queue_size
            })
            self.telemetry_sink.record_metric("task_dropped_queue_full", 1, {"request_id": request_id})
            return False

    def _worker_loop(self):
        while not self._shutdown_flag:
            try:
                task: ShadowTaskPayload = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue

            try:
                if self.shadow_runner:
                    res = self.shadow_runner(task)
                else:
                    # Default isolated runner double
                    res = {
                        "request_id": task.request_id,
                        "verdict": "OFFICIAL_RAG_SERVED",
                        "difference_class": "AGREEMENT",
                        "is_fallback": False
                    }

                comp = ShadowComparator.classify(task.legacy_result_hash, res)
                self.audit_sink.record_event("AUDIT_SHADOW_COMPARED", {
                    "request_id": comp.request_id,
                    "difference_class": comp.difference_class
                })
                self.telemetry_sink.record_metric("difference_class", comp.difference_class, {"request_id": comp.request_id})
            except Exception as exc:
                log.warning("Shadow worker exception: %s", exc)
                self.audit_sink.record_event("AUDIT_SHADOW_FAILED", {
                    "request_id": task.request_id,
                    "error": str(exc)
                })
                self.telemetry_sink.record_metric("shadow_worker_error", 1, {"request_id": task.request_id})
            finally:
                self._queue.task_done()


_global_dispatcher: Optional[ShadowDispatcher] = None


def get_shadow_dispatcher() -> ShadowDispatcher:
    global _global_dispatcher
    if _global_dispatcher is None:
        _global_dispatcher = ShadowDispatcher()
    return _global_dispatcher
