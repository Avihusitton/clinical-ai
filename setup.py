# -*- coding: utf-8 -*-
"""
סקריפט הקמה — מריצים אותו פעם אחת בהתחלה (ואפשר שוב בבטחה, הוא לא דורס
קבצים קיימים). יוצר את מבנה התיקיות ותבניות דוגמה לגלוסר/תרגילים/יחסים,
ומכין את קובץ ה-.env.

הרצה:  python setup.py
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from config import Config

EXAMPLE_GLOSSARY = {
    "_readme": "קובץ דוגמה. מחקו את שני המושגים לדוגמה ומלאו את כ-300 "
               "המושגים האמיתיים של השיטה. כל מפתח הוא שם קנוני; synonyms "
               "היא רשימת מילים נרדפות/הטיות נפוצות; definition היא הגדרה "
               "קצרה - המודל משתמש בה כדי לשפוט אם קטע טקסט באמת שייך "
               "למושג הזה (שלב האימות הבינארי).",
    "concepts": {
        "הדחקה": {
            "synonyms": ["מנגנון הדחקה", "הדחקת רגש", "מדחיק", "מדחיקה"],
            "definition": "מנגנון הגנה נפשי שבו רגש או מחשבה לא נסבלים "
                           "נדחקים מחוץ למודעות."
        },
        "פיצוי פיזי": {
            "synonyms": ["פיצוי גופני", "מפצה פיזית"],
            "definition": "התנהגות פיזית (כמו אכילה) המשמשת להרגעה עצמית "
                           "כתגובה למצוקה רגשית."
        }
    }
}

EXAMPLE_EXERCISES = {
    "_readme": "קובץ דוגמה לתרגילים מעשיים (בשיטה האמיתית יהיו כ-30-50, "
               "לא 300 - זה לקסיקון הרבה יותר קטן מהגלוסר של המושגים).",
    "exercises": {
        "כתיבת יומן": {
            "synonyms": ["יומן רגשות", "תרגיל היומן", "כתיבה יומית"],
            "definition": "תיעוד יומי כתוב של רגשות ואירועים, ככלי להעלאת מודעות."
        },
        "דמיון מודרך": {
            "synonyms": ["הדמיה מודרכת"],
            "definition": "תרגיל הרפיה שבו המטפל מנחה את המטופל בדמיון מונחה."
        }
    }
}

EXAMPLE_RELATIONSHIP_TYPES = {
    "_readme": "טיפוסי הקשר הקנוניים בין מושגים בשיטה. זה שלד לדוגמה "
               "בלבד - צריך להתאים אותו לאונטולוגיה האמיתית של השיטה "
               "(פייבל דיבר על טבלת סתירות של כ-20 שורות - זו רק נקודת "
               "התחלה עם 5 טיפוסים ו-2 זוגות סותרים).",
    "relationship_types": [
        {"name": "is_symptom_of", "description": "X הוא ביטוי/סימפטום הנובע מ-Y"},
        {"name": "leads_to", "description": "X מוביל/גורם ל-Y"},
        {"name": "prevents", "description": "X מונע או חוסם את Y"},
        {"name": "is_recommended_for", "description": "X מומלץ כטיפול/גישה עבור Y"},
        {"name": "is_contraindicated_for", "description": "X אינו מתאים / אסור עבור Y"}
    ],
    "contradictions": [
        {"a": "leads_to", "b": "prevents"},
        {"a": "is_recommended_for", "b": "is_contraindicated_for"}
    ]
}


def main() -> None:
    cfg = Config()
    print("=== הקמת סביבת העבודה ===\n")

    for folder in cfg.all_working_folders():
        folder.mkdir(parents=True, exist_ok=True)
        print(f"תיקייה מוכנה: {folder}/")

    _write_if_missing(cfg.glossary_path, EXAMPLE_GLOSSARY)
    _write_if_missing(cfg.exercise_lexicon_path, EXAMPLE_EXERCISES)
    _write_if_missing(cfg.relationship_types_path, EXAMPLE_RELATIONSHIP_TYPES)

    env_path, example_path = Path(".env"), Path(".env.example")
    if not env_path.exists() and example_path.exists():
        shutil.copy(example_path, env_path)
        print("\nנוצר קובץ .env מתוך .env.example - פתחו אותו ומלאו את "
              "מפתח ה-API ופרטי Neo4j.")
    elif env_path.exists():
        print("\n.env כבר קיים - לא נגעתי בו.")
    else:
        print("\n⚠️  לא נמצא .env.example - ודאו שהוא נמצא באותה תיקייה.")

    print("\n=== סיכום ===")
    print(f"שימו קבצי Word חדשים בתוך: {cfg.inbox_dir}/")
    print(f"מלאו את הגלוסר האמיתי בתוך: {cfg.glossary_path}")
    print(f"מלאו את התרגילים האמיתיים בתוך: {cfg.exercise_lexicon_path}")
    print(f"בדקו/עדכנו את טיפוסי הקשר בתוך: {cfg.relationship_types_path}")
    print("\nכשתסיימו למלא, בדיקה ראשונה בלי לגעת ב-API או ב-Neo4j:")
    print("  python ingestion_pipeline.py --dry-run --mock-llm --limit 1")
    print("\nהסביבה מוכנה.")


def _write_if_missing(path: Path, content: dict) -> None:
    if path.exists():
        print(f"כבר קיים, לא נגעתי: {path}")
        return
    with open(path, "w", encoding="utf-8") as f:
        json.dump(content, f, ensure_ascii=False, indent=2)
    print(f"נוצר קובץ דוגמה: {path}")


if __name__ == "__main__":
    main()
