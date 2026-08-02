# -*- coding: utf-8 -*-
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ai_assisted_answer import (
    AiProviderError,
    AiGeneration,
    AiAssistedAnswerService,
    OpenRouterProvider,
    build_ai_service_from_environment,
    build_compact_context,
)


def grounded_result() -> dict:
    return {
        "status": "answered",
        "mode": "D4_CANONICAL_LOCAL_READ_ONLY",
        "release_id": "D4-TEST",
        "answer_text": "deterministic fallback",
        "matches": [
            {
                "card_id": "D4-001",
                "entry_name": "First",
                "definition": "A" * 3000,
                "exact_source": "source-1",
            },
            {
                "card_id": "D4-002",
                "entry_name": "Second",
                "definition": "B" * 3000,
                "exact_source": "source-2",
            },
            {
                "card_id": "D4-003",
                "entry_name": "Third",
                "definition": "third match",
            },
            {
                "card_id": "D4-004",
                "entry_name": "Must not be sent",
                "definition": "fourth match",
            },
        ],
        "canonical_relations": [
            {
                "source_name": f"S{i}",
                "target_name": f"T{i}",
                "target_id": f"R-{i}",
                "relation_label": "approved",
                "target_definition": (
                    "RELATED_CANONICAL_DEFINITION" if i == 0 else f"definition-{i}"
                ),
            }
            for i in range(20)
        ],
        "approved_source_evidence": [
            {
                "card_id": "D4-001",
                "source_document_id": "SOURCE-PRIMARY-1",
                "source_type": "DICTIONARY_CARDS",
                "source_authority": "METHOD_PRIMARY",
                "evidence_locator": "section-1",
                "evidence_type": "SOURCE_BASED_DEFINITION",
                "certainty": "HIGH",
            }
        ],
        "quarantined_context": [
            {
                "source_label": "SECRET_QUARANTINE_TEXT",
                "target_label": "Must never reach AI",
            }
        ],
        "limitations": [],
    }


class FakeProvider:
    model = "test/model"

    def __init__(self, answer: str = "professional grounded answer"):
        self.answer = answer
        self.calls: list[dict] = []

    def generate(
        self,
        *,
        system_prompt,
        user_prompt,
        max_completion_tokens,
        model=None,
    ):
        self.calls.append(
            {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "max_completion_tokens": max_completion_tokens,
                "model": model,
            }
        )
        return self.answer


class FailingProvider(FakeProvider):
    def generate(self, **_kwargs):
        raise RuntimeError("provider unavailable")


class CodedFailingProvider(FakeProvider):
    def generate(self, **_kwargs):
        raise AiProviderError("http_401", "authentication")


class MetadataProvider(FakeProvider):
    def generate(self, **kwargs):
        self.calls.append(kwargs)
        return AiGeneration(
            text=(
                "<mode>clarification</mode>\n"
                "<response>לפני הצעת כיוון, חסרים שני פרטים: (C012)\n"
                "1. מה כבר נוסה?\n2. מה קרה בעקבותיו?</response>\n"
                "<summary>נבחן קושי סינתטי בקבלת עזרה.</summary>"
            ),
            model="deepseek/deepseek-v4-pro",
            prompt_tokens=1200,
            completion_tokens=240,
            total_tokens=1440,
            cost_usd=0.0018,
        )


class AiAssistedAnswerTests(unittest.TestCase):
    def test_compact_context_is_bounded_and_excludes_quarantine(self):
        context, stats = build_compact_context(grounded_result(), max_chars=16000)

        self.assertLessEqual(len(context), 16000)
        self.assertIn("D4-001", context)
        self.assertIn("D4-002", context)
        self.assertIn("D4-003", context)
        self.assertIn("D4-004", context)
        self.assertNotIn("SECRET_QUARANTINE_TEXT", context)
        self.assertIn("RELATED_CANONICAL_DEFINITION", context)
        self.assertIn("SOURCE-PRIMARY-1", context)
        self.assertIn('"target_card_id":"R-0"', context)
        self.assertEqual(4, stats["match_count"])
        self.assertEqual(20, stats["relation_count"])
        self.assertEqual(1, stats["source_evidence_count"])

    def test_enhancement_runs_draft_and_review_with_bounded_output_budget(self):
        provider = FakeProvider()
        service = AiAssistedAnswerService(provider)

        result = service.enhance("What is the concept?", grounded_result())

        self.assertEqual("professional grounded answer", result["answer_text"])
        self.assertEqual("AI_ASSISTED_D4_GROUNDED", result["mode"])
        self.assertEqual("answered", result["ai_status"])
        self.assertEqual("test/model", result["ai_model"])
        self.assertEqual(2, len(provider.calls))
        for call in provider.calls:
            self.assertLessEqual(call["max_completion_tokens"], 5000)
            self.assertNotIn("SECRET_QUARANTINE_TEXT", call["user_prompt"])

    def test_provider_failure_falls_back_to_deterministic_answer(self):
        result = AiAssistedAnswerService(FailingProvider()).enhance(
            "What is the concept?", grounded_result()
        )

        self.assertEqual("deterministic fallback", result["answer_text"])
        self.assertEqual("D4_CANONICAL_LOCAL_READ_ONLY", result["mode"])
        self.assertEqual("unavailable", result["ai_status"])
        self.assertIn("ai_warning", result)

    def test_provider_failure_exposes_only_sanitized_diagnostic_code(self):
        result = AiAssistedAnswerService(CodedFailingProvider()).enhance(
            "What is the concept?", grounded_result()
        )

        self.assertEqual("http_401", result["ai_error_code"])
        self.assertEqual("authentication", result["ai_error_category"])

    def test_openrouter_request_uses_current_token_limit_and_privacy_routing(self):
        captured = {}

        def fake_post_json(*, url, headers, payload, timeout):
            captured.update(
                {
                    "url": url,
                    "headers": headers,
                    "payload": payload,
                    "timeout": timeout,
                }
            )
            return {"choices": [{"message": {"content": "ok"}}]}

        provider = OpenRouterProvider(
            api_key="secret-value",
            model="deepseek/deepseek-v4-flash",
            post_json=fake_post_json,
        )

        answer = provider.generate(
            system_prompt="system",
            user_prompt="user",
            max_completion_tokens=3000,
        )

        self.assertEqual("ok", answer.text)
        self.assertEqual(
            "https://openrouter.ai/api/v1/chat/completions", captured["url"]
        )
        self.assertEqual("Bearer secret-value", captured["headers"]["Authorization"])
        self.assertEqual(3000, captured["payload"]["max_completion_tokens"])
        self.assertNotIn("max_tokens", captured["payload"])
        self.assertEqual(
            "deny", captured["payload"]["provider"]["data_collection"]
        )
        self.assertEqual(
            "deepseek/deepseek-v4-flash", captured["payload"]["model"]
        )

    def test_quality_mode_can_override_flash_with_allowlisted_pro_model(self):
        captured = {}

        def fake_post_json(*, url, headers, payload, timeout):
            captured["model"] = payload["model"]
            return {"choices": [{"message": {"content": "ok"}}]}

        provider = OpenRouterProvider(
            api_key="secret-value",
            model="deepseek/deepseek-v4-flash",
            post_json=fake_post_json,
        )

        provider.generate(
            system_prompt="system",
            user_prompt="user",
            max_completion_tokens=3000,
            model="deepseek/deepseek-v4-pro",
        )

        self.assertEqual("deepseek/deepseek-v4-pro", captured["model"])

    def test_history_clarification_and_usage_are_returned_without_card_ids(self):
        provider = MetadataProvider()
        result = AiAssistedAnswerService(provider).enhance(
            "What should happen next?",
            grounded_result(),
            requested_model="deepseek/deepseek-v4-pro",
            conversation_history=[
                {"role": "user", "content": "Previous synthetic update"},
                {"role": "assistant", "content": "Previous grounded answer"},
            ],
            conversation_summary="Earlier work focused on receiving support.",
        )

        self.assertEqual("needs_clarification", result["response_type"])
        self.assertIn("מה כבר נוסה", result["answer_text"])
        self.assertNotIn("C012", result["answer_text"])
        self.assertEqual(
            "נבחן קושי סינתטי בקבלת עזרה.",
            result["conversation_summary"],
        )
        self.assertEqual(0.0036, result["generation"]["cost_usd"])
        self.assertAlmostEqual(
            0.0036 * 3.058,
            result["generation"]["cost_ils"],
            places=7,
        )
        self.assertEqual(2400, result["generation"]["prompt_tokens"])
        self.assertIn("Previous synthetic update", provider.calls[0]["user_prompt"])
        self.assertIn(
            "Earlier work focused on receiving support.",
            provider.calls[0]["user_prompt"],
        )

    def test_safe_secret_file_enables_ai_without_using_legacy_environment_key(self):
        with tempfile.TemporaryDirectory() as directory:
            secret_path = Path(directory) / "openrouter.env"
            secret_path.write_text(
                "OPENROUTER_API_KEY=new-rotated-key\n"
                "CLINICAL_AI_MODEL=deepseek/deepseek-v4-flash\n",
                encoding="utf-8",
            )

            service = build_ai_service_from_environment(
                secret_path=secret_path,
                environ={"OPENROUTER_API_KEY": "legacy-exposed-key"},
            )

        self.assertTrue(service.available)
        self.assertEqual("deepseek/deepseek-v4-flash", service.model)

    def test_legacy_environment_key_alone_is_ignored(self):
        service = build_ai_service_from_environment(
            secret_path=Path("missing-secret-file"),
            environ={"OPENROUTER_API_KEY": "legacy-exposed-key"},
        )

        self.assertFalse(service.available)


if __name__ == "__main__":
    unittest.main()
