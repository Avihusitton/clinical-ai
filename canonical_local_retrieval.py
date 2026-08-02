# -*- coding: utf-8 -*-
"""Deterministic, read-only retrieval over the signed D4 dictionary graph."""

from __future__ import annotations

import base64
import json
import re
import urllib.error
import urllib.request
from typing import Any, Protocol


DICTIONARY_RELEASE_ID = "D4-99F53565A7BCC45E"
MODE = "D4_CANONICAL_LOCAL_READ_ONLY"
CANONICAL_RELATION_TYPES = (
    "PARENT_OF",
    "CHILD_OF",
    "SEE_ALSO",
    "PARALLEL_TO",
    "RELATED_TECHNIQUE",
    "RELATED_EXERCISE",
    "DISTINGUISHED_FROM",
)
RELATION_LABELS = {
    "PARENT_OF": "מושג־אב של",
    "CHILD_OF": "מושג־בן של",
    "SEE_ALSO": "ראו גם",
    "PARALLEL_TO": "מקביל ל־",
    "RELATED_TECHNIQUE": "טכניקה קשורה",
    "RELATED_EXERCISE": "תרגיל קשור",
    "DISTINGUISHED_FROM": "נבדל מ־",
}

LIST_ENTRIES_QUERY = """
/* local_qa:list_entries */
MATCH (entry:DictionaryEntity:GlossaryEntry)
WHERE entry.dictionary_release_id = $release_id
  AND entry.status = 'APPROVED'
RETURN entry.card_id AS card_id,
       entry.entry_name AS entry_name,
       entry.entry_type AS entry_type,
       entry.status AS status,
       coalesce(entry.aliases_and_spellings, []) AS aliases,
       coalesce(entry.unified_definition, '') AS definition,
       coalesce(entry.source_based_definition, '') AS source_based_definition,
       coalesce(entry.exact_source, '') AS exact_source,
       coalesce(entry.short_example, '') AS short_example,
       coalesce(entry.common_mistakes, '') AS common_mistakes,
       coalesce(entry.editorial_note, '') AS editorial_note,
       coalesce(entry.therapeutic_contexts, []) AS therapeutic_contexts,
       coalesce(entry.related_techniques, []) AS related_techniques,
       coalesce(entry.related_exercises, []) AS related_exercises,
       coalesce(entry.parent_terms, []) AS parent_terms,
       coalesce(entry.child_terms, []) AS child_terms,
       coalesce(entry.distinguish_from, []) AS distinguish_from,
       coalesce(entry.parallel_terms, []) AS parallel_terms,
       coalesce(entry.see_also, []) AS see_also,
       coalesce(entry.certainty, '') AS certainty
"""

RELATIONS_QUERY = """
/* local_qa:relations */
MATCH (entry:DictionaryEntity:GlossaryEntry)-[relation]-(related:DictionaryEntity:GlossaryEntry)
WHERE entry.card_id IN $card_ids
  AND entry.dictionary_release_id = $release_id
  AND related.dictionary_release_id = $release_id
  AND relation.dictionary_release_id = $release_id
  AND relation.review_status = 'APPROVED_DICTIONARY'
  AND type(relation) IN $relation_types
RETURN entry.card_id AS source_id,
       entry.entry_name AS source_name,
       type(relation) AS relation_type,
       related.card_id AS target_id,
       related.entry_name AS target_name,
       coalesce(related.unified_definition, '') AS target_definition,
       coalesce(related.source_based_definition, '') AS target_source_based_definition,
       CASE WHEN startNode(relation) = entry THEN 'OUTGOING' ELSE 'INCOMING' END AS direction,
       coalesce(relation.evidence_locator, '') AS evidence_locator,
       coalesce(relation.certainty, '') AS certainty
ORDER BY source_id, relation_type, target_name
LIMIT 80
"""

SOURCE_EVIDENCE_QUERY = """
/* local_qa:source_evidence */
MATCH (entry:DictionaryEntity:GlossaryEntry)-[evidence:EVIDENCED_BY]->
      (source:DictionaryEntity:SourceDocument)
WHERE entry.card_id IN $card_ids
  AND entry.dictionary_release_id = $release_id
  AND evidence.dictionary_release_id = $release_id
  AND evidence.source_authority = 'METHOD_PRIMARY'
RETURN entry.card_id AS card_id,
       entry.entry_name AS entry_name,
       source.source_document_id AS source_document_id,
       source.source_type AS source_type,
       source.source_authority AS source_authority,
       evidence.evidence_locator AS evidence_locator,
       evidence.evidence_type AS evidence_type,
       evidence.certainty AS certainty
ORDER BY card_id, source_document_id, evidence_locator
LIMIT 80
"""

HEALTH_QUERY = "/* local_qa:health */ RETURN 1 AS ok"

_MUTATION_PATTERN = re.compile(
    r"\b(CREATE|MERGE|SET|DELETE|REMOVE|DROP|FOREACH|LOAD\s+CSV)\b",
    re.IGNORECASE,
)
_NORMALIZE_PATTERN = re.compile(r"[^\w\u0590-\u05ff]+", re.UNICODE)
_STOPWORDS = {
    "איך",
    "איפה",
    "איזה",
    "אל",
    "אם",
    "את",
    "בשיטת",
    "דרך",
    "האם",
    "הגדר",
    "הגדרה",
    "הצג",
    "מה",
    "מהו",
    "מהי",
    "מהם",
    "מהן",
    "מי",
    "על",
    "אדם",
    "אותו",
    "אחר",
    "אחרים",
    "אחרת",
    "אבל",
    "אך",
    "אילו",
    "איזו",
    "איזה",
    "בעיקר",
    "בו",
    "בפועל",
    "הוא",
    "המשך",
    "כעת",
    "כדאי",
    "כאשר",
    "לפני",
    "לפי",
    "לו",
    "לימודי",
    "נמסר",
    "עוד",
    "עבודה",
    "פרט",
    "פרטים",
    "חסר",
    "חסרים",
    "רוצה",
    "תרחיש",
    "של",
}

_HEBREW_PREFIXES = (
    "כש",
    "מש",
    "בש",
    "וה",
    "וב",
    "ול",
    "לה",
    "מה",
    "שה",
    "ש",
    "ב",
    "כ",
    "ל",
    "מ",
    "ו",
    "י",
)
_HEBREW_SUFFIXES = (
    "יהם",
    "יהן",
    "יות",
    "יים",
    "ים",
    "ות",
    "יה",
    "יו",
    "נו",
    "כם",
    "כן",
    "ה",
    "ו",
    "י",
)

_RETRIEVAL_LENS_RULES = (
    (
        re.compile(r"קבל|עזר|תמכ|נתינ|נותנ"),
        "נתינה קבלה נזקקות עצמאות רגשית",
        (
            "מפתח הנתינה והקבלה",
            "קבלה",
            "נזקקות",
            "עצמאות רגשית",
        ),
    ),
    (
        re.compile(r"פער|אבל|מצד שני|אך|סותר"),
        "קונפליקט חוויה מציאות",
        (
            "קבלה בקונפליקט",
            "חוויה מול מציאות",
        ),
    ),
    (
        re.compile(r"נסוג|נמנע|דוחה|אוטומט|התנהג"),
        "מנהל רגש בסיס עבודה הפעלתית עבודה מהותית",
        (
            "מנהל",
            "רגש בסיס",
            "עבודה הפעלתית",
            "עבודה מהותית",
        ),
    ),
)


class Neo4jUnavailable(RuntimeError):
    """The local graph cannot be reached or returned an invalid response."""


class QueryExecutor(Protocol):
    def run(self, cypher: str, parameters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        ...


class ReadOnlyNeo4jHttpClient:
    """Small stdlib-only client for Neo4j's local transactional HTTP endpoint."""

    def __init__(
        self,
        username: str,
        password: str,
        http_uri: str = "http://127.0.0.1:7474",
        database: str = "neo4j",
        timeout_seconds: float = 8.0,
    ):
        if not password:
            raise ValueError("Neo4j password is required")
        self.endpoint = f"{http_uri.rstrip('/')}/db/{database}/tx/commit"
        token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
        self._authorization = f"Basic {token}"
        self.timeout_seconds = timeout_seconds

    @staticmethod
    def validate_read_only(cypher: str) -> None:
        if _MUTATION_PATTERN.search(cypher):
            raise ValueError("Mutating Cypher is forbidden in local Q&A mode")

    def run(
        self,
        cypher: str,
        parameters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        self.validate_read_only(cypher)
        payload = json.dumps(
            {"statements": [{"statement": cypher, "parameters": parameters or {}}]},
            ensure_ascii=False,
        ).encode("utf-8")
        request = urllib.request.Request(
            self.endpoint,
            data=payload,
            headers={
                "Authorization": self._authorization,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
            raise Neo4jUnavailable("Local Neo4j is unavailable") from exc

        errors = body.get("errors") or []
        if errors:
            message = errors[0].get("message", "Neo4j query failed")
            raise Neo4jUnavailable(message)
        results = body.get("results") or []
        if not results:
            return []
        columns = results[0].get("columns") or []
        return [
            dict(zip(columns, item.get("row") or []))
            for item in results[0].get("data") or []
        ]


def _normalize(text: str) -> str:
    return " ".join(_NORMALIZE_PATTERN.sub(" ", (text or "").casefold()).split())


def _content_tokens(text: str) -> set[str]:
    return {
        token
        for token in _normalize(text).split()
        if len(token) > 1 and token not in _STOPWORDS
    }


def _flatten_text(value: Any) -> str:
    if isinstance(value, (list, tuple, set)):
        return " ".join(_flatten_text(item) for item in value)
    if isinstance(value, dict):
        return " ".join(_flatten_text(item) for item in value.values())
    return str(value or "")


def _concept_token(token: str) -> str:
    value = _normalize(token)
    if not value:
        return ""
    for prefix in _HEBREW_PREFIXES:
        if value.startswith(prefix) and len(value) - len(prefix) >= 3:
            value = value[len(prefix):]
            break
    for suffix in _HEBREW_SUFFIXES:
        if value.endswith(suffix) and len(value) - len(suffix) >= 3:
            value = value[:-len(suffix)]
            break
    return value


def _concept_tokens(text: str) -> set[str]:
    tokens = _content_tokens(text)
    return tokens | {
        concept
        for concept in (_concept_token(token) for token in tokens)
        if len(concept) >= 3
    }


def _expand_question_for_retrieval(question: str) -> str:
    normalized = _normalize(question)
    expansions = [
        terms
        for pattern, terms, _preferred_names in _RETRIEVAL_LENS_RULES
        if pattern.search(normalized)
    ]
    return " ".join([question, *expansions])


def _preferred_lens_names(question: str) -> list[str]:
    normalized = _normalize(question)
    names: list[str] = []
    for pattern, _terms, preferred_names in _RETRIEVAL_LENS_RULES:
        if pattern.search(normalized):
            names.extend(preferred_names)
    return list(dict.fromkeys(_normalize(name) for name in names))


def _field_overlap_score(
    question_tokens: set[str],
    value: Any,
    *,
    weight: float,
) -> float:
    field_tokens = _concept_tokens(_flatten_text(value))
    if not field_tokens:
        return 0.0
    overlap = question_tokens & field_tokens
    if not overlap:
        return 0.0
    coverage = len(overlap) / max(1, len(question_tokens))
    return len(overlap) * weight * 25.0 + coverage * weight * 20.0


def _match_score(
    question: str,
    row: dict[str, Any],
    *,
    allow_direct: bool = True,
) -> float:
    normalized_question = _normalize(question)
    question_tokens = _concept_tokens(question)
    card_id = str(row.get("card_id") or "").casefold()
    name = _normalize(str(row.get("entry_name") or ""))
    aliases = [_normalize(str(alias)) for alias in row.get("aliases") or []]

    if allow_direct and card_id and card_id in normalized_question.split():
        return 2000.0
    if allow_direct and name and name == normalized_question:
        return 1500.0 + len(name)
    if allow_direct and name and name in normalized_question:
        return 1000.0 + len(name) * 10
    contained_aliases = [alias for alias in aliases if alias and alias in normalized_question]
    if allow_direct and contained_aliases:
        longest = max(contained_aliases, key=len)
        return 900.0 + len(longest) * 10

    if not question_tokens:
        return 0.0
    weighted_fields = (
        (row.get("entry_name"), 9.0),
        (row.get("aliases"), 8.0),
        (row.get("source_based_definition"), 4.5),
        (row.get("definition"), 4.0),
        (row.get("common_mistakes"), 3.0),
        (row.get("short_example"), 2.5),
        (row.get("therapeutic_contexts"), 2.5),
        (row.get("related_techniques"), 2.0),
        (row.get("related_exercises"), 2.0),
        (row.get("distinguish_from"), 2.0),
        (row.get("parallel_terms"), 1.5),
        (row.get("parent_terms"), 1.2),
        (row.get("child_terms"), 1.2),
        (row.get("see_also"), 1.0),
        (row.get("editorial_note"), 0.8),
    )
    score = sum(
        _field_overlap_score(question_tokens, value, weight=weight)
        for value, weight in weighted_fields
    )
    return score


def _direct_match_phrases(question: str, row: dict[str, Any]) -> list[str]:
    normalized_question = _normalize(question)
    phrases = []
    card_id = str(row.get("card_id") or "").casefold()
    if card_id and card_id in normalized_question.split():
        phrases.append(card_id)
    name = _normalize(str(row.get("entry_name") or ""))
    if name and name in normalized_question:
        phrases.append(name)
    phrases.extend(
        alias
        for alias in (
            _normalize(str(value)) for value in row.get("aliases") or []
        )
        if alias and alias in normalized_question
    )
    return phrases


class CanonicalLocalRetriever:
    def __init__(self, executor: QueryExecutor):
        self.executor = executor

    def health(self) -> bool:
        try:
            return self.executor.run(HEALTH_QUERY) == [{"ok": 1}]
        except Neo4jUnavailable:
            return False

    def answer(self, question: str) -> dict[str, Any]:
        question = (question or "").strip()
        if not question:
            return self._empty_result(
                "not_found",
                "לא הוזנה שאלה. אפשר לשאול על מושג, הגדרה או קשר בשיטת דרך.",
            )

        try:
            rows = self.executor.run(
                LIST_ENTRIES_QUERY,
                {"release_id": DICTIONARY_RELEASE_ID},
            )
            matches = self._rank_matches(question, rows)
            if not matches:
                return self._empty_result(
                    "not_found",
                    "לא נמצא במילון D4 מושג מאושר שמתאים לשאלה.",
                )

            card_ids = [item["card_id"] for item in matches]
            relations = self.executor.run(
                RELATIONS_QUERY,
                {
                    "card_ids": card_ids,
                    "release_id": DICTIONARY_RELEASE_ID,
                    "relation_types": list(CANONICAL_RELATION_TYPES),
                },
            )
            relations = [
                {
                    **relation,
                    "relation_label": RELATION_LABELS.get(
                        relation.get("relation_type", ""),
                        "קשר מאושר",
                    ),
                }
                for relation in relations
            ]
            source_evidence = self.executor.run(
                SOURCE_EVIDENCE_QUERY,
                {
                    "card_ids": card_ids,
                    "release_id": DICTIONARY_RELEASE_ID,
                },
            )
        except Neo4jUnavailable:
            return self._empty_result(
                "database_unavailable",
                "מסד הנתונים המקומי Neo4j אינו זמין כרגע. לא בוצעה תשובה חלקית.",
            )

        result = {
            "status": "answered",
            "mode": MODE,
            "release_id": DICTIONARY_RELEASE_ID,
            "matches": matches,
            "canonical_relations": relations,
            "approved_source_evidence": source_evidence,
            "quarantined_context": [],
            "limitations": [
                "התשובה מבוססת על מילון D4, קשרים ומראי־מקום שאושרו בלבד.",
                "חומר מוסגר ומועמדי קשר אינם משתתפים במסלול השאלות.",
                "המערכת אינה נותנת אבחנה או המלצה קלינית.",
            ],
        }
        result["answer_text"] = self._compose_answer(result)
        return result

    @staticmethod
    def _rank_matches(question: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        approved = [row for row in rows if row.get("status") == "APPROVED"]
        direct = [
            (row, _direct_match_phrases(question, row))
            for row in approved
        ]
        direct = [(row, phrases) for row, phrases in direct if phrases]
        if direct:
            all_phrases = {
                phrase
                for _, phrases in direct
                for phrase in phrases
            }
            direct = [
                (row, phrases)
                for row, phrases in direct
                if any(
                    not any(
                        phrase != other and phrase in other
                        for other in all_phrases
                    )
                    for phrase in phrases
                )
            ]
            direct.sort(
                key=lambda item: (
                    -max(len(phrase) for phrase in item[1]),
                    str(item[0].get("card_id") or ""),
                )
            )
            direct_rows = [row for row, _ in direct[:10]]
            if len(_content_tokens(question)) <= 8:
                return direct_rows
        else:
            direct_rows = []

        semantic_question = _expand_question_for_retrieval(question)
        scored = [
            (_match_score(semantic_question, row, allow_direct=False), row)
            for row in approved
        ]
        scored = [(score, row) for score, row in scored if score > 0]
        scored.sort(
            key=lambda item: (
                -item[0],
                -len(str(item[1].get("entry_name") or "")),
                str(item[1].get("card_id") or ""),
            )
        )
        if not scored:
            return direct_rows
        top_score = scored[0][0]
        threshold = max(30.0, top_score * 0.32)
        direct_ids = {
            str(row.get("card_id") or "")
            for row in direct_rows
        }
        semantic_rows = [
            row
            for score, row in scored
            if score >= threshold
            and str(row.get("card_id") or "") not in direct_ids
        ]
        selected = list(direct_rows)
        selected_ids = {
            str(row.get("card_id") or "")
            for row in selected
        }
        if semantic_rows and len(selected) < 10:
            top_row = semantic_rows[0]
            selected.append(top_row)
            selected_ids.add(str(top_row.get("card_id") or ""))
        for preferred_name in _preferred_lens_names(question):
            if len(selected) >= 10:
                break
            candidate = next(
                (
                    row
                    for row in semantic_rows
                    if str(row.get("card_id") or "") not in selected_ids
                    and _normalize(str(row.get("entry_name") or ""))
                    == preferred_name
                ),
                None,
            )
            if candidate is None:
                candidate = next(
                    (
                        row
                        for row in semantic_rows
                        if str(row.get("card_id") or "") not in selected_ids
                        and preferred_name
                        in _normalize(str(row.get("entry_name") or ""))
                    ),
                    None,
                )
            if candidate is None:
                candidate = next(
                    (
                        row
                        for row in approved
                        if str(row.get("card_id") or "") not in selected_ids
                        and _normalize(str(row.get("entry_name") or ""))
                        == preferred_name
                    ),
                    None,
                )
            if candidate is not None:
                selected.append(candidate)
                selected_ids.add(str(candidate.get("card_id") or ""))
        for row in semantic_rows:
            if len(selected) >= 10:
                break
            card_id = str(row.get("card_id") or "")
            if card_id not in selected_ids:
                selected.append(row)
                selected_ids.add(card_id)
        return selected

    @staticmethod
    def _compose_answer(result: dict[str, Any]) -> str:
        lines = ["המידע הקנוני שנמצא:"]
        for match in result["matches"]:
            definition = (
                match.get("definition")
                or match.get("source_based_definition")
                or "לא הוזנה הגדרה מאושרת."
            )
            lines.append(
                f"{match['entry_name']} ({match['card_id']}): {definition}"
            )
            if match.get("exact_source"):
                lines.append(f"  מקור: {match['exact_source']}")

        lines.append("")
        lines.append(
            "זהו מענה מילוני ישיר. לקבלת ניסוח מקצועי שמחבר את הידע לבקשה, "
            "יש לבחור באפשרות המענה בסיוע AI."
        )
        return "\n".join(lines)

    @staticmethod
    def _empty_result(status: str, answer_text: str) -> dict[str, Any]:
        return {
            "status": status,
            "mode": MODE,
            "release_id": DICTIONARY_RELEASE_ID,
            "answer_text": answer_text,
            "matches": [],
            "canonical_relations": [],
            "approved_source_evidence": [],
            "quarantined_context": [],
            "limitations": [],
        }
