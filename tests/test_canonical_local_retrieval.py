# -*- coding: utf-8 -*-
from __future__ import annotations

import unittest

from canonical_local_retrieval import (
    CanonicalLocalRetriever,
    Neo4jUnavailable,
    ReadOnlyNeo4jHttpClient,
    SOURCE_EVIDENCE_QUERY,
)


class FakeExecutor:
    def __init__(self, entries=None, relations=None, quarantine=None, failure=None):
        self.entries = entries or []
        self.relations = relations or []
        self.quarantine = quarantine or []
        self.failure = failure
        self.calls = []

    def run(self, cypher, parameters=None):
        self.calls.append((cypher, parameters or {}))
        if self.failure:
            raise self.failure
        if "local_qa:list_entries" in cypher:
            return list(self.entries)
        if "local_qa:relations" in cypher:
            return list(self.relations)
        if "local_qa:source_evidence" in cypher:
            return []
        if "local_qa:quarantine" in cypher:
            return list(self.quarantine)
        if "local_qa:health" in cypher:
            return [{"ok": 1}]
        raise AssertionError(f"Unexpected query: {cypher}")


def entry(card_id, name, aliases=None, definition="הגדרה קנונית", status="APPROVED"):
    return {
        "card_id": card_id,
        "entry_name": name,
        "entry_type": "CONCEPT",
        "status": status,
        "aliases": aliases or [],
        "definition": definition,
        "source_based_definition": "",
        "exact_source": "מקור שיטה מאושר",
        "short_example": "",
        "certainty": "HIGH",
    }


class CanonicalLocalRetrieverTests(unittest.TestCase):
    def test_exact_name_returns_canonical_answer_without_llm(self):
        executor = FakeExecutor(
            entries=[
                entry("A002", "עצמאות רגשית", ["עצמאות פנימית"]),
                entry("A003", "עצמאות תפקודית"),
            ],
            relations=[
                {
                    "source_id": "A002",
                    "source_name": "עצמאות רגשית",
                    "relation_type": "SEE_ALSO",
                    "target_id": "A003",
                    "target_name": "עצמאות תפקודית",
                    "direction": "OUTGOING",
                    "evidence_locator": "עמוד 6",
                    "certainty": "HIGH",
                }
            ],
        )

        result = CanonicalLocalRetriever(executor).answer("מהי עצמאות רגשית?")

        self.assertEqual("answered", result["status"])
        self.assertEqual("D4_CANONICAL_LOCAL_READ_ONLY", result["mode"])
        self.assertEqual("A002", result["matches"][0]["card_id"])
        self.assertIn("הגדרה קנונית", result["answer_text"])
        self.assertNotIn("עצמאות תפקודית", result["answer_text"])
        self.assertNotIn("ראו גם", result["answer_text"])
        self.assertEqual(1, len(result["canonical_relations"]))
        self.assertNotIn("SEE_ALSO", result["answer_text"])
        self.assertTrue(all("LLM" not in query for query, _ in executor.calls))

    def test_longest_phrase_wins_over_nested_shorter_term(self):
        executor = FakeExecutor(
            entries=[
                entry("A007", "מסוגלות"),
                entry("A008", "הרחבת המסוגלות"),
            ]
        )

        result = CanonicalLocalRetriever(executor).answer(
            "איך מוגדרת הרחבת המסוגלות בשיטת דרך?"
        )

        self.assertEqual("A008", result["matches"][0]["card_id"])
        self.assertEqual(1, len(result["matches"]))

    def test_alias_and_card_id_are_supported(self):
        executor = FakeExecutor(
            entries=[entry("A002", "עצמאות רגשית", ["מנהיגות פנימית"])]
        )
        retriever = CanonicalLocalRetriever(executor)

        alias_result = retriever.answer("מה פירוש מנהיגות פנימית?")
        card_result = retriever.answer("הצג את A002")

        self.assertEqual("A002", alias_result["matches"][0]["card_id"])
        self.assertEqual("A002", card_result["matches"][0]["card_id"])

    def test_quarantined_context_is_not_queried_by_runtime_retrieval(self):
        executor = FakeExecutor(
            entries=[entry("B034", "הגנות")],
            relations=[],
            quarantine=[
                {
                    "candidate_id": "CHUNKCAND-1",
                    "relation_type": "LEADS_TO",
                    "source_card_ids": ["B034"],
                    "target_card_ids": ["E010"],
                    "source_label": "הגנות",
                    "target_label": "תלות",
                    "quarantine_status": "READY_FOR_SEMANTIC_REVIEW",
                    "pair_mapping_status": "BOTH_ENDPOINTS_UNIQUE",
                    "automatic_promotion": False,
                    "eligible_for_canonical_relation": False,
                    "deidentified_excerpt": "קטע ראיה ללא מידע מטופל.",
                    "data_classification": "NO_PATIENT_DATA",
                }
            ],
        )

        result = CanonicalLocalRetriever(executor).answer("מהן הגנות?")

        self.assertEqual([], result["canonical_relations"])
        self.assertEqual([], result["quarantined_context"])
        self.assertFalse(
            any("local_qa:quarantine" in query for query, _ in executor.calls)
        )
        self.assertNotIn("קטע ראיה ללא מידע מטופל", result["answer_text"])

    def test_only_approved_d4_entries_are_eligible(self):
        executor = FakeExecutor(
            entries=[
                entry("A002", "עצמאות רגשית"),
                entry("X999", "עצמאות רגשית חלופית", status="DRAFT"),
            ]
        )

        result = CanonicalLocalRetriever(executor).answer("עצמאות רגשית")

        self.assertEqual(["A002"], [item["card_id"] for item in result["matches"]])

    def test_case_question_uses_balanced_retrieval_lenses(self):
        executor = FakeExecutor(
            entries=[
                entry("D046", "מפתח הנתינה והקבלה"),
                entry("C017", "קבלה"),
                entry("E012", "נזקקות"),
                entry("A002", "עצמאות רגשית"),
                entry("G059", "קבלה בקונפליקט"),
                entry("D003", "חוויה מול מציאות"),
                entry("B003", "מנהל"),
                entry("C002", "רגש בסיס"),
                entry("A006", "עבודה הפעלתית"),
                entry("Z001", "מושג לא קשור"),
            ]
        )

        result = CanonicalLocalRetriever(executor).answer(
            "בתרחיש לימודי אדם מתקשה לקבל עזרה ותמיכה, אך נסוג "
            "כאשר מציעים לו עזרה ורוצה להישאר עצמאי. מה כדאי לברר?"
        )

        selected = {item["entry_name"] for item in result["matches"]}
        self.assertTrue(
            {
                "מפתח הנתינה והקבלה",
                "נזקקות",
                "עצמאות רגשית",
                "חוויה מול מציאות",
                "מנהל",
                "רגש בסיס",
            }.issubset(selected)
        )

    def test_database_failure_is_fail_closed_and_user_readable(self):
        executor = FakeExecutor(failure=Neo4jUnavailable("offline"))

        result = CanonicalLocalRetriever(executor).answer("מהי דרך?")

        self.assertEqual("database_unavailable", result["status"])
        self.assertEqual([], result["matches"])
        self.assertIn("Neo4j", result["answer_text"])

    def test_read_only_client_rejects_mutating_cypher(self):
        for query in (
            "CREATE (n:Unsafe)",
            "MATCH (n) SET n.x = 1",
            "MATCH (n) DETACH DELETE n",
            "MERGE (n:Unsafe {id: 1}) RETURN n",
        ):
            with self.subTest(query=query):
                with self.assertRaises(ValueError):
                    ReadOnlyNeo4jHttpClient.validate_read_only(query)

        ReadOnlyNeo4jHttpClient.validate_read_only(
            "MATCH (n:GlossaryEntry) RETURN n.card_id LIMIT 1"
        )

    def test_source_evidence_is_restricted_to_primary_method_sources(self):
        self.assertIn("evidence.source_authority = 'METHOD_PRIMARY'", SOURCE_EVIDENCE_QUERY)


if __name__ == "__main__":
    unittest.main()
