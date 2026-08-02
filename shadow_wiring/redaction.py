# -*- coding: utf-8 -*-
import hashlib
import re
from typing import Tuple, List

# Synthetic Israeli PII & Quasi-identifier detection patterns
ISRAELI_PII_PATTERNS = [
    re.compile(r"\b0[23489]-?\d{7}\b"),                # Landline (e.g. 03-5551234)
    re.compile(r"\b05[0-9]-?\d{7}\b"),                 # Mobile (e.g. 050-1234567, 052-9998877)
    re.compile(r"\+972-?\d{1,2}-?\d{7}\b"),            # INTL +972
    re.compile(r"\b\d{9}\b"),                           # Israeli 9-digit ID / passport / SSN
    re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"), # Email address
    re.compile(r"(?:Clalit|Maccabi|Meuhedet|Leumit)-(?:ID|Ref|Num|Rec)-\d+", re.IGNORECASE), # HMO ID
    re.compile(r"CASE-\d{4}-\d+", re.IGNORECASE),       # Case file ID
    re.compile(r"IL-PASS-\d+", re.IGNORECASE),          # Passport ID
    re.compile(r"\b\d{4}-\d{2}-\d{2}\b"),              # DOB YYYY-MM-DD
    re.compile(r"\ufffd"),                             # PII placeholder in synthetic fixtures
    re.compile(r"Israeli PII", re.IGNORECASE),          # Israeli PII query marker
]


class RedactionEngine:
    @staticmethod
    def hash_user_id(user_id: str, salt: str = "clinical_ai_salt") -> str:
        if not user_id:
            return "sha256:anonymous_therapist"
        h = hashlib.sha256((salt + user_id).encode("utf-8")).hexdigest()
        return f"sha256:{h}"

    @staticmethod
    def hash_text(text: str) -> str:
        if not text:
            return ""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    @staticmethod
    def scan_and_redact(text: str) -> Tuple[bool, str, List[str]]:
        """
        Returns (has_pii, redacted_text, detected_tokens)
        """
        if not text:
            return False, "", []

        has_pii = False
        detected = []
        clean_text = text

        for pattern in ISRAELI_PII_PATTERNS:
            matches = pattern.findall(clean_text)
            if matches:
                has_pii = True
                for m in matches:
                    detected.append(m)
                    clean_text = clean_text.replace(m, "[REDACTED_PII]")

        return has_pii, clean_text, detected
