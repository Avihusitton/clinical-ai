# -*- coding: utf-8 -*-
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from conversation_store import (
    ConversationNotFound,
    LocalConversationStore,
)


class LocalConversationStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.path = Path(self.temp_dir.name) / "workspace.json"
        self.store = LocalConversationStore(self.path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_users_and_conversations_persist_locally(self):
        therapist = self.store.create_therapist("Therapist One")
        patient = self.store.create_patient(therapist["id"], "Patient One")
        conversation = self.store.create_conversation(therapist["id"], patient["id"], "First case")
        self.store.append_message(
            therapist_id=therapist["id"],
            patient_id=patient["id"],
            conversation_id=conversation["id"],
            role="user",
            content="Synthetic progress update",
        )
        self.store.update_summary(
            therapist_id=therapist["id"],
            patient_id=patient["id"],
            conversation_id=conversation["id"],
            summary="Current synthetic case summary",
        )

        reloaded = LocalConversationStore(self.path)
        loaded = reloaded.get_conversation(therapist["id"], patient["id"], conversation["id"])

        self.assertEqual("First case", loaded["title"])
        self.assertEqual("Current synthetic case summary", loaded["summary"])
        self.assertEqual(1, len(loaded["messages"]))
        self.assertEqual("user", loaded["messages"][0]["role"])

    def test_conversations_are_isolated_by_user(self):
        first_t = self.store.create_therapist("First T")
        first_p = self.store.create_patient(first_t["id"], "First P")
        second_t = self.store.create_therapist("Second T")
        second_p = self.store.create_patient(second_t["id"], "Second P")
        conversation = self.store.create_conversation(first_t["id"], first_p["id"], "Private")

        with self.assertRaises(ConversationNotFound):
            self.store.get_conversation(second_t["id"], second_p["id"], conversation["id"])

        self.assertEqual(
            [],
            self.store.list_conversations(second_t["id"], second_p["id"]),
        )

    def test_message_metadata_tracks_cost_and_generation_time(self):
        therapist = self.store.create_therapist("Therapist")
        patient = self.store.create_patient(therapist["id"], "Patient")
        conversation = self.store.create_conversation(therapist["id"], patient["id"], "Case")

        message = self.store.append_message(
            therapist_id=therapist["id"],
            patient_id=patient["id"],
            conversation_id=conversation["id"],
            role="assistant",
            content="Grounded answer",
            metadata={
                "cost_usd": 0.0031,
                "elapsed_ms": 1820,
                "model": "deepseek/deepseek-v4-pro",
            },
        )

        self.assertEqual(0.0031, message["metadata"]["cost_usd"])
        self.assertEqual(1820, message["metadata"]["elapsed_ms"])

    def test_first_question_can_replace_default_conversation_title(self):
        therapist = self.store.create_therapist("Therapist")
        patient = self.store.create_patient(therapist["id"], "Patient")
        conversation = self.store.create_conversation(therapist["id"], patient["id"])

        renamed = self.store.set_title_from_first_question(
            therapist_id=therapist["id"],
            patient_id=patient["id"],
            conversation_id=conversation["id"],
            question="A long synthetic question about receiving help and support",
        )

        self.assertNotEqual("שיחה חדשה", renamed["title"])
        self.assertLessEqual(len(renamed["title"]), 60)


if __name__ == "__main__":
    unittest.main()
