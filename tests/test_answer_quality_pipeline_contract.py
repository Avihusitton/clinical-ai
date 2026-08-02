# -*- coding: utf-8 -*-
from __future__ import annotations

import unittest

from ai_assisted_answer import (
    AiAssistedAnswerService,
    AiGeneration,
    AiProviderError,
    build_compact_context,
)
from canonical_local_retrieval import CanonicalLocalRetriever


QUARANTINE_SENTINEL = "QUARANTINE_SENTINEL_MUST_NEVER_REACH_AI"


def rich_grounding() -> dict:
    return {
        "status": "answered",
        "mode": "D4_CANONICAL_LOCAL_READ_ONLY",
        "release_id": "D4-QUALITY-TEST",
        "answer_text": "תשובה מקומית",
        "matches": [
            {
                "card_id": f"Q{i:03d}",
                "entry_name": f"מושג קנוני {i}",
                "definition": f"הגדרה קנונית מאושרת {i}",
                "exact_source": f"מקור מקורי {i}",
            }
            for i in range(1, 7)
        ],
        "canonical_relations": [],
        "quarantined_context": [
            {
                "source_label": QUARANTINE_SENTINEL,
                "target_label": "חומר שאינו קנוני",
                "deidentified_excerpt": QUARANTINE_SENTINEL,
            }
        ],
        "limitations": [],
    }


class MultiMatchExecutor:
    def __init__(self) -> None:
        self.rows = [
            {
                "card_id": f"Q{i:03d}",
                "entry_name": f"מושג עזרה {i}",
                "entry_type": "CONCEPT",
                "status": "APPROVED",
                "aliases": ["עזרה"],
                "definition": f"הגדרה {i}",
                "source_based_definition": "",
                "exact_source": f"מקור {i}",
                "short_example": "",
                "certainty": "CANONICAL",
            }
            for i in range(1, 7)
        ]

    def run(self, cypher: str, _parameters: dict | None = None) -> list[dict]:
        if "local_qa:list_entries" in cypher:
            return list(self.rows)
        if "local_qa:relations" in cypher:
            return []
        if "local_qa:quarantine" in cypher:
            return []
        return []


class QualityPipelineProvider:
    model = "deepseek/deepseek-v4-pro"

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_completion_tokens: int,
        model: str | None = None,
    ) -> AiGeneration:
        self.calls.append(
            {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "max_completion_tokens": max_completion_tokens,
                "model": model,
            }
        )
        if len(self.calls) == 1:
            return AiGeneration(
                text=(
                    "<analysis>"
                    "<facts><item>נמסר קושי בקבלת עזרה.</item></facts>"
                    "<missing><item>לא ידוע מה כבר נוסה.</item></missing>"
                    "<gaps><item>יש פער בין הרצון לקבל לבין ההתנהגות.</item></gaps>"
                    "<lenses><item>עדשת חוויה מול מציאות.</item></lenses>"
                    "<canonical_basis><item>המקור מתאר קושי כדפוס חוזר.</item>"
                    "</canonical_basis>"
                    "<hypotheses><item>ייתכן שפועלת הגנה מפני תלות.</item>"
                    "</hypotheses>"
                    "</analysis>"
                    "<draft>טיוטה שדורשת תיקון: היא בוודאות מפחדת מתלות.</draft>"
                    "<summary>נבחן תרחיש לימודי של קושי בקבלת עזרה.</summary>"
                ),
                model=self.model,
            )
        return AiGeneration(
            text=(
                "<mode>answer</mode>"
                "<response>"
                "מהמקור הקנוני: קושי יכול להתבטא בדפוס חוזר שפוגע ביכולת לקבל עזרה.\n"
                "השערה מקצועית: ייתכן שפועלת כאן הגנה מפני תלות; זו אפשרות לבירור, "
                "לא עובדה.\n"
                "לפני בחירת כיוון, כדאי לברר מה כבר נוסה ומה קרה בפועל."
                "</response>"
                "<summary>נבחן תרחיש לימודי; חסר מידע על ניסיונות קודמים.</summary>"
                "<score>9/10</score>"
            ),
            model=self.model,
        )


class AnswerQualityPipelineContractTests(unittest.TestCase):
    def test_retrieval_and_context_are_not_capped_at_three_cards(self) -> None:
        retrieved = CanonicalLocalRetriever(MultiMatchExecutor()).answer(
            "מה משמעות העזרה?"
        )

        self.assertGreater(
            len(retrieved["matches"]),
            3,
            "שליפה רלוונטית אינה רשאית להיעצר אוטומטית בשלושה כרטיסים",
        )

        context, stats = build_compact_context(retrieved)

        self.assertGreater(stats["match_count"], 3)
        self.assertIn("Q004", context)

    def test_quality_pass_analyzes_then_reviews_before_user_visible_answer(self) -> None:
        provider = QualityPipelineProvider()

        result = AiAssistedAnswerService(provider).enhance(
            "בתרחיש לימודי, מה כדאי לברר לפני הצעת כיוון?",
            rich_grounding(),
        )

        self.assertEqual(
            2,
            len(provider.calls),
            "נדרשים מעבר ניתוח ומעבר ביקורת נפרדים",
        )
        analysis_instructions = provider.calls[0]["system_prompt"]
        for required_tag in ("<facts>", "<missing>", "<gaps>", "<lenses>"):
            self.assertIn(required_tag, analysis_instructions)

        review_input = provider.calls[1]["user_prompt"]
        self.assertIn("נמסר קושי בקבלת עזרה", review_input)
        self.assertIn("לא ידוע מה כבר נוסה", review_input)
        self.assertIn("יש פער בין הרצון לקבל", review_input)
        self.assertIn("עדשת חוויה מול מציאות", review_input)
        self.assertIn("טיוטה שדורשת תיקון", review_input)

        self.assertTrue(result["quality_reviewed"])
        self.assertIn("מהמקור הקנוני", result["answer_text"])
        self.assertIn("השערה מקצועית", result["answer_text"])
        self.assertNotIn("בוודאות מפחדת", result["answer_text"])

    def test_internal_reviewer_score_is_never_exposed_to_the_user(self) -> None:
        result = AiAssistedAnswerService(QualityPipelineProvider()).enhance(
            "שאלת איכות סינתטית",
            rich_grounding(),
        )

        self.assertNotIn("<score>", result["answer_text"])
        self.assertNotIn("9/10", result["answer_text"])
        self.assertNotIn("ציון", result["answer_text"])

    def test_follow_up_after_clarification_requires_provisional_answer(self) -> None:
        provider = QualityPipelineProvider()
        history = [
            {
                "role": "assistant",
                "content": "מה קרה באירוע קונקרטי?",
                "metadata": {"response_type": "needs_clarification"},
            }
        ]

        AiAssistedAnswerService(provider).enhance(
            "יש אירוע קונקרטי ורגש ברור. כעת הצע כיוון עבודה מדורג.",
            rich_grounding(),
            conversation_history=history,
        )

        for call in provider.calls:
            self.assertIn("אין להחזיר סבב הבהרה נוסף", call["user_prompt"])

    def test_visible_answer_strips_markdown_emphasis_and_headings(self) -> None:
        class MarkdownProvider(QualityPipelineProvider):
            def generate(self, **kwargs):
                generation = super().generate(**kwargs)
                if len(self.calls) == 2:
                    return AiGeneration(
                        text=(
                            "<mode>answer</mode>"
                            "<response>## **כיוון עבודה**\nתוכן נקי.</response>"
                            "<summary>סיכום.</summary>"
                        ),
                        model=self.model,
                    )
                return generation

        result = AiAssistedAnswerService(MarkdownProvider()).enhance(
            "הצע כיוון עבודה",
            rich_grounding(),
        )

        self.assertIn("כיוון עבודה", result["answer_text"])
        self.assertNotIn("**", result["answer_text"])
        self.assertNotIn("##", result["answer_text"])

    def test_pro_timeout_falls_back_to_flash_instead_of_local_dump(self) -> None:
        class ProTimeoutProvider:
            model = "deepseek/deepseek-v4-pro"

            def __init__(self):
                self.calls = []
                self.flash_calls = 0

            def generate(self, **kwargs):
                self.calls.append(kwargs["model"])
                if kwargs["model"] == "deepseek/deepseek-v4-pro":
                    raise AiProviderError("connection_error", "connection")
                self.flash_calls += 1
                if self.flash_calls == 1:
                    return AiGeneration(
                        text=(
                            "<analysis><facts><item>נמסר אירוע.</item></facts>"
                            "<missing></missing><gaps></gaps><lenses></lenses>"
                            "<canonical_basis></canonical_basis>"
                            "<hypotheses></hypotheses></analysis>"
                            "<draft>כיוון זמני.</draft><summary>סיכום.</summary>"
                        ),
                        model="deepseek/deepseek-v4-flash",
                    )
                return AiGeneration(
                    text=(
                        "<mode>answer</mode><response>כיוון זמני ומתוקן.</response>"
                        "<summary>סיכום.</summary>"
                    ),
                    model="deepseek/deepseek-v4-flash",
                )

        provider = ProTimeoutProvider()
        result = AiAssistedAnswerService(provider).enhance(
            "הצע כיוון עבודה",
            rich_grounding(),
            requested_model="deepseek/deepseek-v4-pro",
        )

        self.assertEqual(
            [
                "deepseek/deepseek-v4-pro",
                "deepseek/deepseek-v4-flash",
                "deepseek/deepseek-v4-flash",
            ],
            provider.calls,
        )
        self.assertEqual("answered", result["ai_status"])
        self.assertEqual("כיוון זמני ומתוקן.", result["answer_text"])
        self.assertTrue(result["provider_fallback_used"])
        self.assertEqual(2, result["generation"]["stages"])

    def test_quarantine_is_excluded_from_every_ai_stage(self) -> None:
        provider = QualityPipelineProvider()

        AiAssistedAnswerService(provider).enhance(
            "שאלת איכות סינתטית",
            rich_grounding(),
        )

        self.assertGreaterEqual(len(provider.calls), 1)
        for call in provider.calls:
            self.assertNotIn(QUARANTINE_SENTINEL, call["system_prompt"])
            self.assertNotIn(QUARANTINE_SENTINEL, call["user_prompt"])


if __name__ == "__main__":
    unittest.main()
