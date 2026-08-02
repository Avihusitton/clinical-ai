<div dir="rtl" align="right">

# עקיבות נתונים (Data Lineage)

## 1. כניסה (Source)
- קבצי `.docx` או `.pdf` מונחים בתיקיית `docs_inbox/`.
- הקבצים מזוהים ומעובדים דרך `file_manager.py` (אחראי על איתור, העברה לארכיון או לשגיאות).
- לפני עיבוד נרשמים SHA-256, ‏`source_document_id`, סוג המקור ורמת סמכותו לפי `data/material_intake/source_registry.schema.json`.
- ברירת המחדל לחומר ללא הצהרת מקור מתועדת היא `UNVERIFIED`.
- הצהרת המשתמש בזמן הצירוף נרשמת פעם אחת ואינה מחייבת שאלה חוזרת.

## 2. חלוקה וניקוי (Parsing & Chunking)
- סקריפט `ingestion_pipeline.py` (פונקציות Parsing) קורא את הטקסט.
- **ניקוי PII:** מודל שפה עובר על הקטעים הרגישים כדי למסך שמות פרטיים ומידע רפואי מזהה. אם החלק הזה נכשל, הקובץ מועבר ל-`docs_error`.
- הופך את הטקסט ל-Chunks ששוקלים כ-1000 תווים במקרה של מסמך רשמי, או מחולק לפי פסקאות/עוגני זמן לתמלילים קליניים.

## 3. מיפוי מועמדים (Candidate Generation)
- המערכת משתמשת במילון (`glossary_draft.json` - שהוא כרגע דינמי) כדי לאתר התאמות מדויקות בתוך ה-Chunk.
- `HebrewNormalizer` מוריד ניקוד ומסיר קידומות כמו "ו", "ב", "ה" כדי למצוא התאמה בסיסית. אלו נשמרים בזיכרון המערכת כ-Candidates.
- מועמדים חדשים נשמרים עם זהות המקור, מיקום הראיה וגיבוב הראיה; חבילת המסירה אינה חייבת להכיל ציטוט גולמי.

## 4. שיפוט LLM (Context Verification)
- רשימת המועמדים נשלחת חזרה ל-LLM דרך `llm_client.py` עם שאלת שיפוט: "האם הטקסט הנל מדבר באופן מקצועי/קליני על המושג?".
- מועמדים שמוחזרים כ-`yes` מתקדמים לגרף.
- מועמדים שמוחזרים כ-`unclear` נשמרים בקובץ `waiting_room.json` לבדיקה עתידית.

## 5. הזרקה ל-Neo4j
- קשרי `HAS_CANDIDATE` (לפני השיפוט).
- קשרי `LINKED_TO` (לאחר שיפוט חיובי).
- בסיום ההזרקה, הקובץ המקורי עובר אל `docs_archive/`.
- לפי הממשל הפעיל, כתיבה מותרת רק ל־Staging ולאחר זיהוי מקור קנוני, Preflight, ‏Dry Run ואימות יעד. ייצור נשאר אסור.

## 6. שאילתות משתמש
- משתמש מחפש מחרוזת בממשק.
- המערכת הופכת אותה ל-Entry Concept.
- מבצעת מעבר (Traversal) על הגרף ומחזירה Chunks רלוונטיים ומסלולים לוגיים.

## 7. משוב ליצרן המילון

לאחר PII וזכויות:

- `METHOD_PRIMARY` יכול להפיק `NEW_CANONICAL_ENTRY`, ‏`CANONICAL_UPDATE`, ‏`SUBCONCEPT`, ‏`RELATION` או `EXAMPLE`.
- `SECONDARY_INTERPRETIVE` יכול להפיק רק `SUBCONCEPT`, ‏`RELATION` או `EXAMPLE`, ורק עם עוגן למזהה קנוני קיים.
- `UNVERIFIED` עובר להסגר.

`material_intake_router.py` מפריד בין:

- `DICTIONARY_CANONICAL_REVIEW`
- `DICTIONARY_SUPPLEMENTAL_REVIEW`
- `QUARANTINE`

אין קידום אוטומטי. פרויקט המילון מחזיר ידע מאושר רק כחלק ממהדורה חתומה שעוברת מחדש את בדיקות הקבלה של `clinical_ai`.

</div>
