import json
import shutil
from datetime import datetime
from pathlib import Path

path = Path("data/glossary.json")
backup_dir = Path("data/backups") / datetime.now().strftime("%Y%m%d_%H%M%S")
backup_dir.mkdir(parents=True, exist_ok=True)
shutil.copy2(path, backup_dir / path.name)

data = json.loads(path.read_text(encoding="utf-8"))
concepts = data["concepts"]

additions = {
    "מרחב זוגי": ["במרחב הזוגי", "למרחב הזוגי", "מהמרחב הזוגי"],
    "רגש בסיס": ["רגש הבסיס", "רגשות בסיס"],
}

for canonical, forms in additions.items():
    current = set(concepts[canonical].get("synonyms", []))
    current.update(forms)
    current.discard(canonical)
    concepts[canonical]["synonyms"] = sorted(current)

path.write_text(
    json.dumps(data, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

print(f"גיבוי נוצר: {backup_dir}")
print("נוספו כינויים ל'מרחב זוגי' ול'רגש בסיס'.")
