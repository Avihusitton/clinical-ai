# -*- coding: utf-8 -*-
"""Small local-only store for workspace patients, conversations, and messages."""

from __future__ import annotations

import json
import threading
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class ConversationNotFound(KeyError):
    pass


class PatientNotFound(KeyError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean_text(value: Any, *, max_length: int, field: str) -> str:
    text = " ".join(str(value or "").split())
    if not text:
        raise ValueError(f"{field} is required")
    if len(text) > max_length:
        raise ValueError(f"{field} is too long")
    return text


class LocalConversationStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self._lock = threading.RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write({"version": 1, "patients": [], "conversations": []})

    def _read(self) -> dict[str, Any]:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError("Local conversation workspace is unavailable") from exc
        if not isinstance(payload, dict):
            raise RuntimeError("Local conversation workspace is invalid")
            
        if "users" in payload:
            payload["therapists"] = payload.pop("users")
            
        payload.setdefault("therapists", [])
        payload.setdefault("patients", [])
        payload.setdefault("conversations", [])
        
        # Ensure all patients have a therapist_id
        if payload["patients"] and not any(p.get("therapist_id") for p in payload["patients"]):
            default_therapist_id = f"thr-{uuid.uuid4().hex}"
            payload["therapists"].append({
                "id": default_therapist_id,
                "name": "מטפל כללי",
                "created_at": _now()
            })
            for patient in payload["patients"]:
                patient["therapist_id"] = default_therapist_id

        return payload

    def _write(self, payload: dict[str, Any]) -> None:
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(self.path)

    @staticmethod
    def _find_therapist(payload: dict[str, Any], therapist_id: str) -> dict[str, Any]:
        for therapist in payload["therapists"]:
            if therapist.get("id") == therapist_id:
                return therapist
        raise KeyError(f"Therapist {therapist_id} not found")

    @staticmethod
    def _find_patient(payload: dict[str, Any], therapist_id: str, patient_id: str) -> dict[str, Any]:
        for patient in payload["patients"]:
            if patient.get("id") == patient_id and patient.get("therapist_id") == therapist_id:
                return patient
        raise PatientNotFound(patient_id)

    @staticmethod
    def _find_conversation(
        payload: dict[str, Any],
        therapist_id: str,
        patient_id: str,
        conversation_id: str,
    ) -> dict[str, Any]:
        # Validate patient exists under therapist
        LocalConversationStore._find_patient(payload, therapist_id, patient_id)
        for conversation in payload["conversations"]:
            if (
                conversation.get("id") == conversation_id
                and conversation.get("patient_id") == patient_id
            ):
                return conversation
        raise ConversationNotFound(conversation_id)

    def list_therapists(self) -> list[dict[str, Any]]:
        with self._lock:
            payload = self._read()
            return deepcopy(
                sorted(
                    payload["therapists"],
                    key=lambda item: (str(item.get("name") or "").casefold(), item["id"]),
                )
            )

    def create_therapist(self, name: str) -> dict[str, Any]:
        clean_name = _clean_text(name, max_length=60, field="name")
        with self._lock:
            payload = self._read()
            now = _now()
            therapist = {
                "id": f"thr-{uuid.uuid4().hex}",
                "name": clean_name,
                "created_at": now,
            }
            payload["therapists"].append(therapist)
            self._write(payload)
            return deepcopy(therapist)

    def rename_therapist(self, therapist_id: str, new_name: str) -> dict[str, Any]:
        clean_name = _clean_text(new_name, max_length=60, field="name")
        with self._lock:
            payload = self._read()
            therapist = self._find_therapist(payload, therapist_id)
            therapist["name"] = clean_name
            self._write(payload)
            return deepcopy(therapist)

    def list_patients(self, therapist_id: str) -> list[dict[str, Any]]:
        with self._lock:
            payload = self._read()
            self._find_therapist(payload, therapist_id)
            patients = [
                p for p in payload["patients"]
                if p.get("therapist_id") == therapist_id
            ]
            return deepcopy(
                sorted(
                    patients,
                    key=lambda item: (str(item.get("name") or "").casefold(), item["id"]),
                )
            )

    def create_patient(self, therapist_id: str, name: str) -> dict[str, Any]:
        clean_name = _clean_text(name, max_length=60, field="name")
        with self._lock:
            payload = self._read()
            self._find_therapist(payload, therapist_id)
            now = _now()
            patient = {
                "id": f"pat-{uuid.uuid4().hex}",
                "therapist_id": therapist_id,
                "name": clean_name,
                "created_at": now,
            }
            payload["patients"].append(patient)
            self._write(payload)
            return deepcopy(patient)

    def rename_patient(self, therapist_id: str, patient_id: str, new_name: str) -> dict[str, Any]:
        clean_name = _clean_text(new_name, max_length=60, field="name")
        with self._lock:
            payload = self._read()
            patient = self._find_patient(payload, therapist_id, patient_id)
            patient["name"] = clean_name
            self._write(payload)
            return deepcopy(patient)

    def create_conversation(
        self,
        *,
        therapist_id: str,
        patient_id: str,
        title: str = "שיחה חדשה",
    ) -> dict[str, Any]:
        with self._lock:
            payload = self._read()
            self._find_patient(payload, therapist_id, patient_id)
            conversation_id = f"cnv-{uuid.uuid4().hex}"
            now = _now()
            conversation = {
                "id": conversation_id,
                "patient_id": patient_id,
                "title": str(title or "שיחה חדשה")[:200],
                "summary": "",
                "messages": [],
                "created_at": now,
                "updated_at": now,
            }
            payload["conversations"].append(conversation)
            self._write(payload)
            return deepcopy(conversation)

    def delete_therapist(self, therapist_id: str) -> None:
        with self._lock:
            payload = self._read()
            self._find_therapist(payload, therapist_id)
            payload["therapists"] = [t for t in payload["therapists"] if t.get("id") != therapist_id]
            # Delete associated patients
            patients_to_delete = {p.get("id") for p in payload["patients"] if p.get("therapist_id") == therapist_id}
            payload["patients"] = [p for p in payload["patients"] if p.get("therapist_id") != therapist_id]
            # Delete associated conversations
            payload["conversations"] = [c for c in payload["conversations"] if c.get("patient_id") not in patients_to_delete]
            self._write(payload)

    def delete_conversation(self, therapist_id: str, patient_id: str, conversation_id: str) -> None:
        with self._lock:
            payload = self._read()
            self._find_conversation(payload, therapist_id, patient_id, conversation_id)
            payload["conversations"] = [c for c in payload["conversations"] if c.get("id") != conversation_id]
            self._write(payload)

    def update_title(
        self,
        *,
        therapist_id: str,
        patient_id: str,
        conversation_id: str,
        title: str,
    ) -> dict[str, Any]:
        clean_title = " ".join(str(title or "").split())[:200]
        if not clean_title:
            raise ValueError("title cannot be empty")
        with self._lock:
            payload = self._read()
            conversation = self._find_conversation(
                payload,
                therapist_id,
                patient_id,
                conversation_id,
            )
            conversation["title"] = clean_title
            conversation["updated_at"] = _now()
            self._write(payload)
            return deepcopy(conversation)

    def list_conversations(self, therapist_id: str, patient_id: str) -> list[dict[str, Any]]:
        with self._lock:
            payload = self._read()
            self._find_patient(payload, therapist_id, patient_id)
            conversations = [
                conversation
                for conversation in payload["conversations"]
                if conversation.get("patient_id") == patient_id
            ]
            conversations.sort(
                key=lambda item: str(item.get("updated_at") or ""),
                reverse=True,
            )
            return [
                {
                    key: deepcopy(value)
                    for key, value in conversation.items()
                    if key != "messages"
                }
                | {"message_count": len(conversation.get("messages") or [])}
                for conversation in conversations
            ]

    def get_conversation(
        self,
        therapist_id: str,
        patient_id: str,
        conversation_id: str,
    ) -> dict[str, Any]:
        with self._lock:
            payload = self._read()
            self._find_patient(payload, therapist_id, patient_id)
            return deepcopy(
                self._find_conversation(payload, therapist_id, patient_id, conversation_id)
            )

    def append_message(
        self,
        *,
        therapist_id: str,
        patient_id: str,
        conversation_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if role not in {"user", "assistant"}:
            raise ValueError("role must be user or assistant")
        clean_content = str(content or "").strip()
        if not clean_content:
            raise ValueError("content is required")
        if len(clean_content) > 12000:
            raise ValueError("content is too long")
        with self._lock:
            payload = self._read()
            conversation = self._find_conversation(
                payload,
                therapist_id,
                patient_id,
                conversation_id,
            )
            now = _now()
            message = {
                "id": f"msg-{uuid.uuid4().hex}",
                "role": role,
                "content": clean_content,
                "metadata": deepcopy(metadata or {}),
                "created_at": now,
            }
            conversation["messages"].append(message)
            conversation["updated_at"] = now
            self._write(payload)
            return deepcopy(message)

    def update_summary(
        self,
        *,
        therapist_id: str,
        patient_id: str,
        conversation_id: str,
        summary: str,
    ) -> dict[str, Any]:
        clean_summary = " ".join(str(summary or "").split())[:4000]
        with self._lock:
            payload = self._read()
            conversation = self._find_conversation(
                payload,
                therapist_id,
                patient_id,
                conversation_id,
            )
            conversation["summary"] = clean_summary
            conversation["updated_at"] = _now()
            self._write(payload)
            return deepcopy(conversation)

    def set_title_from_first_question(
        self,
        *,
        therapist_id: str,
        patient_id: str,
        conversation_id: str,
        question: str,
    ) -> dict[str, Any]:
        with self._lock:
            payload = self._read()
            conversation = self._find_conversation(
                payload,
                therapist_id,
                patient_id,
                conversation_id,
            )
            if conversation.get("title") == "שיחה חדשה":
                clean = " ".join(str(question or "").split())
                conversation["title"] = clean[:57] + ("…" if len(clean) > 57 else "")
                conversation["updated_at"] = _now()
                self._write(payload)
            return deepcopy(conversation)


from neo4j import GraphDatabase
import threading
import json
import uuid

class Neo4jConversationStore(LocalConversationStore):
    def __init__(self, uri: str, username: str, password: str, database: str | None = None):
        self._driver = GraphDatabase.driver(uri, auth=(username, password))
        self._database = database
        self._lock = threading.RLock()
        
        # Verify connection and initialize if needed
        try:
            self._driver.verify_connectivity()
            # If the node doesn't exist, _read() handles defaults, but we need to _write them
            payload = self._read()
            if not payload.get("version"):
                payload["version"] = 1
                self._write(payload)
        except Exception as exc:
            raise RuntimeError("Failed to connect to Neo4j") from exc

    def _read(self) -> dict:
        query = """
        MATCH (state:AppState {id: "clinical_ai_conversations"})
        RETURN state.payload AS payload
        """
        try:
            with self._driver.session(database=self._database) as session:
                record = session.run(query).single()
                if record and record["payload"]:
                    payload = json.loads(record["payload"])
                else:
                    payload = {}
        except Exception as exc:
            raise RuntimeError("Neo4j workspace is unavailable") from exc
            
        if not isinstance(payload, dict):
            payload = {}
            
        if "users" in payload:
            payload["therapists"] = payload.pop("users")
            
        payload.setdefault("therapists", [])
        payload.setdefault("patients", [])
        payload.setdefault("conversations", [])
        
        # Ensure all patients have a therapist_id
        if payload["patients"] and not any(p.get("therapist_id") for p in payload["patients"]):
            default_therapist_id = f"thr-{uuid.uuid4().hex}"
            payload["therapists"].append({
                "id": default_therapist_id,
                "name": "מטפל כללי",
                "created_at": _now()
            })
            for patient in payload["patients"]:
                patient["therapist_id"] = default_therapist_id

        return payload

    def _write(self, payload: dict) -> None:
        payload_str = json.dumps(payload, ensure_ascii=False)
        query = """
        MERGE (state:AppState {id: "clinical_ai_conversations"})
        SET state.payload = $payload
        """
        with self._driver.session(database=self._database) as session:
            session.run(query, payload=payload_str)

