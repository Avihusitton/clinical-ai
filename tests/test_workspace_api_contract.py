# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from conversation_store import LocalConversationStore
from local_qa_app import LocalQaRequestHandler


class FakeRetriever:
    def answer(self, question: str) -> dict:
        return {
            "status": "answered",
            "mode": "D4_CANONICAL_LOCAL_READ_ONLY",
            "release_id": "D4-99F53565A7BCC45E",
            "answer_text": f"תשובה מקומית עבור: {question}",
            "matches": [],
            "canonical_relations": [],
            "quarantined_context": [],
            "limitations": [],
        }

    def health(self) -> bool:
        return True


class FakeAiService:
    available = True
    model = "deepseek/deepseek-v4-pro"

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def enhance(
        self,
        question: str,
        result: dict,
        *,
        requested_model: str | None = None,
        conversation_history: list[dict] | None = None,
        conversation_summary: str = "",
    ) -> dict:
        self.calls.append(
            {
                "question": question,
                "requested_model": requested_model,
                "conversation_history": conversation_history or [],
                "conversation_summary": conversation_summary,
            }
        )
        return {
            **result,
            "mode": "AI_ASSISTED_D4_GROUNDED",
            "answer_text": "תשובת AI מבוססת רשת לשיחה המתמשכת.",
            "ai_status": "answered",
            "ai_model": requested_model or self.model,
            "response_type": "answer",
            "quality_reviewed": True,
            "conversation_summary": "סיכום מעודכן של התרחיש הלימודי.",
            "generation": {
                "cost_usd": 0.002,
                "cost_ils": 0.006116,
                "usd_to_ils_rate": 3.058,
                "usd_to_ils_rate_date": "2026-07-28",
                "elapsed_ms": 1420,
                "prompt_tokens": 900,
                "completion_tokens": 180,
                "total_tokens": 1080,
                "model": requested_model or self.model,
            },
        }


class WorkspaceApiContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = LocalConversationStore(
            Path(self.temp_dir.name) / "workspace.json"
        )
        self.ai_service = FakeAiService()

        class TestHandler(LocalQaRequestHandler):
            retriever = FakeRetriever()
            ai_service = self.ai_service
            workspace_store = self.store

        self.builder_patch = patch(
            "local_qa_app.build_ai_service_from_environment",
            return_value=self.ai_service,
        )
        self.builder_patch.start()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), TestHandler)
        self.thread = threading.Thread(
            target=self.server.serve_forever,
            daemon=True,
        )
        self.thread.start()
        host, port = self.server.server_address
        self.base_url = f"http://{host}:{port}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)
        self.builder_patch.stop()
        self.temp_dir.cleanup()

    def request(
        self,
        method: str,
        path: str,
        payload: dict | None = None,
    ) -> tuple[int, dict]:
        data = None
        headers: dict[str, str] = {}
        if payload is not None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            self.base_url + path,
            data=data,
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                return response.status, json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read().decode("utf-8"))

    def create_therapist(self, name: str) -> dict:
        status, body = self.request("POST", "/api/therapists", {"name": name})
        self.assertEqual(201, status)
        return body["therapist"]

    def create_patient(self, therapist_id: str, name: str) -> dict:
        status, body = self.request("POST", f"/api/therapists/{therapist_id}/patients", {"name": name})
        self.assertEqual(201, status)
        return body["patient"]

    def create_conversation(
        self,
        therapist_id: str,
        patient_id: str,
        title: str = "תרחיש לימודי",
    ) -> dict:
        status, body = self.request(
            "POST",
            f"/api/therapists/{therapist_id}/patients/{patient_id}/conversations",
            {"title": title},
        )
        self.assertEqual(201, status)
        return body["conversation"]

    def test_profile_can_be_created_and_listed(self) -> None:
        created = self.create_therapist("סביבת עבודה א")

        status, body = self.request("GET", "/api/therapists")

        self.assertEqual(200, status)
        self.assertEqual(
            [(created["id"], "סביבת עבודה א")],
            [(t["id"], t["name"]) for t in body["therapists"]],
        )

    def test_conversations_are_created_and_isolated_between_profiles(self) -> None:
        first_t = self.create_therapist("מטפל א")
        first_p = self.create_patient(first_t["id"], "מטופל א")
        second_t = self.create_therapist("מטפל ב")
        second_p = self.create_patient(second_t["id"], "מטופל ב")
        conversation = self.create_conversation(first_t["id"], first_p["id"], "שיחה פרטית")

        status_first, body_first = self.request(
            "GET",
            f"/api/therapists/{first_t['id']}/patients/{first_p['id']}/conversations",
        )
        status_second, body_second = self.request(
            "GET",
            f"/api/therapists/{second_t['id']}/patients/{second_p['id']}/conversations",
        )

        self.assertEqual(200, status_first)
        self.assertEqual(200, status_second)
        self.assertEqual(
            [conversation["id"]],
            [item["id"] for item in body_first["conversations"]],
        )
        self.assertEqual([], body_second["conversations"])

    def test_ai_answer_persists_shekel_cost_time_and_receives_history(self) -> None:
        therapist = self.create_therapist("סביבת בדיקה")
        patient = self.create_patient(therapist["id"], "מטופל בדיקה")
        conversation = self.create_conversation(therapist["id"], patient["id"])
        self.store.append_message(
            therapist_id=therapist["id"],
            patient_id=patient["id"],
            conversation_id=conversation["id"],
            role="user",
            content="עדכון קודם בתרחיש לימודי לא־קליני.",
        )
        self.store.append_message(
            therapist_id=therapist["id"],
            patient_id=patient["id"],
            conversation_id=conversation["id"],
            role="assistant",
            content="מענה קודם מבוסס־שיטה.",
        )
        self.store.update_summary(
            therapist_id=therapist["id"],
            patient_id=patient["id"],
            conversation_id=conversation["id"],
            summary="סיכום קודם של התרחיש הלימודי.",
        )

        status, body = self.request(
            "POST",
            "/api/ask",
            {
                "therapist_id": therapist["id"],
                "patient_id": patient["id"],
                "conversation_id": conversation["id"],
                "question": "מה כדאי לברר בשלב הבא בתרחיש הלימודי?",
                "confirmed_no_patient_data": True,
                "use_ai": True,
                "ai_model": "deepseek/deepseek-v4-pro",
            },
        )

        self.assertEqual(200, status)
        self.assertEqual(conversation["id"], body["conversation_id"])
        self.assertEqual(0.006116, body["generation"]["cost_ils"])
        self.assertEqual(1420, body["generation"]["elapsed_ms"])
        self.assertEqual(1, len(self.ai_service.calls))
        ai_call = self.ai_service.calls[0]
        self.assertEqual(
            "סיכום קודם של התרחיש הלימודי.",
            ai_call["conversation_summary"],
        )
        self.assertEqual(
            ["user", "assistant"],
            [message["role"] for message in ai_call["conversation_history"]],
        )
        self.assertIn(
            "עדכון קודם",
            ai_call["conversation_history"][0]["content"],
        )

        saved = self.store.get_conversation(therapist["id"], patient["id"], conversation["id"])
        self.assertEqual(
            ["user", "assistant", "user", "assistant"],
            [message["role"] for message in saved["messages"]],
        )
        assistant = saved["messages"][-1]
        self.assertEqual(
            "תשובת AI מבוססת רשת לשיחה המתמשכת.",
            assistant["content"],
        )
        self.assertEqual(
            0.006116,
            assistant["metadata"]["generation"]["cost_ils"],
        )
        self.assertEqual(
            1420,
            assistant["metadata"]["generation"]["elapsed_ms"],
        )
        self.assertEqual("answer", assistant["metadata"]["response_type"])
        self.assertEqual(
            "deepseek/deepseek-v4-pro",
            assistant["metadata"]["ai_model"],
        )
        self.assertTrue(assistant["metadata"]["quality_reviewed"])
        self.assertEqual(
            "סיכום מעודכן של התרחיש הלימודי.",
            saved["summary"],
        )


if __name__ == "__main__":
    unittest.main()
