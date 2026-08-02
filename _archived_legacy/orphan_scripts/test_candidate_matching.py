from config import Config
from ingestion_pipeline import Pipeline

p = Pipeline(Config())

samples = [
    "בזמן הפעלה קשה לבני הזוג לראות את המהות, וההגנות נכנסות לפעולה.",
    "במרחב הזוגי נבקש להעלות בקשות פרקטיות בזמן שוטף ולא בזמן הפעלה.",
    "תרגיל אורח מארח מאפשר לאחד לשתף והשני להקשיב ללא הפרעה.",
    "נשתמש בתרגול מחמאות ובעיניים מאמינות כדי לחזק את ראיית הטוב בקשר.",
    "בדף תסכולים נזהה את רגש הבסיס שמתחת למאבק.",
    "תשעת שלבי התסכול וכלי איך הם כלים לעבודה זוגית מובנית.",
]

for i, text in enumerate(samples, 1):
    concepts = p.concept_gen.candidates_for(text)
    exercises = p.exercise_gen.candidates_for(text)

    print(f"`n--- בדיקה {i} ---")
    print(text)
    print("מושגים:", [
        f"{x['canonical']} ({x['matched_form']}, {x['method']})"
        for x in concepts
    ])
    print("תרגילים:", [
        f"{x['canonical']} ({x['matched_form']}, {x['method']})"
        for x in exercises
    ])
