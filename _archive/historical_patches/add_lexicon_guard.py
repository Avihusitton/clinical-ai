from pathlib import Path

path = Path("ingestion_pipeline.py")
text = path.read_text(encoding="utf-8")

old = '''        glossary = self._load_lexicon(cfg.glossary_path, "concepts")
        exercises = self._load_lexicon(cfg.exercise_lexicon_path, "exercises")
        self.concept_gen = CandidateGenerator(cfg, glossary, "Concept")'''

new = '''        glossary = self._load_lexicon(cfg.glossary_path, "concepts")
        exercises = self._load_lexicon(cfg.exercise_lexicon_path, "exercises")

        if not glossary:
            raise RuntimeError(
                f"גלוסר המושגים ריק או חסר: {cfg.glossary_path}. "
                "ההרצה נעצרת כדי למנוע טעינה ללא Entity Linking."
            )
        if not exercises:
            raise RuntimeError(
                f"לקסיקון התרגילים ריק או חסר: {cfg.exercise_lexicon_path}. "
                "ההרצה נעצרת כדי למנוע טעינה ללא Entity Linking."
            )

        self.concept_gen = CandidateGenerator(cfg, glossary, "Concept")'''

if old not in text:
    raise SystemExit("לא נמצא הקטע הצפוי; לא בוצע שינוי.")

backup = Path("ingestion_pipeline.before_lexicon_guard.py")
if not backup.exists():
    backup.write_text(text, encoding="utf-8")

path.write_text(text.replace(old, new, 1), encoding="utf-8")

print(f"גיבוי קוד: {backup}")
print("נוסף שער: הפייפליין ייעצר אם glossary או exercises ריקים.")
