# -*- coding: utf-8 -*-
"""
שכבת השליפה וההיסק — החלק שפייבל הציע להמשיך אליו ("רוצה שאמשיך לשכבת
ה-retrieval?") אבל לא הגיע לכתוב בפועל. הקוד כאן ממומש לפי המפרט המדויק
שפייבל כן נתן:

- "דלת כניסה" בלי Pinecone: הגלוסר קטן (300-350 פריטים) אז משתמשים באותה
  התאמה מורפולוגית/fuzzy מהצינור, לא בווקטורים נפרדים (זו בדיוק ההצעה
  השנייה, ה"קיצונית", שפייבל נתן - ונבחרה כאן כי היא הכי פשוטה).
- Traversal היסקי אך ורק על whitelist מפורש של טיפוסי קשר תיאורטיים,
  ולעולם לא עובר דרך Exercise (זה תיקון "הגשר המדומה").
- תרגילים נשלפים בשלב עיטור נפרד וטרמינלי, בעומק 1.
- תשובה סופית מחייבת שרשרת hop-אחר-hop עם "הערת אי-התאמה", ואסור בה
  שפת המלצה ישירה.
- עומק קשיח 2, לא פרמטר פתוח לשאילתה.

הרצה (אחרי שיש דאטה בגרף):
    python retrieval.py --question "מטופל אוכל גלידה בלילות אחרי ריב עם אמו" --modality individual
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Optional

from config import Config
from ingestion_pipeline import CandidateGenerator
from llm_client import LLMClient

log = logging.getLogger("retrieval")
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(message)s")


# ---------------------------------------------------------------------------
# מציאת "דלת הכניסה" - בלי Pinecone, בלי embeddings, כמו שפייבל הציע
# ---------------------------------------------------------------------------

def find_entry_concepts(question: str, concept_gen: CandidateGenerator, top_n: int = 3) -> list[str]:
    candidates = concept_gen.candidates_for(question)
    return [c["canonical"] for c in candidates[:top_n]]


# ---------------------------------------------------------------------------
# Traversal היסקי — whitelist מפורש, לעולם לא [*1..2] גנרי
# ---------------------------------------------------------------------------

REASONING_CYPHER_TEMPLATE = """
MATCH path = (start:Concept {{canonical_name: $start}})
             -[:{rel_types}*1..{depth}]->
             (end:Concept)
RETURN
    [n IN nodes(path) | n.canonical_name] AS concept_chain,
    [r IN relationships(path) | {{
        type: type(r), quote: r.quote, modality: r.modality,
        lesson_number: r.lesson_number
    }}] AS hop_evidence
LIMIT 25
"""

EXERCISES_FOR_CONCEPTS_CYPHER = """
MATCH (co:Concept)<-[r:WORKS_ON]-(e:Exercise)
WHERE co.canonical_name IN $concept_names
RETURN co.canonical_name AS concept, e.canonical_name AS exercise,
       r.modality AS modality, r.quote AS quote
"""


class Retriever:
    def __init__(self, cfg: Config, driver, concept_gen: CandidateGenerator, llm: LLMClient,
                 shadow_dispatcher: Optional[Any] = None):
        self.cfg = cfg
        self.driver = driver
        self.concept_gen = concept_gen
        self.llm = llm
        self._shadow_dispatcher = shadow_dispatcher
        rel_types = "|".join(t.upper() for t in cfg.reasoning_relationship_types)
        self._cypher = REASONING_CYPHER_TEMPLATE.format(
            rel_types=rel_types, depth=cfg.reasoning_depth_default)

    def _run_reasoning(self, start_concept: str) -> list[dict]:
        with self.driver.session() as s:
            result = s.run(self._cypher, start=start_concept)
            return [record.data() for record in result]

    def _run_exercises(self, concept_names: list[str]) -> list[dict]:
        if not concept_names:
            return []
        with self.driver.session() as s:
            result = s.run(EXERCISES_FOR_CONCEPTS_CYPHER, concept_names=concept_names)
            return [record.data() for record in result]

    def answer(self, question: str, current_case_modality: Optional[str] = None) -> str:
        entry_concepts = find_entry_concepts(question, self.concept_gen)
        if not entry_concepts:
            legacy_res = "אין מספיק מידע בגרף כדי לענות על השאלה הזו - לא נמצא מושג פתיחה מתאים."
            self._safe_submit_shadow(question, current_case_modality, legacy_res)
            return legacy_res

        all_paths: list[dict] = []
        for concept in entry_concepts:
            all_paths.extend(self._run_reasoning(concept))

        if not all_paths:
            legacy_res = f"נמצא מושג פתיחה ('{entry_concepts[0]}') אבל אין קשרים תיאורטיים יוצאים ממנו בגרף. אין מידע מספק."
            self._safe_submit_shadow(question, current_case_modality, legacy_res)
            return legacy_res

        # שלב עיטור טרמינלי - תרגילים בעומק 1, אחרי שההיסק הסתיים
        involved_concepts = sorted({n for p in all_paths for n in p["concept_chain"]})
        exercises = self._run_exercises(involved_concepts)

        legacy_res = self._compose(question, current_case_modality, all_paths, exercises)
        self._safe_submit_shadow(question, current_case_modality, legacy_res)
        return legacy_res

    def _safe_submit_shadow(self, question: str, modality: Optional[str], legacy_result: str) -> None:
        try:
            dispatcher = self._shadow_dispatcher
            if dispatcher is None:
                from shadow_wiring import get_shadow_settings, get_shadow_dispatcher
                settings = get_shadow_settings()
                if settings.mode == "SHADOW_COMPARE" and not settings.emergency_disable:
                    dispatcher = get_shadow_dispatcher()
            if dispatcher is not None:
                import uuid
                req_id = f"req-{uuid.uuid4()}"
                dispatcher.submit(req_id, question, modality, legacy_result)
        except Exception:
            pass

    def _compose(self, question: str, current_case_modality: Optional[str],
                 paths: list[dict], exercises: list[dict]) -> str:
        canonical_block = "\n".join(
            " -> ".join(p["concept_chain"]) for p in paths
        )
        evidence_block = json.dumps(
            [{"chain": p["concept_chain"], "hops": p["hop_evidence"]} for p in paths],
            ensure_ascii=False, indent=2,
        )
        exercises_block = json.dumps(exercises, ensure_ascii=False, indent=2) if exercises else "(אין תרגילים מקושרים)"

        system = (
            "אתה עוזר חשיבה למטפל, לא קלינאי שמחליט במקום המטפל. "
            "יש לך שני בלוקים: 'קשרים קנוניים בשיטה' (הקשרים התיאורטיים "
            "עצמם) ו'הקשר ראייתי' (ציטוטים ו-metadata מהיכן כל קשר הגיע). "
            "חוק קשיח: מה-metadata אסור להכליל - הוא משמש רק כדי לשפוט אם "
            "הקשר הקנוני רלוונטי למקרה הנוכחי, לא כידע כללי.\n\n"
            "פורמט התשובה חובה:\n"
            "1. שרשרת מנומקת hop-אחר-hop: 'צעד 1: X→Y על סמך ציטוט "
            "(הקשר המקור: ...). צעד 2: ...'\n"
            "2. שדה 'הערת אי-התאמה' חובה - השוואה בין ההקשר הטיפולי של "
            "הראיות (modality בכל hop) לבין ההקשר הטיפולי של המקרה הנוכחי "
            "שנמסר לך. אם הם שונים, ציין זאת במפורש. אי אפשר להשמיט שדה זה.\n"
            "3. אסור שפת המלצה ישירה. תמיד 'השיטה מציעה לשקול...', "
            "לעולם לא 'ההתערבות המומלצת היא...'.\n"
            "4. אם התרגילים הרלוונטיים שייכים למודאליות שונה מהמקרה "
            "הנוכחי, ציין זאת בנפרד ואל תמליץ עליהם ישירות."
        )
        user = (
            f"שאלת המטפל: {question}\n"
            f"הקשר טיפולי של המקרה הנוכחי: {current_case_modality or 'לא צוין'}\n\n"
            f"=== קשרים קנוניים בשיטה ===\n{canonical_block}\n\n"
            f"=== הקשר ראייתי (ציטוטים + metadata, לשיפוט רלוונטיות בלבד) ===\n{evidence_block}\n\n"
            f"=== תרגילים מקושרים (עיטור טרמינלי, עומק 1) ===\n{exercises_block}"
        )
        return self.llm._call(system, user, mock_response="MOCK_ANSWER")


def main() -> None:
    ap = argparse.ArgumentParser(description="שאילתת שליפה והיסק על הגרף")
    ap.add_argument("--base-dir", default=".", type=Path)
    ap.add_argument("--question", required=True)
    ap.add_argument("--modality", choices=["individual", "couples", "family", "general"], default=None)
    ap.add_argument("--mock-llm", action="store_true")
    args = ap.parse_args()

    from neo4j import GraphDatabase
    cfg = Config(base_dir=args.base_dir, mock_llm=args.mock_llm)
    driver = GraphDatabase.driver(cfg.neo4j_uri, auth=(cfg.neo4j_user, cfg.neo4j_password))

    with open(cfg.glossary_path, encoding="utf-8") as f:
        glossary = json.load(f).get("concepts", {})
    concept_gen = CandidateGenerator(cfg, glossary, "Concept")
    llm = LLMClient(cfg.openrouter_api_key, cfg.llm_model, mock=cfg.mock_llm)

    retriever = Retriever(cfg, driver, concept_gen, llm)
    try:
        print(retriever.answer(args.question, args.modality))
    finally:
        driver.close()


if __name__ == "__main__":
    main()
