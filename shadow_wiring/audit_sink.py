# -*- coding: utf-8 -*-
import hashlib
import time
from typing import List, Dict, Any


class AuditSink:
    def __init__(self):
        self._audit_log: List[Dict[str, Any]] = []
        self._last_hash: str = "GENESIS_HASH"

    def record_event(self, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        ts = time.time()
        # Verify zero raw text in audit payload
        clean_payload = {k: v for k, v in payload.items() if k not in ("raw_query", "raw_narrative", "query_text")}
        raw_str = f"{self._last_hash}|{event_type}|{ts}|{clean_payload}"
        current_hash = hashlib.sha256(raw_str.encode("utf-8")).hexdigest()

        entry = {
            "event_type": event_type,
            "timestamp": ts,
            "payload": clean_payload,
            "prev_hash": self._last_hash,
            "current_hash": current_hash,
        }
        self._last_hash = current_hash
        self._audit_log.append(entry)
        return entry

    def get_events(self) -> List[Dict[str, Any]]:
        return list(self._audit_log)
