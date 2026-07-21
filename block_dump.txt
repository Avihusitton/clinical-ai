from pathlib import Path

path = Path("ingestion_pipeline.py")
original = path.read_text(encoding="utf-8")

old = '''        works_on_edges: list[dict] = []
        rel_edges: list[dict] = []
        conflicts: list[dict] = []
        for c in all_chunks:
            works_on_edges.extend(self.rel_extractor.extract_works_on(c))
            to_load, conf = self.rel_extractor.extract_concept_relationships(c, self.existing_concept_pairs)
            rel_edges.extend(to_load)
            conflicts.extend(conf)'''

new = '''        works_on_edges: list[dict] = []
        # קשרי Concept-Concept אוטומטיים חסומים עד לאישור אנושי מפורש.
        # קשרים כאלה עשויים להיות פרשנות של מודל, ולא עובדה תיאורטית מאושרת.
        rel_edges: list[dict] = []
        conflicts: list[dict] = []
        for c in all_chunks:
            works_on_edges.extend(self.rel_extractor.extract_works_on(c))'''

if old not in original:
    raise SystemExit(
        "לא נמצא קטע הקשרים הצפוי; לא בוצע שום שינוי."
    )

backup = Path("ingestion_pipeline.before_concept_relationship_block.py")
if not backup.exists():
    backup.write_text(original, encoding="utf-8")

path.write_text(original.replace(old, new, 1), encoding="utf-8")

print(f"גיבוי קוד: {backup}")
print("קשרי Concept-Concept אוטומטיים חסומים.")
print("קשרי WORKS_ON נשארו פעילים.")
