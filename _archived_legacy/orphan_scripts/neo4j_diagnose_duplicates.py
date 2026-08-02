# -*- coding: utf-8 -*-
"""
neo4j_diagnose_duplicates.py -- קריאה בלבד. לא מוחק, לא כותב, לא נוגע בשום דבר.
בודק אם הבאג שמצאנו (קובץ שעובד פעמיים תחת שמות שונים) השאיר עותקים
כפולים בגרף האמיתי.

הרצה:
    python neo4j_diagnose_duplicates.py
"""
from __future__ import annotations

from neo4j import GraphDatabase
from config import Config

cfg = Config()


def main() -> None:
    driver = GraphDatabase.driver(cfg.neo4j_uri, auth=(cfg.neo4j_user, cfg.neo4j_password))
    try:
        with driver.session() as s:
            print("=== סיכום כללי (בייסליין) ===")
            n_chunks = s.run("MATCH (c:Chunk) RETURN count(c) AS n").single()["n"]
            n_concepts = s.run("MATCH (k:Concept) RETURN count(k) AS n").single()["n"]
            n_exercises = s.run("MATCH (e:Exercise) RETURN count(e) AS n").single()["n"]
            print(f"  Chunk: {n_chunks}")
            print(f"  Concept: {n_concepts}")
            print(f"  Exercise: {n_exercises}")

            print("\n=== חשוד #1: chunks ששם המסמך שלהם נראה כמו קובץ שכבר אורכב ===")
            print("(doc_id שמכיל '_processed_YYYY-MM-DD' - סימן שקובץ מהארכיון חזר לאינבוקס)")
            suspects = list(s.run("""
                MATCH (c:Chunk)
                WHERE c.doc_id =~ '.*_processed_\\\\d{4}-\\\\d{2}-\\\\d{2}.*'
                RETURN c.doc_id AS doc_id, count(c) AS n_chunks
                ORDER BY n_chunks DESC
            """))
            if suspects:
                for r in suspects:
                    print(f"  ⚠️  doc_id='{r['doc_id']}' - {r['n_chunks']} chunks")
            else:
                print("  לא נמצא כלום - נקי מהתבנית הזו.")

            print("\n=== חשוד #2: chunks ארוכים (100+ תווים) עם טקסט זהה בדיוק אבל chunk_id שונה ===")
            print("(מוגבל ל-100+ תווים בכוונה - ביטויים קצרים חוזרים לעיתים באופן לגיטימי")
            print(" בשיעורים שונים, וזה לא סימן לבאג)")
            dupes = list(s.run("""
                MATCH (c:Chunk)
                WHERE size(c.text) >= 100
                WITH c.text AS text, collect({id: c.chunk_id, doc_id: c.doc_id}) AS copies
                WHERE size(copies) > 1
                RETURN text, copies
                LIMIT 20
            """))
            if dupes:
                for r in dupes:
                    print(f"  ⚠️  טקסט זהה ב-{len(r['copies'])} chunks:")
                    for cp in r["copies"]:
                        print(f"       chunk_id={cp['id']}  doc_id={cp['doc_id']}")
                    print(f"       תחילת הטקסט: {r['text'][:80]!r}")
            else:
                print("  לא נמצא טקסט כפול - נקי.")

            print("\n=== סיכום ===")
            if not suspects and not dupes:
                print("לא נמצאה עדות לכפילות בגרף האמיתי. ייתכן שהריצה הבעייתית הייתה dry-run בפועל,")
                print("או שהיא לא הגיעה לשלב הטעינה. אין צורך בניקוי.")
            else:
                print("נמצאה עדות לכפילות אמיתית. אל תמחקו כלום עדיין - תעתיקו את הפלט הזה")
                print("ונחליט יחד בדיוק מה למחוק (תמיד chunk_id אחד נשמר, לא שניהם).")
    finally:
        driver.close()


if __name__ == "__main__":
    main()
