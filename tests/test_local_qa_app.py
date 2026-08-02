# -*- coding: utf-8 -*-
from __future__ import annotations

import unittest

from local_qa_app import _parse_neo4j_env_lines, handle_ask, render_app_html


class FakeRetriever:
    def __init__(self):
        self.questions = []

    def answer(self, question):
        self.questions.append(question)
        return {
            "status": "answered",
            "mode": "D4_CANONICAL_LOCAL_READ_ONLY",
            "release_id": "D4-99F53565A7BCC45E",
            "answer_text": "תשובה מקומית",
            "matches": [],
            "canonical_relations": [],
            "quarantined_context": [],
            "limitations": [],
        }


class FakeAiService:
    available = True
    model = "test/model"

    def __init__(self):
        self.calls = []

    def enhance(
        self,
        question,
        result,
        *,
        requested_model=None,
        conversation_history=None,
        conversation_summary="",
    ):
        self.calls.append(
            (
                question,
                result,
                requested_model,
                conversation_history,
                conversation_summary,
            )
        )
        enhanced = dict(result)
        enhanced["answer_text"] = "AI answer"
        enhanced["mode"] = "AI_ASSISTED_D4_GROUNDED"
        enhanced["ai_status"] = "answered"
        return enhanced


class LocalQaAppTests(unittest.TestCase):
    def test_requires_explicit_no_patient_data_confirmation(self):
        retriever = FakeRetriever()

        status, body = handle_ask(
            retriever,
            {"question": "מהי עצמאות רגשית?", "confirmed_no_patient_data": False},
        )

        self.assertEqual(400, status)
        self.assertEqual("privacy_confirmation_required", body["status"])
        self.assertEqual([], retriever.questions)

    def test_rejects_direct_identifiers_even_after_confirmation(self):
        retriever = FakeRetriever()

        status, body = handle_ask(
            retriever,
            {
                "question": "מהי עצמאות רגשית עבור person@example.com?",
                "confirmed_no_patient_data": True,
            },
        )

        self.assertEqual(400, status)
        self.assertEqual("identifier_detected", body["status"])
        self.assertEqual([], retriever.questions)

    def test_confirmed_method_question_is_answered(self):
        retriever = FakeRetriever()

        status, body = handle_ask(
            retriever,
            {
                "question": "מהי עצמאות רגשית?",
                "confirmed_no_patient_data": True,
            },
        )

        self.assertEqual(200, status)
        self.assertEqual("answered", body["status"])
        self.assertEqual(["מהי עצמאות רגשית?"], retriever.questions)

    def test_internal_card_ids_are_removed_from_visible_answer(self):
        retriever = FakeRetriever()
        retriever.answer = lambda _question: {
            "status": "answered",
            "mode": "D4_CANONICAL_LOCAL_READ_ONLY",
            "answer_text": "קושי בנפש (C012) קשור למנהל B003.",
            "matches": [],
            "canonical_relations": [],
        }

        status, body = handle_ask(
            retriever,
            {
                "question": "שאלה על השיטה",
                "confirmed_no_patient_data": True,
            },
        )

        self.assertEqual(200, status)
        self.assertEqual("קושי בנפש קשור למנהל.", body["answer_text"])

    def test_ai_is_optional_and_only_runs_when_checkbox_is_selected(self):
        retriever = FakeRetriever()
        ai_service = FakeAiService()

        _, local_body = handle_ask(
            retriever,
            {
                "question": "method question",
                "confirmed_no_patient_data": True,
                "use_ai": False,
            },
            ai_service=ai_service,
            conversation_history=[
                {"role": "user", "content": "previous update"}
            ],
            conversation_summary="previous summary",
        )
        _, ai_body = handle_ask(
            retriever,
            {
                "question": "method question",
                "confirmed_no_patient_data": True,
                "use_ai": True,
                "ai_model": "deepseek/deepseek-v4-pro",
            },
            ai_service=ai_service,
            conversation_history=[
                {"role": "user", "content": "previous update"}
            ],
            conversation_summary="previous summary",
        )

        self.assertNotEqual("AI answer", local_body["answer_text"])
        self.assertEqual("AI answer", ai_body["answer_text"])
        self.assertEqual(1, len(ai_service.calls))
        self.assertEqual("deepseek/deepseek-v4-pro", ai_service.calls[0][2])
        self.assertEqual("previous update", ai_service.calls[0][3][0]["content"])
        self.assertEqual("previous summary", ai_service.calls[0][4])
        self.assertEqual(
            "previous update\nmethod question",
            retriever.questions[-1],
        )

    def test_html_is_fully_local_rtl_and_right_aligned(self):
        html = render_app_html()

        self.assertIn('dir="rtl"', html)
        self.assertIn("text-align: right", html)
        self.assertIn('id="confirmNoPatientData"', html)
        self.assertIn('id="useAi"', html)
        self.assertIn('id="aiModel"', html)
        self.assertIn("deepseek/deepseek-v4-pro", html)
        self.assertIn('id="therapistSelect"', html)
        self.assertIn('id="patientList"', html)
        self.assertIn('id="messageTimeline"', html)
        self.assertIn("use_ai", html)
        self.assertIn("ידע קנוני מאושר", html)
        self.assertIn("קשרים מאושרים", html)
        self.assertIn("₪", html)
        self.assertIn("זמן הפקה", html)
        self.assertIn("עבר בקרת איכות", html)
        self.assertNotIn("הקשר מוסגר", html)
        self.assertNotIn("https://", html)
        self.assertNotIn("http://", html)

    def test_local_settings_parser_ignores_non_neo4j_credentials(self):
        settings = _parse_neo4j_env_lines(
            [
                "NEO4J_USER=neo4j",
                "NEO4J_PASSWORD=local-password",
                "OPENROUTER_API_KEY=must-not-be-used",
            ]
        )

        self.assertEqual(
            {"NEO4J_USER": "neo4j", "NEO4J_PASSWORD": "local-password"},
            settings,
        )


if __name__ == "__main__":
    unittest.main()
