# -*- coding: utf-8 -*-
"""
טוען ל-Neo4j רק קשרי Concept-Concept שאושרו בממשק review_app.py.
מדלג על קשרים שנטענו כבר (loaded_at != None), כך שהרצה חזרה בטוחה.

הרצה: python load_approved_relationships.py
"""

from __future__ import annotations

import datetime as dt
import json
import logging

from config import Config
from ingestion_pipeline import GraphLoader

logging.basicConfig(level=logging.INFO,
                     format="%(asctime)s | %(levelname)-7s | %(message)s")
log = logging.getLogger("load_approved")


def main() -> None:
    cfg = Config()
    queue_path = cfg.data_dir / "concept_relationships_queue.json"

    if not queue_path.exists():
        log.error("קובץ התור לא נמצא: %s", queue_path)
        return

    with open(queue_path, encoding="utf-8") as f:
        queue = json.load(f)

    to_load = [e for e in queue if e["status"] == "approved" and not e.get("loaded_at")]

    if not to_load:
        log.info("אין קשרים מאושרים חדשים לטעינה.")
        return

    log.info("נמצאו %d קשרים מאושרים לטעינה.", len(to_load))

    loader = GraphLoader(cfg)
    try:
        loader.connect()
        loaded = loader.load_concept_relationships(to_load)
    finally:
        loader.close()

    now = dt.datetime.now().isoformat()
    loaded_keys = {
        (e["concept_a"], e["type"], e["concept_b"], e["chunk_id"]) for e in to_load
    }
    for e in queue:
        key = (e["concept_a"], e["type"], e["concept_b"], e["chunk_id"])
        if key in loaded_keys:
            e["loaded_at"] = now

    with open(queue_path, "w", encoding="utf-8") as f:
        json.dump(queue, f, ensure_ascii=False, indent=2)

    log.info("נטענו %d קשרי מושג-מושג מאושרים ל-Neo4j.", loaded)


if __name__ == "__main__":
    main()