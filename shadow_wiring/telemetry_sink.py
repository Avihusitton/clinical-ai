# -*- coding: utf-8 -*-
from typing import List, Dict, Any


class TelemetrySink:
    def __init__(self):
        self._telemetry_records: List[Dict[str, Any]] = []

    def record_metric(self, metric_name: str, value: Any, tags: Dict[str, str] = None) -> Dict[str, Any]:
        record = {
            "metric_name": metric_name,
            "value": value,
            "tags": tags or {},
        }
        self._telemetry_records.append(record)
        return record

    def get_records(self) -> List[Dict[str, Any]]:
        return list(self._telemetry_records)
