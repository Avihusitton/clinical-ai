import json
import shutil
from datetime import datetime
from pathlib import Path

data_dir = Path("data")
out_dir = Path("out")

glossary_draft = out_dir / "glossary_clean_draft.json"
exercises_draft = out_dir / "exercises_draft.json"

glossary_live = data_dir / "glossary.json"
exercises_live = data_dir / "exercises.json"

for path in (glossary_draft, exercises_draft):
    if not path.exists():
        raise SystemExit(f"טיוטה חסרה: {path}")

glossary = json.loads(glossary_draft.read_text(encoding="utf-8"))
exercises = json.loads(exercises_draft.read_text(encoding="utf-8"))

concepts = glossary.get("concepts")
tools = exercises.get("exercises")

if not isinstance(concepts, dict) or len(concepts) < 1:
    raise SystemExit("טיוטת הגלוסר אינה תקינה או ריקה.")
if not isinstance(tools, dict) or len(tools) < 1:
    raise SystemExit("טיוטת התרגילים אינה תקינה או ריקה.")

for kind, entries in (("מושג", concepts), ("תרגיל", tools)):
    for name, meta in entries.items():
        if not isinstance(name, str) or not name.strip():
            raise SystemExit(f"{kind} ללא שם תקין.")
        if not isinstance(meta, dict):
            raise SystemExit(f"{kind} '{name}' אינו אובייקט JSON תקין.")
        if not isinstance(meta.get("synonyms", []), list):
            raise SystemExit(f"{kind} '{name}': synonyms חייב להיות רשימה.")
        if not isinstance(meta.get("definition", ""), str) or not meta["definition"].strip():
            raise SystemExit(f"{kind} '{name}': חסרה definition.")

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_dir = data_dir / "backups" / stamp
backup_dir.mkdir(parents=True, exist_ok=True)

for live in (glossary_live, exercises_live):
    if live.exists():
        shutil.copy2(live, backup_dir / live.name)

glossary_live.write_text(
    json.dumps(
        {
            "_readme": "גלוסר פעיל v1. נגזר מטיוטה שעברה אישור אנושי.",
            "concepts": concepts,
        },
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)

exercises_live.write_text(
    json.dumps(
        {
            "_readme": "לקסיקון תרגילים פעיל v1. נגזר מטיוטה שעברה אישור אנושי.",
            "exercises": tools,
        },
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)

print(f"גיבוי קבצי data: {backup_dir}")
print(f"גלוסר פעיל: {len(concepts)} מושגים -> {glossary_live}")
print(f"תרגילים פעילים: {len(tools)} תרגילים -> {exercises_live}")
print("לא בוצעה טעינה ל-Neo4j.")
