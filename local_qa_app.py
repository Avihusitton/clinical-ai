# -*- coding: utf-8 -*-
"""Local, dependency-free web UI for read-only D4 dictionary questions."""

from __future__ import annotations

import json
import os
import re
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from ai_assisted_answer import (
    AiAssistedAnswerService,
    build_ai_service_from_environment,
)
from canonical_local_retrieval import (
    CanonicalLocalRetriever,
    ReadOnlyNeo4jHttpClient,
    BoltQueryExecutor,
)
from clinical_workspace_ui import render_workspace_html
from conversation_store import (
    ConversationNotFound,
    LocalConversationStore,
    PatientNotFound,
)


_EMAIL_PATTERN = re.compile(r"\b[^@\s]+@[^@\s]+\.[^@\s]+\b")
_PHONE_PATTERN = re.compile(r"(?<!\d)(?:\+?972[-\s]?|0)5\d[-\s]?\d{3}[-\s]?\d{4}(?!\d)")
_NINE_DIGIT_PATTERN = re.compile(r"(?<!\d)\d{9}(?!\d)")
_VISIBLE_CARD_ID_PATTERN = re.compile(
    r"(?<![\w-])(?:\(\s*)?(?:[A-Z]\d{3}|D4-[A-Z0-9-]+)(?:\s*\))?",
    flags=re.IGNORECASE,
)
_ALLOWED_NEO4J_SETTINGS = {
    "NEO4J_USER",
    "NEO4J_PASSWORD",
    "NEO4J_HTTP_URI",
    "NEO4J_URI",
    "NEO4J_DATABASE",
}
DEFAULT_WORKSPACE_PATH = (
    Path(__file__).with_name("out") / "local_runtime" / "conversation_workspace.json"
)


def _contains_direct_identifier(text: str) -> bool:
    return any(
        pattern.search(text or "")
        for pattern in (_EMAIL_PATTERN, _PHONE_PATTERN, _NINE_DIGIT_PATTERN)
    )


def _without_visible_card_ids(text: str) -> str:
    clean = _VISIBLE_CARD_ID_PATTERN.sub("", str(text or ""))
    clean = re.sub(r"[ \t]+([,.;:!?])", r"\1", clean)
    clean = re.sub(r"\(\s*\)", "", clean)
    clean = re.sub(r"[ \t]{2,}", " ", clean)
    return clean.strip()


def _parse_neo4j_env_lines(lines: list[str]) -> dict[str, str]:
    settings: dict[str, str] = {}
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key not in _ALLOWED_NEO4J_SETTINGS:
            continue
        settings[key] = value.strip().strip('"').strip("'")
    return settings


def _build_retrieval_question(
    question: str,
    conversation_history: list[dict[str, Any]] | None,
) -> str:
    """Ground follow-ups in recent user-provided facts, not only the last turn."""
    recent_user_updates = [
        str(message.get("content") or "").strip()
        for message in list(conversation_history or [])[-8:]
        if message.get("role") == "user"
        and str(message.get("content") or "").strip()
    ][-3:]
    parts = [*recent_user_updates, question]
    return "\n".join(parts)[-5000:]


def handle_ask(
    retriever: CanonicalLocalRetriever,
    payload: dict[str, Any],
    *,
    ai_service: AiAssistedAnswerService | None = None,
    conversation_history: list[dict[str, Any]] | None = None,
    conversation_summary: str = "",
) -> tuple[int, dict[str, Any]]:
    started_at = time.perf_counter()
    if payload.get("confirmed_no_patient_data") is not True:
        return HTTPStatus.BAD_REQUEST, {
            "status": "privacy_confirmation_required",
            "answer_text": (
                "יש לאשר שהשאלה עוסקת בשיטה בלבד ואינה כוללת מידע על מטופל "
                "או אדם מזוהה."
            ),
        }
    question = str(payload.get("question") or "").strip()
    if _contains_direct_identifier(question):
        return HTTPStatus.BAD_REQUEST, {
            "status": "identifier_detected",
            "answer_text": (
                "השאלה נחסמה משום שנמצא בה פרט מזהה אפשרי. "
                "יש להסיר פרטים על אנשים ולשאול רק על מושגי השיטה."
            ),
        }
    if len(question) > 1500:
        return HTTPStatus.BAD_REQUEST, {
            "status": "question_too_long",
            "answer_text": "השאלה ארוכה מדי. יש לנסח שאלת ידע קצרה על השיטה.",
        }
    retrieval_question = (
        _build_retrieval_question(question, conversation_history)
        if payload.get("use_ai") is True
        else question
    )
    result = retriever.answer(retrieval_question)
    if payload.get("use_ai") is True:
        service = ai_service or AiAssistedAnswerService()
        result = service.enhance(
            question,
            result,
            requested_model=str(payload.get("ai_model") or ""),
            conversation_history=conversation_history,
            conversation_summary=conversation_summary,
        )
    result["answer_text"] = _without_visible_card_ids(
        str(result.get("answer_text") or "")
    )
    result.setdefault("response_type", "answer")
    result.setdefault(
        "generation",
        {
            "elapsed_ms": round((time.perf_counter() - started_at) * 1000),
            "cost_usd": 0.0,
            "cost_ils": 0.0,
            "usd_to_ils_rate": 3.058,
            "usd_to_ils_rate_date": "2026-07-28",
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "model": "מענה מקומי",
        },
    )
    return HTTPStatus.OK, result


def render_app_html() -> str:
    return render_workspace_html()

def build_retriever_from_environment() -> CanonicalLocalRetriever:
    file_settings: dict[str, str] = {}
    env_path = Path(__file__).with_name(".env")
    if env_path.exists():
        file_settings = _parse_neo4j_env_lines(
            env_path.read_text(encoding="utf-8").splitlines()
        )
    username = (
        os.getenv("NEO4J_USER")
        or os.getenv("NEO4J_USERNAME")
        or file_settings.get("NEO4J_USER")
        or "neo4j"
    )
    password = (os.getenv("NEO4J_PASSWORD") or file_settings.get("NEO4J_PASSWORD", "")).strip()
    
    # If a Bolt/neo4j+s URI is provided, use the BoltQueryExecutor (required for Aura)
    bolt_uri = (
        os.getenv("NEO4J_URI") 
        or file_settings.get("NEO4J_URI")
    )
    
    database = (
        os.getenv("NEO4J_DATABASE")
        or file_settings.get("NEO4J_DATABASE")
        or None
    )
    
    if bolt_uri and (
        bolt_uri.startswith("bolt://") 
        or bolt_uri.startswith("neo4j://") 
        or bolt_uri.startswith("neo4j+s://")
        or bolt_uri.startswith("neo4j+ssc://")
        or bolt_uri.startswith("bolt+ssc://")
    ):
        executor = BoltQueryExecutor(
            uri=bolt_uri,
            username=username,
            password=password,
            database=database,
        )
    else:
        http_uri = (
            os.getenv("NEO4J_HTTP_URI")
            or file_settings.get("NEO4J_HTTP_URI")
            or "http://127.0.0.1:7474"
        )
        executor = ReadOnlyNeo4jHttpClient(
            username=username,
            password=password,
            http_uri=http_uri,
            database=database,
        )
        
    return CanonicalLocalRetriever(executor)


def build_workspace_store() -> LocalConversationStore:
    configured_path = os.getenv("CLINICAL_AI_WORKSPACE_PATH", "").strip()
    return LocalConversationStore(
        Path(configured_path) if configured_path else DEFAULT_WORKSPACE_PATH
    )


class LocalQaRequestHandler(BaseHTTPRequestHandler):
    retriever: CanonicalLocalRetriever
    ai_service: AiAssistedAnswerService
    workspace_store: LocalConversationStore
    server_version = "ClinicalAiLocalQa/1.0"

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _parse_multipart(self) -> tuple[list[dict[str, Any]], int]:
        import re as _re
        content_type = self.headers.get('Content-Type', '')
        boundary_match = _re.search(r'boundary=([^\s;]+)', content_type)
        if not boundary_match:
            raise ValueError('No boundary')
        boundary = boundary_match.group(1).encode()
        length = int(self.headers.get('Content-Length', '0'))
        if length <= 0 or length > 500 * 1024 * 1024:  # 500MB limit
            raise ValueError('Invalid content length for upload')
        body = self.rfile.read(length)
        
        parts = body.split(b'--' + boundary)
        files = []
        order = 1
        for part in parts:
            if b'Content-Disposition' not in part:
                continue
            headers_end = part.find(b'\r\n\r\n')
            if headers_end < 0:
                continue
            header_section = part[:headers_end].decode('utf-8', errors='replace')
            file_data = part[headers_end + 4:]
            if file_data.endswith(b'\r\n'):
                file_data = file_data[:-2]
            
            name_match = _re.search(r'name="([^"]+)"', header_section)
            filename_match = _re.search(r'filename="([^"]+)"', header_section)
            
            if not name_match:
                continue
            field_name = name_match.group(1)
            
            if field_name == 'order':
                order = int(file_data.decode().strip())
            elif filename_match:
                files.append({
                    'filename': filename_match.group(1),
                    'data': file_data
                })
        return files, order

    def _read_json_payload(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > 5 * 1024 * 1024:  # 5MB limit
            raise ValueError("invalid content length")
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("payload must be an object")
        return payload

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        if parsed.path == "/":
            body = render_app_html().encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'self';")
            self.send_header("Referrer-Policy", "no-referrer")
            self.end_headers()
            self.wfile.write(body)
            return
        if parsed.path == "/api/health":
            type(self).ai_service = build_ai_service_from_environment()
            self._send_json(
                HTTPStatus.OK,
                {
                    "status": "ok",
                    "neo4j_running": self.retriever.health(),
                    "mode": "D4_CANONICAL_LOCAL_READ_ONLY",
                    "ai_available": self.ai_service.available,
                    "ai_model": self.ai_service.model,
                },
            )
            return
        if parsed.path == "/api/therapists":
            self._send_json(
                HTTPStatus.OK,
                {
                    "status": "ok",
                    "therapists": self.workspace_store.list_therapists(),
                },
            )
            return
        
        if parsed.path == "/api/inbox/files":
            import datetime
            inbox_dir = Path("docs_inbox")
            files_list = []
            if inbox_dir.exists() and inbox_dir.is_dir():
                for filename in os.listdir(inbox_dir):
                    if filename.endswith(".meta.json") or filename == ".gitkeep":
                        continue
                    file_path = inbox_dir / filename
                    if not file_path.is_file():
                        continue
                    size_kb = os.path.getsize(file_path) / 1024
                    meta_path = inbox_dir / (filename.rsplit('.', 1)[0] + ".meta.json")
                    has_meta = meta_path.exists()
                    meta_status = "unknown"
                    if has_meta:
                        try:
                            with open(meta_path, "r", encoding="utf-8") as f:
                                meta_status = json.load(f).get("status", "unknown")
                        except Exception:
                            pass
                    
                    created_at = datetime.datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
                    files_list.append({
                        "filename": filename,
                        "size_kb": round(size_kb, 2),
                        "has_meta": has_meta,
                        "meta_status": meta_status,
                        "created_at": created_at
                    })
            self._send_json(HTTPStatus.OK, {"status": "ok", "files": files_list})
            return
        
        patients_match = re.match(r"^/api/therapists/([^/]+)/patients$", parsed.path)
        if patients_match:
            therapist_id = patients_match.group(1)
            try:
                patients = self.workspace_store.list_patients(therapist_id)
            except KeyError:
                self._send_json(HTTPStatus.NOT_FOUND, {"status": "therapist_not_found"})
                return
            self._send_json(
                HTTPStatus.OK,
                {"status": "ok", "patients": patients},
            )
            return

        conversations_match = re.match(r"^/api/therapists/([^/]+)/patients/([^/]+)/conversations$", parsed.path)
        if conversations_match:
            therapist_id = conversations_match.group(1)
            patient_id = conversations_match.group(2)
            try:
                conversations = self.workspace_store.list_conversations(therapist_id, patient_id)
            except (KeyError, PatientNotFound):
                self._send_json(
                    HTTPStatus.NOT_FOUND,
                    {"status": "patient_not_found"},
                )
                return
            self._send_json(
                HTTPStatus.OK,
                {"status": "ok", "conversations": conversations},
            )
            return
        if parsed.path == "/api/conversation":
            therapist_id = str((query.get("therapist_id") or [""])[0])
            patient_id = str((query.get("patient_id") or [""])[0])
            conversation_id = str(
                (query.get("conversation_id") or [""])[0]
            )
            try:
                conversation = self.workspace_store.get_conversation(
                    therapist_id,
                    patient_id,
                    conversation_id,
                )
            except (KeyError, PatientNotFound, ConversationNotFound):
                self._send_json(
                    HTTPStatus.NOT_FOUND,
                    {"status": "conversation_not_found"},
                )
                return
            self._send_json(
                HTTPStatus.OK,
                {"status": "ok", "conversation": conversation},
            )
            return
            
        if parsed.path == "/api/inbox/progress":
            base_dir = Path(__file__).parent
            progress_path = base_dir / "out" / "local_runtime" / "progress.json"
            if not progress_path.exists():
                self._send_json(HTTPStatus.OK, {"status": "idle"})
                return
            try:
                with open(progress_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._send_json(HTTPStatus.OK, data)
            except Exception:
                self._send_json(HTTPStatus.OK, {"status": "idle"})
            return

        self._send_json(HTTPStatus.NOT_FOUND, {"status": "not_found"})

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        post_patients_match = re.match(r"^/api/therapists/([^/]+)/patients$", parsed.path)
        post_conversations_match = re.match(r"^/api/therapists/([^/]+)/patients/([^/]+)/conversations$", parsed.path)
        
        if parsed.path not in {
            "/api/therapists",
            "/api/ask",
            "/api/intake",
            "/api/intake/upload",
            "/api/inbox/process",
        } and not post_conversations_match and not post_patients_match:
            self._send_json(HTTPStatus.NOT_FOUND, {"status": "not_found"})
            return
            
        if parsed.path == "/api/intake/upload":
            try:
                files, order = self._parse_multipart()
            except ValueError as e:
                self._send_json(HTTPStatus.BAD_REQUEST, {"status": "invalid_request", "answer_text": str(e)})
                return
            
            import uuid
            inbox_dir = Path("docs_inbox")
            os.makedirs(inbox_dir, exist_ok=True)
            
            authority = "UNKNOWN"
            if order == 1:
                authority = "METHOD_PRIMARY"
            elif order == 2:
                authority = "SECONDARY_INTERPRETIVE"
            elif order == 3:
                authority = "UNVERIFIED"

            ids = []
            count = 0
            for file_info in files:
                orig_name = file_info['filename']
                ext = ""
                if '.' in orig_name:
                    ext = "." + orig_name.rsplit('.', 1)[-1].lower()
                
                if ext not in {'.pdf', '.docx', '.doc', '.txt'}:
                    continue
                
                material_id = str(uuid.uuid4())
                file_name = f"material_{material_id}{ext}"
                file_path = inbox_dir / file_name
                meta_path = inbox_dir / f"material_{material_id}.meta.json"
                
                with open(file_path, "wb") as f:
                    f.write(file_info['data'])
                
                with open(meta_path, "w", encoding="utf-8") as f:
                    json.dump({
                        "id": material_id,
                        "order": order,
                        "authority": authority,
                        "status": "pending",
                        "original_filename": orig_name
                    }, f, ensure_ascii=False, indent=2)
                
                ids.append(material_id)
                count += 1
            
            self._send_json(HTTPStatus.CREATED, {"status": "created", "count": count, "ids": ids})
            return

        try:
            payload = self._read_json_payload()
        except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
            self._send_json(
                HTTPStatus.BAD_REQUEST,
                {"status": "invalid_request", "answer_text": "בקשה לא תקינה."},
            )
            return
        if parsed.path == "/api/therapists":
            try:
                therapist = self.workspace_store.create_therapist(
                    str(payload.get("name") or "")
                )
            except ValueError:
                self._send_json(
                    HTTPStatus.BAD_REQUEST,
                    {"status": "invalid_therapist_name"},
                )
                return
            self._send_json(
                HTTPStatus.CREATED,
                {"status": "created", "therapist": therapist},
            )
            return

        if post_patients_match:
            therapist_id = post_patients_match.group(1)
            try:
                patient = self.workspace_store.create_patient(
                    therapist_id,
                    str(payload.get("name") or "")
                )
            except KeyError:
                self._send_json(
                    HTTPStatus.NOT_FOUND,
                    {"status": "therapist_not_found"},
                )
                return
            except ValueError:
                self._send_json(
                    HTTPStatus.BAD_REQUEST,
                    {"status": "invalid_patient_name"},
                )
                return
            self._send_json(
                HTTPStatus.CREATED,
                {"status": "created", "patient": patient},
            )
            return
        if post_conversations_match:
            therapist_id = post_conversations_match.group(1)
            patient_id = post_conversations_match.group(2)
            try:
                conversation = self.workspace_store.create_conversation(
                    therapist_id,
                    patient_id,
                    str(payload.get("title") or "שיחה חדשה"),
                )
            except (KeyError, PatientNotFound):
                self._send_json(
                    HTTPStatus.NOT_FOUND,
                    {"status": "patient_not_found"},
                )
                return
            except ValueError:
                self._send_json(
                    HTTPStatus.BAD_REQUEST,
                    {"status": "invalid_conversation"},
                )
                return
            self._send_json(
                HTTPStatus.CREATED,
                {"status": "created", "conversation": conversation},
            )
            return

        if parsed.path == "/api/intake":
            content_text = payload.get("content")
            order = payload.get("order", 1)
            if not content_text:
                self._send_json(HTTPStatus.BAD_REQUEST, {"status": "missing_content"})
                return
            
            import uuid
            material_id = str(uuid.uuid4())
            
            authority = "UNKNOWN"
            if order == 1:
                authority = "METHOD_PRIMARY"
            elif order == 2:
                authority = "SECONDARY_INTERPRETIVE"
            elif order == 3:
                authority = "UNVERIFIED"
            
            inbox_dir = Path("docs_inbox")
            os.makedirs(inbox_dir, exist_ok=True)
            
            file_path = os.path.join(inbox_dir, f"material_{material_id}.txt")
            meta_path = os.path.join(inbox_dir, f"material_{material_id}.meta.json")
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content_text)
                
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump({
                    "id": material_id,
                    "order": order,
                    "authority": authority,
                    "status": "pending"
                }, f, ensure_ascii=False, indent=2)
                
            # Trigger background processing for text paste
            pipeline_trigger.set()
                
            self._send_json(HTTPStatus.CREATED, {"status": "created", "id": material_id})
            return

        if parsed.path == "/api/inbox/process":
            files = payload.get("files", [])
            inbox_dir = Path("docs_inbox")
            processed = 0
            for item in files:
                filename = item.get("filename")
                order = item.get("order", 1)
                if not filename:
                    continue
                file_path = inbox_dir / filename
                if not file_path.exists():
                    continue
                
                meta_name = filename.rsplit('.', 1)[0] + ".meta.json"
                meta_path = inbox_dir / meta_name
                
                authority = "UNKNOWN"
                if order == 1:
                    authority = "METHOD_PRIMARY"
                elif order == 2:
                    authority = "SECONDARY_INTERPRETIVE"
                elif order == 3:
                    authority = "UNVERIFIED"
                
                meta_data = {}
                if meta_path.exists():
                    try:
                        with open(meta_path, "r", encoding="utf-8") as f:
                            meta_data = json.load(f)
                    except Exception:
                        pass
                
                meta_data["order"] = order
                meta_data["authority"] = authority
                if "status" not in meta_data:
                    meta_data["status"] = "pending"
                if "id" not in meta_data:
                    meta_data["id"] = filename.split('_')[1].split('.')[0] if '_' in filename else "unknown"
                
                with open(meta_path, "w", encoding="utf-8") as f:
                    json.dump(meta_data, f, ensure_ascii=False, indent=2)
                processed += 1
            
            # Trigger background processing for the selected files
            if processed > 0:
                pipeline_trigger.set()
            
            self._send_json(HTTPStatus.OK, {"status": "ok", "processed": processed})
            return

        therapist_id = str(payload.get("therapist_id") or "")
        patient_id = str(payload.get("patient_id") or "")
        conversation_id = str(payload.get("conversation_id") or "")
        conversation: dict[str, Any] | None = None
        if therapist_id and patient_id and conversation_id:
            try:
                conversation = self.workspace_store.get_conversation(
                    therapist_id,
                    patient_id,
                    conversation_id,
                )
            except (KeyError, PatientNotFound, ConversationNotFound):
                self._send_json(
                    HTTPStatus.NOT_FOUND,
                    {
                        "status": "conversation_or_patient_not_found",
                        "message": "השיחה או המטופל לא נמצאו (ייתכן שהשרת הופעל מחדש). רענן את העמוד כדי להתחיל מחדש."
                    },
                )
                return
        if payload.get("use_ai") is True:
            type(self).ai_service = build_ai_service_from_environment()
        status, response = handle_ask(
            self.retriever,
            payload,
            ai_service=self.ai_service,
            conversation_history=(
                list(conversation.get("messages") or [])
                if conversation is not None
                else None
            ),
            conversation_summary=(
                str(conversation.get("summary") or "")
                if conversation is not None
                else ""
            ),
        )
        if status == HTTPStatus.OK and conversation is not None:
            question = str(payload.get("question") or "").strip()
            self.workspace_store.append_message(
                therapist_id=therapist_id,
                patient_id=patient_id,
                conversation_id=conversation_id,
                role="user",
                content=question,
            )
            assistant_metadata = {
                "generation": response.get("generation") or {},
                "response_type": response.get("response_type") or "answer",
                "ai_model": response.get("ai_model"),
                "mode": response.get("mode"),
                "release_id": response.get("release_id"),
                "quality_reviewed": bool(
                    response.get("quality_reviewed")
                ),
                "retrieval_stats": response.get("ai_context") or {},
                "evidence": {
                    "matches": list(response.get("matches") or [])[:12],
                    "canonical_relations": list(
                        response.get("canonical_relations") or []
                    )[:24],
                    "approved_source_evidence": list(
                        response.get("approved_source_evidence") or []
                    )[:24],
                },
            }
            self.workspace_store.append_message(
                therapist_id=therapist_id,
                patient_id=patient_id,
                conversation_id=conversation_id,
                role="assistant",
                content=str(response.get("answer_text") or ""),
                metadata=assistant_metadata,
            )
            if response.get("conversation_summary") is not None:
                self.workspace_store.update_summary(
                    therapist_id=therapist_id,
                    patient_id=patient_id,
                    conversation_id=conversation_id,
                    summary=str(response.get("conversation_summary") or ""),
                )
            if conversation.get("title") == "שיחה חדשה":
                if self.ai_service and self.ai_service.available:
                    new_title = self.ai_service.generate_title(question, requested_model=payload.get("ai_model"))
                    if new_title and new_title != "שיחה חדשה":
                        self.workspace_store.update_title(
                            therapist_id=therapist_id,
                            patient_id=patient_id,
                            conversation_id=conversation_id,
                            title=new_title
                        )
                else:
                    self.workspace_store.set_title_from_first_question(
                        therapist_id=therapist_id,
                        patient_id=patient_id,
                        conversation_id=conversation_id,
                        question=question,
                    )
            response["conversation_id"] = conversation_id
        self._send_json(status, response)

    def do_DELETE(self) -> None:
        parsed = urlparse(self.path)
        delete_therapist_match = re.match(r"^/api/therapists/([^/]+)$", parsed.path)
        
        if delete_therapist_match:
            therapist_id = delete_therapist_match.group(1)
            try:
                self.workspace_store.delete_therapist(therapist_id)
                self._send_json(HTTPStatus.OK, {"status": "ok"})
            except KeyError:
                self._send_json(HTTPStatus.NOT_FOUND, {"status": "not_found"})
            return

        if parsed.path == "/api/conversation":
            query = parse_qs(parsed.query)
            therapist_id = query.get("therapist_id", [""])[0]
            patient_id = query.get("patient_id", [""])[0]
            conversation_id = query.get("conversation_id", [""])[0]
            if not therapist_id or not patient_id or not conversation_id:
                self._send_json(HTTPStatus.BAD_REQUEST, {"status": "missing_parameters"})
                return
            try:
                self.workspace_store.delete_conversation(therapist_id, patient_id, conversation_id)
                self._send_json(HTTPStatus.OK, {"status": "ok"})
            except KeyError:
                self._send_json(HTTPStatus.NOT_FOUND, {"status": "not_found"})
            return

        self._send_json(HTTPStatus.NOT_FOUND, {"status": "not_found"})

    def do_PUT(self) -> None:
        parsed = urlparse(self.path)
        put_therapist_match = re.match(r"^/api/therapists/([^/]+)$", parsed.path)
        put_patient_match = re.match(r"^/api/therapists/([^/]+)/patients/([^/]+)$", parsed.path)
        
        if not put_therapist_match and not put_patient_match:
            self._send_json(HTTPStatus.NOT_FOUND, {"status": "not_found"})
            return
            
        try:
            payload = self._read_json_payload()
        except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
            self._send_json(
                HTTPStatus.BAD_REQUEST,
                {"status": "invalid_request", "answer_text": "שגיאה בפורמט הבקשה."},
            )
            return

        if put_therapist_match:
            therapist_id = put_therapist_match.group(1)
            try:
                therapist = self.workspace_store.rename_therapist(
                    therapist_id,
                    str(payload.get("name") or "")
                )
            except KeyError:
                self._send_json(HTTPStatus.NOT_FOUND, {"status": "therapist_not_found"})
                return
            except ValueError:
                self._send_json(HTTPStatus.BAD_REQUEST, {"status": "invalid_therapist_name"})
                return
            self._send_json(HTTPStatus.OK, {"status": "ok", "therapist": therapist})
            return

        if put_patient_match:
            therapist_id = put_patient_match.group(1)
            patient_id = put_patient_match.group(2)
            try:
                patient = self.workspace_store.rename_patient(
                    therapist_id,
                    patient_id,
                    str(payload.get("name") or "")
                )
            except (KeyError, PatientNotFound):
                self._send_json(HTTPStatus.NOT_FOUND, {"status": "patient_or_therapist_not_found"})
                return
            except ValueError:
                self._send_json(HTTPStatus.BAD_REQUEST, {"status": "invalid_patient_name"})
                return
            self._send_json(HTTPStatus.OK, {"status": "ok", "patient": patient})
            return

    def log_message(self, _format: str, *args: Any) -> None:
        return


def main() -> None:
    # Support standard PaaS environments (like Render) which inject PORT
    host = os.getenv("LOCAL_QA_HOST", "0.0.0.0" if os.getenv("PORT") else "127.0.0.1")
    port = int(os.getenv("LOCAL_QA_PORT", os.getenv("PORT", "8765")))
    LocalQaRequestHandler.retriever = build_retriever_from_environment()
    LocalQaRequestHandler.ai_service = build_ai_service_from_environment()
    LocalQaRequestHandler.workspace_store = build_workspace_store()
    server = ThreadingHTTPServer((host, port), LocalQaRequestHandler)
    print(f"🚀 שרת Clinical AI הופעל בהצלחה!")
    print(f"👉 היכנס לדפדפן בכתובת: http://{host if host != '0.0.0.0' else 'localhost'}:{port}/")
    print(f"לחץ על Ctrl+C כדי לכבות את השרת.")
    server.serve_forever()


if __name__ == "__main__":
    main()
