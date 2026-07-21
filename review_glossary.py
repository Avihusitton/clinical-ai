import json
from pathlib import Path

src = Path("out/glossary_draft.json")
out = Path("out/glossary_review.txt")

data = json.loads(src.read_text(encoding="utf-8"))
concepts = data.get("concepts", {})

primary = {name: meta for name, meta in concepts.items() if not meta.get("parent")}
children = {}
orphans = []

for name, meta in concepts.items():
    parent = meta.get("parent")
    if parent:
        if parent in concepts:
            children.setdefault(parent, []).append(name)
        else:
            orphans.append((name, parent))

lines = [
    f"מסמך מקור: {data.get('source_document', '')}",
    f"סהכ מושגים: {len(concepts)}",
    f"מושגים ראשיים: {len(primary)}",
    f"מושגי משנה: {len(concepts) - len(primary)}",
    "",
    "=" * 72,
    "היררכיית מושגים",
    "=" * 72,
    ""
]

for parent in sorted(primary):
    meta = concepts[parent]
    lines.append(f"[ראשי] {parent}")
    lines.append(f"  הגדרה: {meta.get('definition', '')}")
    synonyms = meta.get("synonyms", [])
    if synonyms:
        lines.append(f"  חלופות: {', '.join(synonyms)}")

    for child in sorted(children.get(parent, [])):
        child_meta = concepts[child]
        lines.append(f"  - [משנה] {child}")
        lines.append(f"    הגדרה: {child_meta.get('definition', '')}")
        child_synonyms = child_meta.get("synonyms", [])
        if child_synonyms:
            lines.append(f"    חלופות: {', '.join(child_synonyms)}")
    lines.append("")

if orphans:
    lines.extend(["=" * 72, "הורים חסרים", "=" * 72])
    lines.extend(f"{name} -> {parent}" for name, parent in orphans)

out.write_text("\n".join(lines), encoding="utf-8")
print(f"נוצר דוח: {out}")
print(f"ראשיים: {len(primary)} | משניים: {len(concepts) - len(primary)} | הורים חסרים: {len(orphans)}")
