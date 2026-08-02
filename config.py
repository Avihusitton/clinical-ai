# -*- coding: utf-8 -*-
"""
תצורה מרכזית לכל הפרויקט — כל הקבועים המכווננים במקום אחד.

מבנה התיקיות (ארכיטקטורת 3 התיקיות, כפי שסוכם בשיחה עם ג'מיני):
    docs_inbox/   - כאן זורקים קבצי Word חדשים. אחרי ריצה מוצלחת - ריקה.
    docs_archive/ - קבצים שעובדו בהצלחה, עם תאריך עיבוד בשם הקובץ.
    docs_error/   - קבצים שנכשלו. אם התיקייה הזו ריקה - הכל תקין.
    data/         - glossary.json, exercises.json, relationship_types.json
                    (אלה קבצי התוכן האמיתי של השיטה - setup.py יוצר תבניות
                    לדוגמה, אבל אתם צריכים למלא אותם בתוכן האמיתי).
    out/          - כל הדוחות שהצינור כותב (manifest, anchors_report וכו').
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:
    from dotenv import load_dotenv
    secret_dir = Path(__file__).parent / ".secrets"
    if secret_dir.exists():
        for env_file in secret_dir.glob("*.env"):
            load_dotenv(env_file)
    load_dotenv()
except ImportError:
    pass  # python-dotenv הוא נוחות, לא חובה - אפשר גם export ידני של משתני סביבה


@dataclass
class Config:
    base_dir: Path = Path(".")

    # --- Chunking ---
    chunk_target_chars: int = 1200
    chunk_hard_max_chars: int = 2400

    # --- Chunking למסמכי שיטה רשמיים (chunk_by_headings, לא לפי תווים) ---
    official_doc_target_chars: int = 4000  # רק לדיווח/אזהרה - לא מפצלים כפוי בטווח הזה
    official_doc_hard_cap_chars: int = 6000  # תוספת בטיחות שלי - מעליו כן מפצלים בכוח

    # --- סיווג סוג מסמך (DocumentTypeClassifier) ---
    doc_type_header_max_chars: int = 80
    doc_type_heading_ratio_threshold: float = 0.15

    # --- זיהוי עוגני זמן ---
    header_max_chars: int = 60
    anchor_min_score: int = 2

    # --- Entity linking (שלב דטרמיניסטי - שער א') ---
    fuzzy_threshold: int = 86
    max_candidates_per_chunk: int = 5

    # --- Neo4j ---
    neo4j_uri: str = field(default_factory=lambda: os.getenv("NEO4J_URI", "bolt://localhost:7687"))
    neo4j_user: str = field(default_factory=lambda: os.getenv("NEO4J_USER", "neo4j"))
    neo4j_password: str = field(default_factory=lambda: os.getenv("NEO4J_PASSWORD", ""))
    neo4j_batch_size: int = 200

    # --- LLM (OpenRouter) ---
    openrouter_api_key: str = field(default_factory=lambda: os.getenv("OPENROUTER_API_KEY", ""))
    llm_model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", "deepseek/deepseek-v4-flash"))

    # --- דגלי הרצה (נשלטים דרך ה-CLI, לא דרך .env) ---
    dry_run: bool = False   # לא כותבים ל-Neo4j, רק דוחות
    mock_llm: bool = False  # ⚠️ תשובות מזויפות - אך ורק לבדיקות עם דאטה מזויפת
    limit: int | None = None  # לעבד רק N קבצים ראשונים (להרצות מדגם מבוקרות)

    # --- טיפוסי קשר תיאורטיים מותרים (נטענים בפועל מ-relationship_types.json) ---
    reasoning_relationship_types: tuple[str, ...] = (
        "IS_SYMPTOM_OF", "LEADS_TO", "PREVENTS",
        "IS_RECOMMENDED_FOR", "IS_CONTRAINDICATED_FOR",
    )
    reasoning_depth_default: int = 2  # עומק קשיח כברירת מחדל, כפי שפייבל המליץ

    @property
    def inbox_dir(self) -> Path:
        return self.base_dir / "docs_inbox"

    @property
    def archive_dir(self) -> Path:
        return self.base_dir / "docs_archive"

    @property
    def error_dir(self) -> Path:
        return self.base_dir / "docs_error"

    @property
    def output_dir(self) -> Path:
        return self.base_dir / "out"

    @property
    def data_dir(self) -> Path:
        return self.base_dir / "data"

    @property
    def glossary_path(self) -> Path:
        return self.data_dir / "glossary.json"

    @property
    def exercise_lexicon_path(self) -> Path:
        return self.data_dir / "exercises.json"

    @property
    def relationship_types_path(self) -> Path:
        return self.data_dir / "relationship_types.json"

    @property
    def content_hash_registry_path(self) -> Path:
        """נשמר לצמיתות ב-data/ (לא נדרס בכל ריצה כמו הדוחות ב-out/) -
        כדי שדה-דופליקציה יעבוד גם בין ריצות נפרדות, לא רק בתוך ריצה אחת.
        זו הייתה נקודה עיוורת בגרסה המקורית: seen_hashes היה רק בזיכרון,
        אז קובץ כפול שנזרק לאינבוקס בריצה מאוחרת יותר לא היה מזוהה."""
        return self.data_dir / "content_hashes.json"

    def all_working_folders(self) -> tuple[Path, ...]:
        return (self.inbox_dir, self.archive_dir, self.error_dir,
                self.output_dir, self.data_dir)
