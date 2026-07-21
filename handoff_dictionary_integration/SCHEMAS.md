# סכימת הגרף ב-Neo4j (Schemas)

הסכימה מבוססת על Constraints שמוגדרים בשלב ההקמה (`ingestion_pipeline.py` -> `_setup_db`).

## Nodes (צמתים)
1. **`Chunk`**
   - `chunk_id` (String, UNIQUE CONSTRAINT): מזהה ייחודי מסוג חתימת Hash.
   - מאחסן טקסט מחולק מקובץ המקור.
2. **`Concept`**
   - `canonical_name` (String, UNIQUE CONSTRAINT): שם המושג הראשי.
   - דוגמא: "השלכה", "פחד נטישה".
3. **`Exercise`**
   - `canonical_name` (String, UNIQUE CONSTRAINT): שם התרגיל.
   - דוגמא: "תרגיל הכיסא הריק".

## Relationships (קשרים)
1. **`(Chunk)-[HAS_CANDIDATE]->(Concept/Exercise)`**
   - מאפיינים: `matched_form` (המילה כפי שהופיעה בטקסט), `method` ("exact"), `score` (100).
   - מתאר מציאה טקסטואלית טרם שיפוט LLM.
2. **`(Chunk)-[LINKED_TO]->(Concept/Exercise)`**
   - מאפיינים: `matched_form`, `method`.
   - נוצר **רק לאחר ששופט ה-LLM אישר** שהמושג מופיע בהקשר קליני תקין.
3. **`(Exercise)-[WORKS_ON {chunk_id: "..."}]->(Concept)`**
   - מתאר איזה תרגיל מיועד לטפל באיזה מושג. ה-`chunk_id` מראה מאיפה זה נלמד.
4. **`DYNAMIC_RELATIONSHIPS`** (לדוגמה: `IS_SYMPTOM_OF`)
   - `(Concept)-[TYPE {chunk_id: "..."}]->(Concept)`
   - מחבר בין מושגים קליניים על סמך מה שהסקריפט זיהה בטקסט עצמו.
