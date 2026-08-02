# -*- coding: utf-8 -*-
"""
Ingestion Pipeline — "המוח המערכתי" (Hebrew Clinical GraphRAG)
================================================================
קבצי Word -> דה-דופליקציה -> אנונימיזציה (LLM, שער קשיח) -> עוגני זמן
(Rolling State) -> Chunking -> מועמדי Entity Linking (דטרמיניסטי) ->
סיווג הקשר טיפולי (LLM) -> אימות בינארי (LLM) -> קשרי Exercise-Concept
ו-Concept-Concept -> טעינה ל-Neo4j -> ניהול קבצים (Inbox/Archive/Error).

עקרונות על (מהביקורת של פייבל):
1.  שער קשיח ל-De-identification: טקסט גולמי לעולם לא ממשיך בצינור.
    שינוי לעומת הגרסה המקורית: בלי מפתח LLM אמיתי, de-id נכשל במפורש
    (ולא "מדמה" ניקוי) - כך שאי אפשר בטעות להריץ על דאטה אמיתי בלי
    אנונימיזציה אמיתית.
2.  אין הרעלת מצב שקטה: כל עדכון עוגן זמן נרשם בלוג + דוח עוגנים.
3.  אין זיהום טיפוסים: lesson_date הוא date/None, סטטוס בשדה enum נפרד.
4.  LINKED_TO (הקשר שהשליפה משתמשת בו) נוצר רק אחרי אימות LLM = yes.
    HAS_CANDIDATE (טרם אומת) נשמר בנפרד - אף פעם לא מתבלבל עם קשר מאושר.
5.  Exercise לעולם לא ישתתף בטראברסל ההיסקי - נאכף בשכבת ה-retrieval.
6.  אידמפוטנטיות: טעינה כפולה לא מכפילה נתונים (MERGE על מפתחות יציבים).
7.  כישלון של קובץ בודד לא מפיל ריצה: מדלגים ומעבירים ל-docs_error.

תלויות:  pip install -r requirements.txt
הרצה לבדיקה (בלי API, בלי Neo4j):
    python ingestion_pipeline.py --dry-run --mock-llm --limit 3
הרצה אמיתית:
    python ingestion_pipeline.py
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import hashlib
import json
import logging
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Iterable, Optional

try:
    import docx  # python-docx
except ImportError:  # pragma: no cover
    sys.exit("חסרה תלות: pip install python-docx")

try:
    from rapidfuzz import fuzz
except ImportError:  # pragma: no cover
    sys.exit("חסרה תלות: pip install rapidfuzz")

import file_manager
from config import Config
from llm_client import LLMClient, LLMError

logging.basicConfig(level=logging.INFO,
                     format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s")
log = logging.getLogger("ingestion")


# ---------------------------------------------------------------------------
# מודל הנתונים הפנימי
# ---------------------------------------------------------------------------

class TemporalStatus(str, Enum):
    ANCHORED = "anchored"
    TIMELESS = "timeless"
    LOW_CONFIDENCE = "low_confidence"


@dataclass
class TimeAnchor:
    lesson_number: Optional[int]
    lesson_date: Optional[dt.date]
    source_line: str
    paragraph_index: int
    score: int


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    text: str
    paragraph_range: tuple[int, int]
    lesson_number: Optional[int]
    lesson_date: Optional[dt.date]
    temporal_status: TemporalStatus
    anchor_distance: int
    modality: str = "general"  # individual / couples / family / general
    concept_candidates: list[dict] = field(default_factory=list)
    exercise_candidates: list[dict] = field(default_factory=list)
    verified_links: list[dict] = field(default_factory=list)   # verdict == yes
    unclear_links: list[dict] = field(default_factory=list)    # verdict == unclear -> חדר המתנה


@dataclass
class DocResult:
    doc_id: str
    path: str
    status: str  # ok / failed_read / failed_deid / duplicate
    anchors: list[TimeAnchor] = field(default_factory=list)
    chunks: list[Chunk] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# שלב 0: קריאת קבצים ודה-דופליקציה
# ---------------------------------------------------------------------------

class DocxReader:
    @staticmethod
    def read(path: Path) -> list[dict]:
        document = docx.Document(str(path))
        paragraphs = []
        for p in document.paragraphs:
            text = p.text.strip()
            if not text:
                continue
            style_name = (p.style.name or "") if p.style else ""
            runs_with_text = [r for r in p.runs if r.text.strip()]
            all_bold = bool(runs_with_text) and all(r.bold for r in runs_with_text)
            paragraphs.append({
                "text": text,
                "is_heading_style": style_name.lower().startswith("heading") or "כותרת" in style_name,
                "is_bold": all_bold,
            })
        return paragraphs

    @staticmethod
    def content_hash(paragraphs: list[dict]) -> str:
        joined = "".join(p["text"] for p in paragraphs)
        normalized = re.sub(r"\s+", "", joined)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# שלב 1: De-identification — שער קשיח, מגובה LLM אמיתי
# ---------------------------------------------------------------------------

class DeIdentifier:
    """
    חוזה קשיח: deidentify() מחזירה טקסט נקי או זורקת DeIdError.
    אין מצב שבו טקסט גולמי ממשיך בצינור אחרי כישלון - כולל "אין מפתח API".
    """

    class DeIdError(RuntimeError):
        pass

    _PHONE_RE = re.compile(r"\b0\d{1,2}[- ]?\d{7}\b")
    _ID_RE = re.compile(r"\b\d{9}\b")

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def deidentify(self, text: str) -> str:
        try:
            cleaned = self.llm.deidentify(text)
        except LLMError as exc:
            raise self.DeIdError(f"קריאת de-id נכשלה: {exc}") from exc
        cleaned = self._PHONE_RE.sub("[טלפון]", cleaned)
        cleaned = self._ID_RE.sub("[ת.ז.]", cleaned)
        return cleaned


# ---------------------------------------------------------------------------
# שלב 2: זיהוי עוגני זמן — מסווג מבוסס ניקוד
# ---------------------------------------------------------------------------

class TimeAnchorDetector:
    LESSON_RE = re.compile(r"(?:ש[יי]?עור|מפגש)\s*(?:מס'?|מספר)?\s*(\d{1,3})")
    DATE_RE = re.compile(r"\b(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})\b")
    NARRATIVE_HINTS = ("סיפר", "סיפרה", "בשנת", "כשהיה", "כשהיתה", "לפני", "אז ב")

    def __init__(self, cfg: Config):
        self.cfg = cfg

    def detect(self, par: dict, index: int) -> Optional[TimeAnchor]:
        text = par["text"]
        lesson_match = self.LESSON_RE.search(text)
        date_match = self.DATE_RE.search(text)
        if not lesson_match and not date_match:
            return None

        score = 0
        if lesson_match:
            score += 2
        if len(text) <= self.cfg.header_max_chars:
            score += 1
        if par["is_heading_style"]:
            score += 2
        if par["is_bold"]:
            score += 1
        if date_match and self._date_dominates_line(text, date_match):
            score += 1

        if any(h in text for h in self.NARRATIVE_HINTS):
            score -= 3
        if date_match and not lesson_match and len(text) > self.cfg.header_max_chars:
            score -= 2

        if score < self.cfg.anchor_min_score:
            return None

        return TimeAnchor(
            lesson_number=int(lesson_match.group(1)) if lesson_match else None,
            lesson_date=self._parse_date(date_match) if date_match else None,
            source_line=text[:120], paragraph_index=index, score=score,
        )

    @staticmethod
    def _date_dominates_line(text: str, m: re.Match) -> bool:
        return (len(m.group(0)) / max(len(text), 1)) > 0.3

    @staticmethod
    def _parse_date(m: re.Match) -> Optional[dt.date]:
        day, month, year = (int(g) for g in m.groups())
        if year < 100:
            year += 2000
        try:
            return dt.date(year, month, day)
        except ValueError:
            log.warning("תאריך לא חוקי בטקסט: %s", m.group(0))
            return None


class RollingTimeState:
    def __init__(self):
        self.current: Optional[TimeAnchor] = None
        self.distance: int = 0
        self.monotonicity_broken: bool = False
        self.warnings: list[str] = []

    def update(self, anchor: TimeAnchor) -> None:
        if self.current:
            prev_n, new_n = self.current.lesson_number, anchor.lesson_number
            if prev_n is not None and new_n is not None:
                if new_n < prev_n:
                    msg = f"שבירת מונוטוניות: שיעור {new_n} אחרי שיעור {prev_n} (שורה: '{anchor.source_line}')"
                    self.warnings.append(msg)
                    log.warning(msg)
                    self.monotonicity_broken = True
                elif new_n > prev_n + 1:
                    self.warnings.append(f"דילוג במספור: {prev_n} -> {new_n}. שיעור חסר או עוגן שפוספס?")
        self.current = anchor
        self.distance = 0
        self.monotonicity_broken = False

    def step(self) -> None:
        self.distance += 1

    def stamp(self) -> tuple[Optional[int], Optional[dt.date], TemporalStatus, int]:
        if self.current is None:
            return None, None, TemporalStatus.TIMELESS, 0
        status = TemporalStatus.ANCHORED
        if self.distance > 60 or self.monotonicity_broken:
            status = TemporalStatus.LOW_CONFIDENCE
        return self.current.lesson_number, self.current.lesson_date, status, self.distance


# ---------------------------------------------------------------------------
# שלב 3: Chunking — לא חוצה גבולות עוגן
# ---------------------------------------------------------------------------

class Chunker:
    SENTENCE_END_RE = re.compile(r"[.!?׃]\s")

    def __init__(self, cfg: Config, detector: TimeAnchorDetector):
        self.cfg = cfg
        self.detector = detector

    def chunk_document(self, doc_id: str, paragraphs: list[dict]
    ) -> tuple[list[Chunk], list[TimeAnchor], list[str]]:
        state = RollingTimeState()
        anchors: list[TimeAnchor] = []
        chunks: list[Chunk] = []
        buffer: list[str] = []
        buf_start = 0
        overlap_text = ""

        def flush(end_index: int) -> None:
            nonlocal overlap_text
            if not buffer:
                return
            text = (overlap_text + "\n" + "\n".join(buffer)) if overlap_text else "\n".join(buffer)
            lesson_n, lesson_d, status, dist = state.stamp()
            parts = list(self._soft_split(text))
            for part_i, part in enumerate(parts):
                cid = hashlib.sha256(f"{doc_id}|{buf_start}|{part_i}|{part[:64]}".encode()).hexdigest()[:24]
                chunks.append(Chunk(
                    chunk_id=cid, doc_id=doc_id, text=part,
                    paragraph_range=(buf_start, end_index),
                    lesson_number=lesson_n, lesson_date=lesson_d,
                    temporal_status=status, anchor_distance=dist,
                ))
            if parts:
                last = parts[-1]
                overlap_text = last[-self.cfg.chunk_overlap_chars:] if len(last) > self.cfg.chunk_overlap_chars else last
            buffer.clear()

        for i, par in enumerate(paragraphs):
            anchor = self.detector.detect(par, i)
            if anchor:
                flush(i - 1)
                overlap_text = ""
                state.update(anchor)
                anchors.append(anchor)
                buf_start = i + 1
                continue
            state.step()
            buffer.append(par["text"])
            if sum(len(t) for t in buffer) >= self.cfg.chunk_target_chars:
                flush(i)
                buf_start = i + 1
        flush(len(paragraphs) - 1)
        return chunks, anchors, state.warnings

    def _soft_split(self, text: str) -> Iterable[str]:
        if len(text) <= self.cfg.chunk_hard_max_chars:
            yield text
            return
        log.warning("chunk באורך %d תווים - מפצלים בגבול משפט הקרוב לסף", len(text))
        start = 0
        n = len(text)
        while start < n:
            target_end = min(start + self.cfg.chunk_target_chars, n)
            if target_end >= n:
                yield text[start:n]
                break
            window_start = max(start + int(self.cfg.chunk_target_chars * 0.6), start + 1)
            search_region = text[window_start:target_end + 200]
            match = None
            for m in self.SENTENCE_END_RE.finditer(search_region):
                match = m
            if match:
                cut = window_start + match.end()
            else:
                space_idx = text.rfind(" ", start, target_end)
                cut = space_idx + 1 if space_idx > start else target_end
            yield text[start:cut]
            start = cut


# ---------------------------------------------------------------------------
# שלב 4א: מועמדי Entity Linking — דטרמיניסטי (שער א')
# ---------------------------------------------------------------------------

class HebrewNormalizer:
    PREFIXES = ("וש", "וה", "וב", "ול", "וכ", "ומ", "ו", "ה", "ב", "ל", "כ", "מ", "ש")

    def __init__(self, lexicon_forms: set[str]):
        self.lexicon_forms = lexicon_forms

    @staticmethod
    def strip_niqqud(text: str) -> str:
        return "".join(c for c in unicodedata.normalize("NFD", text) if not unicodedata.combining(c))

    def normalize_token(self, token: str) -> str:
        token = self.strip_niqqud(token).strip('."\',:;()[]')
        if token in self.lexicon_forms:
            return token
        for pref in self.PREFIXES:
            if token.startswith(pref):
                stripped = token[len(pref):]
                if stripped in self.lexicon_forms:
                    return stripped
        return token


class CandidateGenerator:
    """
    lexicon: {"שם_קנוני": {"synonyms": [...], "definition": "..."}, ...}
    שינוי לעומת הגרסה המקורית: כל מושג נושא גם definition, כי שלב האימות
    הבינארי (LLM) צריך הגדרה כדי לשפוט yes/no/unclear - זה לא היה בקוד
    המקורי של פייבל.
    """

    def __init__(self, cfg: Config, lexicon: dict[str, dict], entity_type: str):
        self.cfg = cfg
        self.entity_type = entity_type
        self.definitions: dict[str, str] = {}
        self.form_to_canonical: dict[str, str] = {}
        for canonical, meta in lexicon.items():
            synonyms = meta.get("synonyms", [])
            self.definitions[canonical] = meta.get("definition", "")
            for form in [canonical, *synonyms]:
                self.form_to_canonical[HebrewNormalizer.strip_niqqud(form)] = canonical
        self.normalizer = HebrewNormalizer(set(self.form_to_canonical))
        self.sorted_forms = sorted(self.form_to_canonical, key=len, reverse=True)

    def candidates_for(self, text: str) -> list[dict]:
        found: dict[str, dict] = {}
        clean = HebrewNormalizer.strip_niqqud(text)

        for form in self.sorted_forms:
            if len(form) >= 4 and form in clean:
                canon = self.form_to_canonical[form]
                found.setdefault(canon, {"canonical": canon, "matched_form": form,
                                          "method": "exact", "score": 100,
                                          "entity_type": self.entity_type})

        for raw_token in re.findall(r"[\u0590-\u05FF]{3,}", clean):
            token = self.normalizer.normalize_token(raw_token)
            if token in self.form_to_canonical:
                canon = self.form_to_canonical[token]
                found.setdefault(canon, {"canonical": canon, "matched_form": raw_token,
                                          "method": "prefix_norm", "score": 95,
                                          "entity_type": self.entity_type})
                continue
            if len(token) >= 5:
                for form in self.sorted_forms:
                    if abs(len(form) - len(token)) > 3:
                        continue
                    ratio = fuzz.ratio(token, form)
                    if ratio >= self.cfg.fuzzy_threshold:
                        canon = self.form_to_canonical[form]
                        existing = found.get(canon)
                        if not existing or existing["score"] < ratio:
                            found[canon] = {"canonical": canon, "matched_form": raw_token,
                                             "method": "fuzzy", "score": ratio,
                                             "entity_type": self.entity_type}
        ranked = sorted(found.values(), key=lambda c: -c["score"])
        return ranked[: self.cfg.max_candidates_per_chunk]


# ---------------------------------------------------------------------------
# שלב 4ב: אימות בינארי (שער ב') + חדר המתנה
# ---------------------------------------------------------------------------

class CandidateVerifier:
    """
    לכל מועמד דטרמיניסטי: שאלת yes/no/unclear מול הגדרת הגלוסר.
    רק yes -> LINKED_TO. no -> נזרק. unclear -> חדר המתנה (waiting_room.json).
    זה בדיוק השלב שפייבל תיאר אבל לא כתב לו קוד ("שלב נפרד, מחוץ לקובץ הזה").
    """

    def __init__(self, llm: LLMClient, definitions: dict[str, str]):
        self.llm = llm
        self.definitions = definitions

    def verify_chunk(self, chunk: Chunk) -> None:
        for cand in chunk.concept_candidates + chunk.exercise_candidates:
            canon = cand["canonical"]
            definition = self.definitions.get(canon) or "(אין הגדרה בגלוסר - מומלץ למלא)"
            verdict = self.llm.verify_candidate(chunk.text, canon, definition)
            record = {**cand, "chunk_id": chunk.chunk_id, "verdict": verdict}
            if verdict == "yes":
                chunk.verified_links.append(record)
            elif verdict == "unclear":
                chunk.unclear_links.append(record)
            # "no" נזרק בשקט - זה בדיוק ההתנהגות המתוכננת


# ---------------------------------------------------------------------------
# שלב 5: קשרים ברמת הגרף — WORKS_ON (Exercise->Concept) ו-Concept<->Concept
# ---------------------------------------------------------------------------

class RelationshipExtractor:
    """
    פועל אחרי האימות, על verified_links בלבד (לא על מועמדים גולמיים).

    WORKS_ON: דטרמיניסטי - אם chunk מכיל גם תרגיל מאומת וגם מושג מאומת,
    זו כבר עדות ליישום (בדיוק כפי שפייבל תיאר: "יש לזה הקשר יישום, וזו
    ראיה"). אין צורך בקריאת LLM נוספת.

    קשרים תיאורטיים בין מושגים (is_symptom_of וכו'): כאן יש קריאת LLM,
    כי בניגוד ל-WORKS_ON זו לא רק "הופיעו יחד" אלא טענה תיאורטית
    ("X גורם ל-Y") שצריך שיפוט. בדיקת סתירה מתבצעת לפני טעינה.
    """

    def __init__(self, llm: LLMClient, allowed_types: list[str], contradictions: list[tuple[str, str]]):
        self.llm = llm
        self.allowed_types = allowed_types
        self.contradiction_pairs = {frozenset((a.lower(), b.lower())) for a, b in contradictions}

    def extract_works_on(self, chunk: Chunk) -> list[dict]:
        exercises = [c for c in chunk.verified_links if c["entity_type"] == "Exercise"]
        concepts = [c for c in chunk.verified_links if c["entity_type"] == "Concept"]
        edges = []
        for ex in exercises:
            for co in concepts:
                edges.append({
                    "exercise": ex["canonical"], "concept": co["canonical"],
                    "chunk_id": chunk.chunk_id, "modality": chunk.modality,
                    "lesson_number": chunk.lesson_number,
                    "lesson_date": chunk.lesson_date.isoformat() if chunk.lesson_date else None,
                    "quote": chunk.text[:300],
                })
        return edges

    def extract_concept_relationships(self, chunk: Chunk, existing_pairs: dict[frozenset, str]
                                       ) -> tuple[list[dict], list[dict]]:
        """מחזיר (קשרים_לטעינה, קונפליקטים_לבדיקה_אנושית)."""
        concepts = [c["canonical"] for c in chunk.verified_links if c["entity_type"] == "Concept"]
        concepts = sorted(set(concepts))
        to_load, conflicts = [], []
        for i in range(len(concepts)):
            for j in range(i + 1, len(concepts)):
                a, b = concepts[i], concepts[j]
                rel_type = self.llm.classify_relationship(a, b, chunk.text, self.allowed_types)
                if not rel_type:
                    continue
                pair_key = frozenset((a, b))
                edge = {
                    "concept_a": a, "concept_b": b, "type": rel_type.upper(),
                    "chunk_id": chunk.chunk_id, "modality": chunk.modality,
                    "lesson_number": chunk.lesson_number,
                    "lesson_date": chunk.lesson_date.isoformat() if chunk.lesson_date else None,
                    "quote": chunk.text[:300],
                }
                existing_type = existing_pairs.get(pair_key)
                if existing_type and frozenset((existing_type.lower(), rel_type.lower())) in self.contradiction_pairs:
                    conflicts.append({**edge, "conflicts_with_existing_type": existing_type})
                else:
                    to_load.append(edge)
                    existing_pairs[pair_key] = rel_type
        return to_load, conflicts


# ---------------------------------------------------------------------------
# שלב 6: טעינה ל-Neo4j — batched, אידמפוטנטי
# ---------------------------------------------------------------------------

class GraphLoader:
    """
    הערות סכמה קריטיות:
    - lesson_date נטען כ-date או null, לעולם לא כמחרוזת "timeless".
    - HAS_CANDIDATE (טרם אומת) ו-LINKED_TO (מאומת, yes) הם קשתות נפרדות.
    - Exercise לעולם לא משתתף בטראברסל ההיסקי - נאכף ב-retrieval.py, לא כאן.
    - טיפוסי קשר בין מושגים (IS_SYMPTOM_OF וכו') נטענים דינמית עם apoc.merge,
      אחרי ולידציה מחמירה של שם הטיפוס (רק אותיות/מספרים/קו תחתון) - מונע
      הזרקת Cypher דרך שם קשר לא צפוי.

    ⚠️ דורש את תוסף APOC מותקן ב-Neo4j (בגלל apoc.merge.node/relationship).
       זו הייתה כבר תלות סמויה בקוד המקורי של פייבל - כאן היא רק מפורשת יותר.
    """

    _SAFE_REL_TYPE = re.compile(r"^[A-Z_][A-Z0-9_]*$")

    SCHEMA_STATEMENTS = [
        "CREATE CONSTRAINT chunk_id IF NOT EXISTS FOR (c:Chunk) REQUIRE c.chunk_id IS UNIQUE",
        "CREATE CONSTRAINT concept_name IF NOT EXISTS FOR (k:Concept) REQUIRE k.canonical_name IS UNIQUE",
        "CREATE CONSTRAINT exercise_name IF NOT EXISTS FOR (e:Exercise) REQUIRE e.canonical_name IS UNIQUE",
    ]

    LOAD_CHUNKS_CYPHER = """
    UNWIND $rows AS row
    MERGE (c:Chunk {chunk_id: row.chunk_id})
    SET c.doc_id = row.doc_id, c.text = row.text,
        c.lesson_number = row.lesson_number,
        c.lesson_date = CASE WHEN row.lesson_date IS NULL THEN NULL ELSE date(row.lesson_date) END,
        c.temporal_status = row.temporal_status, c.anchor_distance = row.anchor_distance,
        c.modality = row.modality
    WITH c, row
    UNWIND row.candidates AS cand
    CALL apoc.merge.node([cand.entity_type], {canonical_name: cand.canonical}) YIELD node AS ent
    MERGE (c)-[r:HAS_CANDIDATE]->(ent)
    SET r.matched_form = cand.matched_form, r.method = cand.method, r.score = cand.score
    """

    LOAD_LINKED_CYPHER = """
    UNWIND $rows AS row
    MATCH (c:Chunk {chunk_id: row.chunk_id})
    CALL apoc.merge.node([row.entity_type], {canonical_name: row.canonical}) YIELD node AS ent
    MERGE (c)-[r:LINKED_TO]->(ent)
    SET r.matched_form = row.matched_form, r.method = row.method,
        r.modality = row.modality, r.lesson_number = row.lesson_number,
        r.lesson_date = CASE WHEN row.lesson_date IS NULL THEN NULL ELSE date(row.lesson_date) END
    """

    LOAD_WORKS_ON_CYPHER = """
    UNWIND $rows AS row
    MERGE (e:Exercise {canonical_name: row.exercise})
    MERGE (co:Concept {canonical_name: row.concept})
    MERGE (e)-[r:WORKS_ON {chunk_id: row.chunk_id}]->(co)
    SET r.modality = row.modality, r.lesson_number = row.lesson_number,
        r.lesson_date = CASE WHEN row.lesson_date IS NULL THEN NULL ELSE date(row.lesson_date) END,
        r.quote = row.quote
    """

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self._driver = None

    def connect(self) -> None:
        from neo4j import GraphDatabase
        self._driver = GraphDatabase.driver(self.cfg.neo4j_uri,
                                             auth=(self.cfg.neo4j_user, self.cfg.neo4j_password))
        with self._driver.session() as s:
            for stmt in self.SCHEMA_STATEMENTS:
                s.run(stmt)

    def load_chunks(self, chunks: list[Chunk]) -> int:
        assert self._driver, "יש לקרוא connect() קודם"
        rows = [self._chunk_row(c) for c in chunks]
        return self._batched_write(self.LOAD_CHUNKS_CYPHER, rows, "chunks")

    def load_linked(self, chunks: list[Chunk]) -> int:
        rows = []
        for c in chunks:
            for link in c.verified_links:
                rows.append({
                    "chunk_id": c.chunk_id, "entity_type": link["entity_type"],
                    "canonical": link["canonical"], "matched_form": link["matched_form"],
                    "method": link["method"], "modality": c.modality,
                    "lesson_number": c.lesson_number,
                    "lesson_date": c.lesson_date.isoformat() if c.lesson_date else None,
                })
        return self._batched_write(self.LOAD_LINKED_CYPHER, rows, "linked-to edges")

    def load_works_on(self, edges: list[dict]) -> int:
        return self._batched_write(self.LOAD_WORKS_ON_CYPHER, edges, "WORKS_ON edges")

    def load_concept_relationships(self, edges: list[dict]) -> int:
        """כל edge כאן עובר ולידציה על שם הטיפוס לפני שהוא נכנס לשאילתה."""
        assert self._driver, "יש לקרוא connect() קודם"
        loaded = 0
        with self._driver.session() as s:
            for e in edges:
                rel_type = e["type"]
                if not self._SAFE_REL_TYPE.match(rel_type):
                    log.error("שם טיפוס קשר לא תקין, מדלגים: %r", rel_type)
                    continue
                cypher = f"""
                MERGE (a:Concept {{canonical_name: $concept_a}})
                MERGE (b:Concept {{canonical_name: $concept_b}})
                MERGE (a)-[r:{rel_type} {{chunk_id: $chunk_id}}]->(b)
                SET r.modality = $modality, r.lesson_number = $lesson_number,
                    r.lesson_date = CASE WHEN $lesson_date IS NULL THEN NULL ELSE date($lesson_date) END,
                    r.quote = $quote
                """
                s.execute_write(lambda tx, params=e: tx.run(cypher, **params))
                loaded += 1
        log.info("נטענו %d קשרי מושג-מושג", loaded)
        return loaded

    def _batched_write(self, cypher: str, rows: list[dict], label: str) -> int:
        if not rows:
            return 0
        assert self._driver, "יש לקרוא connect() קודם"
        loaded = 0
        with self._driver.session() as s:
            for i in range(0, len(rows), self.cfg.neo4j_batch_size):
                batch = rows[i:i + self.cfg.neo4j_batch_size]
                s.execute_write(lambda tx: tx.run(cypher, rows=batch))
                loaded += len(batch)
                log.info("נטענו %d/%d %s", loaded, len(rows), label)
        return loaded

    @staticmethod
    def _chunk_row(c: Chunk) -> dict:
        return {
            "chunk_id": c.chunk_id, "doc_id": c.doc_id, "text": c.text,
            "lesson_number": c.lesson_number,
            "lesson_date": c.lesson_date.isoformat() if c.lesson_date else None,
            "temporal_status": c.temporal_status.value, "anchor_distance": c.anchor_distance,
            "modality": c.modality,
            "candidates": c.concept_candidates + c.exercise_candidates,
        }

    def close(self) -> None:
        if self._driver:
            self._driver.close()


# ---------------------------------------------------------------------------
# ה-Orchestrator
# ---------------------------------------------------------------------------

class Pipeline:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        file_manager.ensure_folders(cfg)
        self.llm = LLMClient(cfg.openrouter_api_key, cfg.llm_model, mock=cfg.mock_llm)
        self.deid = DeIdentifier(self.llm)
        self.detector = TimeAnchorDetector(cfg)
        self.chunker = Chunker(cfg, self.detector)

        glossary = self._load_lexicon(cfg.glossary_path, "concepts")
        exercises = self._load_lexicon(cfg.exercise_lexicon_path, "exercises")

        if not glossary:
            raise RuntimeError(
                f"גלוסר המושגים ריק או חסר: {cfg.glossary_path}. "
                "ההרצה נעצרת כדי למנוע טעינה ללא Entity Linking."
            )
        if not exercises:
            raise RuntimeError(
                f"לקסיקון התרגילים ריק או חסר: {cfg.exercise_lexicon_path}. "
                "ההרצה נעצרת כדי למנוע טעינה ללא Entity Linking."
            )

        self.concept_gen = CandidateGenerator(cfg, glossary, "Concept")
        self.exercise_gen = CandidateGenerator(cfg, exercises, "Exercise")

        definitions = {**self.concept_gen.definitions, **self.exercise_gen.definitions}
        self.verifier = CandidateVerifier(self.llm, definitions)

        rel_types, contradictions = self._load_relationship_types(cfg.relationship_types_path)
        self.rel_extractor = RelationshipExtractor(self.llm, rel_types, contradictions)

        self.seen_hashes: dict[str, str] = self._load_hash_registry(cfg.content_hash_registry_path)
        self.existing_concept_pairs: dict[frozenset, str] = {}  # לזיהוי סתירות תוך-ריצה

    @staticmethod
    def _load_hash_registry(path: Path) -> dict[str, str]:
        if not path.exists():
            return {}
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def _save_hash_registry(self) -> None:
        with open(self.cfg.content_hash_registry_path, "w", encoding="utf-8") as f:
            json.dump(self.seen_hashes, f, ensure_ascii=False, indent=2)

    @staticmethod
    def _load_lexicon(path: Path, key: str) -> dict[str, dict]:
        if not path.exists():
            log.warning("קובץ %s לא נמצא - ממשיכים עם לקסיקון ריק. הריצו setup.py.", path)
            return {}
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data.get(key, {})

    @staticmethod
    def _load_relationship_types(path: Path) -> tuple[list[str], list[tuple[str, str]]]:
        if not path.exists():
            log.warning("קובץ %s לא נמצא - אין קשרים תיאורטיים בריצה הזו.", path)
            return [], []
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        types = [t["name"] for t in data.get("relationship_types", [])]
        contradictions = [(c["a"], c["b"]) for c in data.get("contradictions", [])]
        return types, contradictions

    # ------------------------- עיבוד קובץ בודד --------------------------
    def process_file(self, path: Path) -> DocResult:
        doc_id = path.stem
        result = DocResult(doc_id=doc_id, path=str(path), status="ok")

        try:
            paragraphs = DocxReader.read(path)
        except Exception as exc:
            result.status, msg = "failed_read", str(exc)
            result.warnings.append(msg)
            log.error("כשל בקריאת %s: %s", path.name, exc)
            file_manager.move_to_error(path, self.cfg.error_dir, msg)
            return result

        h = DocxReader.content_hash(paragraphs)
        if h in self.seen_hashes:
            result.status = "duplicate"
            result.warnings.append(f"כפילות תוכן של {self.seen_hashes[h]}")
            log.warning("%s הוא כפילות של %s - מדלגים", doc_id, self.seen_hashes[h])
            file_manager.move_to_error(path, self.cfg.error_dir, "כפילות תוכן")
            return result
        self.seen_hashes[h] = doc_id

        try:
            paragraphs = [{**p, "text": self.deid.deidentify(p["text"])} for p in paragraphs]
        except DeIdentifier.DeIdError as exc:
            result.status = "failed_deid"
            result.warnings.append(str(exc))
            log.error("de-id נכשל עבור %s - הקובץ לא ימשיך בצינור", doc_id)
            file_manager.move_to_error(path, self.cfg.error_dir, "כשל de-id")
            return result

        chunks, anchors, warnings = self.chunker.chunk_document(doc_id, paragraphs)
        result.anchors, result.warnings = anchors, result.warnings + warnings

        for c in chunks:
            c.concept_candidates = self.concept_gen.candidates_for(c.text)
            c.exercise_candidates = self.exercise_gen.candidates_for(c.text)
            c.modality = self.llm.classify_modality(c.text)
            self.verifier.verify_chunk(c)
        result.chunks = chunks

        file_manager.move_to_archive(path, self.cfg.archive_dir)
        return result

    # ------------------------- ריצה מלאה --------------------------------
    def run(self) -> None:
        files = sorted(self.cfg.inbox_dir.glob("*.docx"))
        if self.cfg.limit:
            files = files[: self.cfg.limit]
        if not files:
            log.error("לא נמצאו קבצי docx ב-%s", self.cfg.inbox_dir)
            return

        results = [self.process_file(p) for p in files]
        self._save_hash_registry()
        ok = [r for r in results if r.status == "ok"]
        all_chunks = [c for r in ok for c in r.chunks]

        works_on_edges: list[dict] = []
        # קשרי Concept-Concept אוטומטיים חסומים עד לאישור אנושי מפורש.
        # קשרים כאלה עשויים להיות פרשנות של מודל, ולא עובדה תיאורטית מאושרת.
        rel_edges: list[dict] = []
        conflicts: list[dict] = []
        for c in all_chunks:
            works_on_edges.extend(self.rel_extractor.extract_works_on(c))

        self._write_reports(results, works_on_edges, rel_edges, conflicts)

        log.info("סיכום: %d קבצים, %d תקינים, %d chunks, %d קשרי WORKS_ON, "
                 "%d קשרי מושג-מושג, %d קונפליקטים לבדיקה אנושית",
                 len(results), len(ok), len(all_chunks),
                 len(works_on_edges), len(rel_edges), len(conflicts))

        if self.cfg.dry_run:
            log.info("dry-run: לא טוענים ל-Neo4j. בדקו את הדוחות ב-%s", self.cfg.output_dir)
            return

        loader = GraphLoader(self.cfg)
        try:
            loader.connect()
            loader.load_chunks(all_chunks)
            loader.load_linked(all_chunks)
            loader.load_works_on(works_on_edges)
            loader.load_concept_relationships(rel_edges)
        finally:
            loader.close()

    # ------------------------- דוחות לבדיקה אנושית -----------------------
    def _write_reports(self, results: list[DocResult], works_on: list[dict],
                        rel_edges: list[dict], conflicts: list[dict]) -> None:
        manifest = {
            "run_time": dt.datetime.now().isoformat(),
            "files": [{"doc_id": r.doc_id, "status": r.status, "n_chunks": len(r.chunks),
                       "n_anchors": len(r.anchors), "warnings": r.warnings} for r in results],
        }
        anchors_report = {
            r.doc_id: [{"line": a.source_line, "lesson": a.lesson_number,
                        "date": a.lesson_date.isoformat() if a.lesson_date else None,
                        "score": a.score, "paragraph": a.paragraph_index} for a in r.anchors]
            for r in results if r.status == "ok"
        }
        linking_stats = self._linking_stats(results)
        waiting_room = self._waiting_room(results)

        payloads = {
            "manifest.json": manifest,
            "anchors_report.json": anchors_report,
            "linking_stats.json": linking_stats,
            "waiting_room.json": waiting_room,
            "works_on_candidates.json": works_on,
            "concept_relationships.json": rel_edges,
            "conflicts_report.json": conflicts,
        }
        for name, payload in payloads.items():
            out = self.cfg.output_dir / name
            with open(out, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            log.info("נכתב דוח: %s", out)

    @staticmethod
    def _linking_stats(results: list[DocResult]) -> dict:
        chunks = [c for r in results if r.status == "ok" for c in r.chunks]
        if not chunks:
            return {}
        with_cand = [c for c in chunks if c.concept_candidates]
        with_verified = [c for c in chunks if c.verified_links]
        return {
            "total_chunks": len(chunks),
            "chunks_with_concept_candidates": len(with_cand),
            "candidate_coverage_pct": round(100 * len(with_cand) / len(chunks), 1),
            "chunks_with_verified_links": len(with_verified),
            "avg_candidates_per_chunk": round(
                sum(len(c.concept_candidates) for c in chunks) / len(chunks), 2),
            "timeless_chunks": sum(1 for c in chunks if c.temporal_status == TemporalStatus.TIMELESS),
            "low_confidence_chunks": sum(1 for c in chunks if c.temporal_status == TemporalStatus.LOW_CONFIDENCE),
            "modality_breakdown": {
                m: sum(1 for c in chunks if c.modality == m)
                for m in ("individual", "couples", "family", "general")
            },
        }

    @staticmethod
    def _waiting_room(results: list[DocResult]) -> dict:
        """מקובץ לפי שם קנוני - כל ה-unclear של אותו מושג ביחד, כמו שפייבל תיאר
        ('לא להציג 40 מופעים בנפרד, לקבץ ולהציג אשכול אחד')."""
        grouped: dict[str, list[dict]] = {}
        for r in results:
            if r.status != "ok":
                continue
            for c in r.chunks:
                for item in c.unclear_links:
                    grouped.setdefault(item["canonical"], []).append({
                        "doc_id": r.doc_id, "chunk_id": c.chunk_id,
                        "matched_form": item["matched_form"],
                        "excerpt": c.text[:200],
                    })
        return grouped


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description="Ingestion pipeline - המוח המערכתי")
    ap.add_argument("--base-dir", default=".", type=Path, help="תיקיית השורש של הפרויקט")
    ap.add_argument("--dry-run", action="store_true", help="לא טוענים ל-Neo4j, רק דוחות")
    ap.add_argument("--mock-llm", action="store_true",
                     help="⚠️ תשובות LLM מזויפות - אך ורק לבדיקות עם דאטה מזויפת, לעולם לא עם קבצים אמיתיים")
    ap.add_argument("--limit", type=int, default=None, help="לעבד רק N קבצים ראשונים (הרצת מדגם מבוקרת)")
    args = ap.parse_args()

    cfg = Config(base_dir=args.base_dir, dry_run=args.dry_run,
                 mock_llm=args.mock_llm, limit=args.limit)

    if args.mock_llm:
        log.warning("=" * 70)
        log.warning("מצב --mock-llm פעיל: כל תשובות ה-LLM מזויפות (כולל אנונימיזציה).")
        log.warning("להשתמש אך ורק עם קבצי בדיקה מזויפים, לעולם לא עם דאטה של מטופלים.")
        log.warning("=" * 70)

    Pipeline(cfg).run()


if __name__ == "__main__":
    main()
