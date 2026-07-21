import json
from pathlib import Path

glossary_path = Path("out/glossary_clean_draft.json")
exercises_path = Path("out/exercises_draft.json")

glossary = json.loads(glossary_path.read_text(encoding="utf-8"))
exercises = json.loads(exercises_path.read_text(encoding="utf-8"))

concepts = glossary["concepts"]
tools = exercises["exercises"]

# כפילות: "דפוסי הגנה" נשאר ניסוח חלופי של "הגנות", לא Concept נפרד.
concepts.pop("דפוסי הגנה", None)

# הסר חלופות רחבות מדי, שעלולות לזהות הקשרים לא נכונים.
remove_from_concepts = {
    "מבנה הנפש": {"3 המעגלים"},
    "לימוד זכות": {"הצדקת התנהגות"},
    "מאבק": {"עימות", "היאבקות"},
}

remove_from_exercises = {
    "עיניים מאמינות": {"מיקוד במהות", "ראיית הטוב"},
    "כלי איך": {"כלי עבודה מובנה"},
}

for name, banned in remove_from_concepts.items():
    if name in concepts:
        concepts[name]["synonyms"] = [
            x for x in concepts[name].get("synonyms", []) if x not in banned
        ]

for name, banned in remove_from_exercises.items():
    if name in tools:
        tools[name]["synonyms"] = [
            x for x in tools[name].get("synonyms", []) if x not in banned
        ]

# הגדרות מדויקות יותר עבור מושגים רגישים.
concepts["לימוד זכות"]["definition"] = (
    "ניסיון להבין את התנהגות האחר בהקשר רחב ומיטיב, "
    "בלי לבטל אחריות, גבולות או פגיעה."
)
concepts["תלות"]["definition"] = (
    "הישענות על בן או בת הזוג לצרכים רגשיים או מעשיים; "
    "הקשר הטיפולי מבחין בין תלות טבעית לתלות מכבידה או פוגעת."
)
concepts["מאבק"]["definition"] = (
    "מעגל תגובתי שבו ניסיון לשנות את האחר יוצר התנגדות "
    "ומחריף את הקונפליקט הזוגי."
)
tools["כלי איך"]["definition"] = (
    "כלי עבודה מובנה בשיטה, המסייע לבני זוג לברר "
    "ולעבד קונפליקט באופן מדורג."
)

glossary_path.write_text(
    json.dumps(glossary, ensure_ascii=False, indent=2),
    encoding="utf-8",
)
exercises_path.write_text(
    json.dumps(exercises, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

print(f"מושגים מאושרים בטיוטה: {len(concepts)}")
print(f"תרגילים מאושרים בטיוטה: {len(tools)}")
print("התיקון בוצע רק ב-out; data ו-Neo4j לא שונו.")
