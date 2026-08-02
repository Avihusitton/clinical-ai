from pathlib import Path

path = Path("ingestion_pipeline.py")
text = path.read_text(encoding="utf-8")

old_run = '''        works_on_edges: list[dict] = []
        rel_edges: list[dict] = []
        conflicts: list[dict] = []
        for c in all_chunks:
            works_on_edges.extend(self.rel_extractor.extract_works_on(c))
            to_load, conf = self.rel_extractor.extract_concept_relationships(c, self.existing_concept_pairs)
            rel_edges.extend(to_load)
            conflicts.extend(conf)'''

new_run = '''        works_on_edges: list[dict] = []
        rel_edges: list[dict] = []
        conflicts: list[dict] = []
        for c in all_chunks:
            works_on_edges.extend(self.rel_extractor.extract_works_on(c))
            if getattr(self.cfg, "enable_concept_relationships", False):
                to_load, conf = self.rel_extractor.extract_concept_relationships(
                    c, self.existing_concept_pairs
                )
                rel_edges.extend(to_load)
                conflicts.extend(conf)'''

old_config = '''    limit: int | None = None # לעבד רק N קבצים ראשונים (הרצות מדגם מבוקרות)'''

new_config = '''    limit: int | None = None # לעבד רק N קבצים ראשונים (הרצות מדגם מבוקרות)
    enable_concept_relationships: bool = False # רק באישור אנושי מפורש'''

old_cli = '''    ap.add_argument("--limit", type=int, default=None, help="לעבד רק N קבצים ראשונים (הרצת מדגם מבוקרת)")
    args = ap.parse_args()

    cfg = Config(base_dir=args.base_dir, dry_run=args.dry_run,
                 mock_llm=args.mock_llm, limit=args.limit)'''

new_cli = '''    ap.add_argument("--limit", type=int, default=None, help="לעבד רק N קבצים ראשונים (הרצת מדגם מבוקרת)")
    ap.add_argument("--enable-concept-relationships", action="store_true",
                    help="הפעלת קשרי מושג-מושג אוטומטיים; רק לאחר אישור אנושי")
    args = ap.parse_args()

    cfg = Config(base_dir=args.base_dir, dry_run=args.dry_run,
                 mock_llm=args.mock_llm, limit=args.limit,
                 enable_concept_relationships=args.enable_concept_relationships)'''

for label, old, new in (
    ("לולאת הקשרים", old_run, new_run),
    ("Config", old_config, new_config),
    ("CLI", old_cli, new_cli),
):
    if old not in text:
        raise SystemExit(f"לא נמצא קטע צפוי עבור {label}; לא בוצע שינוי.")
    text = text.replace(old, new, 1)

backup = Path("ingestion_pipeline.before_relationship_guard.py")
if not backup.exists():
    backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")

path.write_text(text, encoding="utf-8")
print(f"גיבוי קוד: {backup}")
print("קשרי Concept-Concept חסומים כברירת מחדל.")
print("להפעלה מודעת בעתיד: --enable-concept-relationships")
