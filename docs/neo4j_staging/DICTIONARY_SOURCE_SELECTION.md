<div dir="rtl">

# בחירת מקור למילון ול־Official Glossary

## תוצאה

לא קיימת עדיין חבילת שחרור קנונית שניתן להעביר ל־technical preflight או
לטעון ל־Neo4j staging.

פרויקט היצרן הוא:

`C:\Avihusitton\dherech-dictionery\Derech_Dictionary_Project`

חוזה הממשק שלו מגדיר חבילה בת 1,006 מזהים בטווחים A001–H560, ובראשה
`official_glossary.jsonl` ו־`dictionary_release_manifest.json`. בעת
הבדיקה, פרויקט היצרן היה בשער 1. רק `SOURCE_MAP.csv` נוצר; שבעת תוצרי
השחרור האחרים עדיין חסרים, ותיקיית `07_UPDATED_DICTIONARY` ריקה.

## מקורות שנפסלו כמקור קנוני

- `data/glossary.json` הוא גלוסר legacy בן 48 מושגים, ללא מזהי A–H וללא
  25 שדות הסכימה המחייבים.
- `data/official_glossary/official_glossary.sample.jsonl` הוא קובץ דוגמה
  בן שני פריטים בלבד. המזהים והשדות שלו אינם תואמים לחוזה השחרור.
- `out/glossary_draft.json` הוא תוצר LLM בן 5,071 מועמדים ואינו חבילת
  שחרור עריכתית חתומה.
- קובצי `data/backups`, `preflight_run` ושאר קובצי `out` הם עותקים,
  טיוטות או חומרי ביקורת.
- `avihu-knowledge/01_concepts` הוא קורפוס ידע של פרויקט אחר, לא חבילת
  המילון המוצהרת.
- 192 מסמכי ה־DOCX/PDF בפרויקט היצרן הם חומרי המקור שמהם תיבנה החבילה;
  הם אינם רשומות שחרור שניתן לטעון ישירות.

## השלכה על Neo4j

הסקריפט הקיים `neo4j_staging/neo4j_staging_ingest.py` מפנה לגלוסר
ה־legacy ולקובץ הדוגמה. לכן ראיות ה־dry run וה־post-load מ־24/07/2026,
המציגות 48 Concepts ושני GlossaryEntry, אינן ראיות לטעינת המילון הקנוני
ואסור להשתמש בהן כבסיס ל־PASS.

לא ניתן להריץ preflight מקצועי, dry run תקף או טעינת staging לפני
שחבילת היצרן המלאה קיימת וחתימתה ניתנת לאימות מול
`dictionary_release_manifest.json`.

```text
CANONICAL_DICTIONARY_PATH: null
CANONICAL_GLOSSARY_PATH: null
CANONICAL_SOURCE_STATUS: UNRESOLVED
TECHNICAL_PREFLIGHT_STATUS: NOT_RUN
FINAL_STATUS: BLOCKED_CANONICAL_DICTIONARY_SOURCE_AMBIGUOUS
```

הראיה המכאנית המלאה נמצאת ב־
`tests/NEO4J_STAGING_DICTIONARY_SOURCE_IDENTITY.json`.

</div>
