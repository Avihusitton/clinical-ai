from pathlib import Path

path = Path("ingestion_pipeline.py")
original = path.read_text(encoding="utf-8")

anchor_extract = """        works_on_edges: list[dict] = []
        # קשרי Concept-Concept אוטומטיים חסומים עד לאישור אנושי מפורש.
        # קשרים כאלה עשויים להיות פרשנות של מודל, ולא עובדה תיאורטית מאושרת.
        rel_edges: list[dict] = []
        conflicts: list[dict] = []
        for c in all_chunks:
            works_on_edges.extend(self.rel_extractor.extract_works_on(c))"""

new_extract = """        works_on_edges: list[dict] = []
        # קשרי Concept-Concept ממשיכים להיחלץ, אך נכתבים לתור אישור אנושי
        # (data/concept_relationships_queue.json) ולא נטענים אוטומטית ל-Neo4j.
        rel_edges: list[dict] = []
        conflicts: list[dict] = []
        for c in all_chunks:
            works_on_edges.extend(self.rel_extractor.extract_works_on(c))
            to_load, conf = self.rel_extractor.extract_concept_relationships(
                c, self.existing_concept_pairs
            )
            rel_edges.extend(to_load)
            conflicts.extend(conf)"""

anchor_load_block = """        loader = GraphLoader(self.cfg)
        try:
            loader.connect()
            loader.load_chunks(all_chunks)
            loader.load_linked(all_chunks)
            loader.load_works_on(works_on_edges)
            loader.load_concept_relationships(rel_edges)
        finally:
            loader.close()"""

new_load_block = """        loader = GraphLoader(self.cfg)
        try:
            loader.connect()
            loader.load_chunks(all_chunks)
            loader.load_linked(all_chunks)
            loader.load_works_on(works_on_edges)
            # קשרי Concept-Concept לא נטענים כאן - הם ממתינים באישור אנושי.
            # ראו review_app.py ו-load_approved_relationships.py.
        finally:
            loader.close()"""

anchor_write_call = "        self._write_reports(results, works_on_edges, rel_edges, conflicts)"

new_write_call = """        self._write_reports(results, works_on_edges, rel_edges, conflicts)
        self._queue_concept_relationships(rel_edges)"""

anchor_method_insert = "    @staticmethod\n    def _linking_stats(results: list[DocResult]) -> dict:"

new_method_insert = '''    def _queue_concept_relationships(self, rel_edges: list[dict]) -> None:
        """
        מוסיף הצעות קשר חדשות לתור אישור אנושי קבוע. לא כותב ל-Neo4j.
        דה-דופליקציה לפי (concept_a, type, concept_b, chunk_id) - אותה הצעה
        לא תופיע פעמיים אם מריצים את הצינור פעמיים על אותו chunk.
        """
        queue_path = self.cfg.data_dir / "concept_relationships_queue.json"
        if queue_path.exists():
            with open(queue_path, encoding="utf-8") as f:
                queue = json.load(f)
        else:
            queue = []

        existing_keys = {
            (e["concept_a"], e["type"], e["concept_b"], e["chunk_id"])
            for e in queue
        }

        added = 0
        for edge in rel_edges:
            key = (edge["concept_a"], edge["type"], edge["concept_b"], edge["chunk_id"])
            if key in existing_keys:
                continue
            queue.append({
                **edge,
                "status": "pending",  # pending / approved / rejected
                "queued_at": dt.datetime.now().isoformat(),
                "decided_at": None,
                "loaded_at": None,
            })
            existing_keys.add(key)
            added += 1

        with open(queue_path, "w", encoding="utf-8") as f:
            json.dump(queue, f, ensure_ascii=False, indent=2)
        log.info("נוספו %d הצעות קשר חדשות לתור האישור (%s)", added, queue_path)

    @staticmethod
    def _linking_stats(results: list[DocResult]) -> dict:'''

replacements = [
    ("שיקום חילוץ הקשרים", anchor_extract, new_extract),
    ("הסרת טעינה אוטומטית", anchor_load_block, new_load_block),
    ("קריאה לתור אחרי הדוחות", anchor_write_call, new_write_call),
    ("הוספת מתודת התור", anchor_method_insert, new_method_insert),
]

for label, old, new in replacements:
    if old not in original:
        raise SystemExit(f"לא נמצא קטע צפוי עבור: {label}. לא בוצע שום שינוי.")
    original = original.replace(old, new, 1)

backup = Path("ingestion_pipeline.before_review_queue.py")
if not backup.exists():
    backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")

path.write_text(original, encoding="utf-8")
print(f"גיבוי קוד: {backup}")
print("קשרי Concept-Concept נחלצים ונכתבים לתור אישור, לא נטענים אוטומטית.")
