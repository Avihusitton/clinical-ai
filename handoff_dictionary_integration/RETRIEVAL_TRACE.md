# תהליך ההיסק ושליפת המידע (Retrieval Trace)

מסמך זה מתעד כיצד שאילתת משתמש הופכת למידע מהגרף ב-`retrieval.py`.

## שלב 1: איתור מושגי כניסה (Entry Doors)
המשתמש שואל שאלה: "איזה תרגיל מתאים למטופל שמפגין פחד נטישה?"
1. המחרוזת מועברת ל-`CandidateGenerator` (אותו אלגוריתם משלב ה-Ingestion).
2. ה-`HebrewNormalizer` מסיר ניקוד ומנסה להתאים תת-מחרוזות.
3. מתגלה המושג "פחד נטישה". הוא הופך ל-`start_concept`.

## שלב 2: סריקת הגרף (Cypher Traversal)
מריצים את השאילתה `REASONING_CYPHER_TEMPLATE`:
```cypher
MATCH path = (start:Concept {canonical_name: $start})
             -[:IS_SYMPTOM_OF|CAUSES|RELATED_TO*1..2]->
             (end:Concept)
RETURN ...
```
**מגבלות קשיחות פה:**
- **עומק מרבי 2:** כדי לא לגרום ל"דריפט קליני" (התרחקות מהנושא המקורי).
- **Whitelist של קשרים:** רק קשרים היסקיים מאושרים עוברים.
- **ללא Exercises:** אי אפשר לעבור דרך קשר של תרגיל. תרגילים אינם חלק משרשרת הסיבתיות התיאורטית.

## שלב 3: שליפת תרגילים (Terminal Step)
מריצים את השאילתה `EXERCISES_FOR_CONCEPTS_CYPHER`:
```cypher
MATCH (co:Concept)<-[r:WORKS_ON]-(e:Exercise)
WHERE co.canonical_name IN $concept_names
...
```
שולפים ישירות אילו תרגילים קשורים למושגים שמצאנו.

## שלב 4: הרכבת התשובה (Generation)
כלל המידע - המסלולים ההיסקיים, ההוכחות (Quotes), והתרגילים המקושרים - נשלחים ל-LLM כדי לנסח תשובה. על ה-LLM חל איסור "המלצה ישירה", אלא הוא חייב להציג את התשובה כדיווח אובייקטיבי מתוך המערכת ("על פי הגרף, תרגיל X מקושר למושג Y").
