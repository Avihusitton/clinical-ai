"""
controlled_integration/security/security_policy.py
---------------------------------------------------
Security policy engine enforcing PII detection/rejection, least-privilege RBAC,
and zero raw clinical narrative storage.
"""

import re
from typing import Dict, Any, List, Optional, Set
from ..exceptions import IntegrationException
from ..models import IntegrationContext

class PIIRejectedError(IntegrationException):
    """Raised when PII (email, phone, SSN, national ID) is detected in request input."""
    def __init__(self, message: str = "PII detected in request. Patient data must be fully anonymized.", details: dict = None):
        super().__init__(message, code="ERR_SEC_PII", details=details)

class AccessDeniedError(IntegrationException):
    """Raised when user role lacks required scope/permission for requested resource."""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, code="ERR_SEC_RBAC", details=details)

class RawNarrativeStoreForbiddenError(IntegrationException):
    """Raised when attempting to store raw clinical narrative in persistent storage."""
    def __init__(self, message: str = "Storing raw clinical narratives is strictly prohibited.", details: dict = None):
        super().__init__(message, code="ERR_SEC_RAW_NARRATIVE", details=details)


# Compiled regex patterns for PII scanning
REGEX_PATTERNS = {
    "SSN": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "EMAIL": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "PHONE_US": re.compile(r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    "PHONE_IL": re.compile(r"\b(?:\+?972[-.\s]?|0)5\d[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    "MRN_OR_ID": re.compile(r"\b(?:MRN|ID|PASSPORT|SSN)\s*[:=]?\s*\d{6,9}\b", re.IGNORECASE),
    "SYNTHETIC_PII": re.compile(r"\b(?:patient identifier|SSN pattern|phone/email|synthetic PII)\b", re.IGNORECASE),
}

# Role Mapping & Access Control Matrix (matching ACCESS_CONTROL_MATRIX.json)
ROLE_ALIASES = {
    "ROLE_INTERNAL_THERAPIST": "THERAPIST_PILOT_USER",
    "THERAPIST_PILOT_USER": "THERAPIST_PILOT_USER",
    "LICENSED_THERAPIST": "THERAPIST_PILOT_USER",
    "THERAPIST": "THERAPIST_PILOT_USER",
    "ROLE_CLINICAL_REVIEWER": "CLINICAL_REVIEWER",
    "CLINICAL_REVIEWER": "CLINICAL_REVIEWER",
    "ROLE_CONTENT_REVIEWER": "CONTENT_REVIEWER",
    "CONTENT_REVIEWER": "CONTENT_REVIEWER",
    "ROLE_SYSTEM_OPERATOR": "SYSTEM_OPERATOR",
    "SYSTEM_OPERATOR": "SYSTEM_OPERATOR",
    "ROLE_SECURITY_AUDITOR": "SECURITY_AUDITOR",
    "SECURITY_AUDITOR": "SECURITY_AUDITOR",
}

# Resource ID -> Allowed Canonical Roles
RESOURCE_PERMISSIONS: Dict[str, Set[str]] = {
    "pilot_query_advisor": {"THERAPIST_PILOT_USER"},
    "pilot_note_summarize": {"THERAPIST_PILOT_USER"},
    "knowledge_graph_read": {"THERAPIST_PILOT_USER", "CLINICAL_REVIEWER", "CONTENT_REVIEWER"},
    "knowledge_graph_write": set(),  # EXPLICIT DENY for ALL
    "novelty_candidate_queue": {"CLINICAL_REVIEWER", "CONTENT_REVIEWER", "SECURITY_AUDITOR"},
    "audit_logs": {"SECURITY_AUDITOR", "CLINICAL_REVIEWER"},
    "feature_flags": {"SYSTEM_OPERATOR", "SECURITY_AUDITOR"},
    "system_telemetry": {"SYSTEM_OPERATOR", "SECURITY_AUDITOR"},
}

class SecurityPolicy:
    """
    Enforces security, data privacy, PII rejection, and RBAC authorization.
    """

    @staticmethod
    def scan_pii(text: str) -> List[str]:
        """Scans text for PII patterns and returns list of detected PII types."""
        if not text:
            return []
        detected = []
        for pii_type, pattern in REGEX_PATTERNS.items():
            if pattern.search(text):
                detected.append(pii_type)
        return detected

    def validate_input(self, text: str) -> None:
        """
        Validates input text against PII patterns.
        Raises PIIRejectedError if any PII is detected.
        """
        detected = self.scan_pii(text)
        if detected:
            raise PIIRejectedError(
                message=f"PII detected in request ({', '.join(detected)}). Patient data must be fully anonymized.",
                details={"detected_types": detected}
            )

    @staticmethod
    def sanitize_text(text: str) -> str:
        """Sanitizes/redacts PII from text for safe audit logging."""
        if not text:
            return text
        sanitized = text
        sanitized = REGEX_PATTERNS["EMAIL"].sub("[REDACTED_EMAIL]", sanitized)
        sanitized = REGEX_PATTERNS["SSN"].sub("[REDACTED_SSN]", sanitized)
        sanitized = REGEX_PATTERNS["PHONE_IL"].sub("[REDACTED_PHONE]", sanitized)
        sanitized = REGEX_PATTERNS["PHONE_US"].sub("[REDACTED_PHONE]", sanitized)
        sanitized = REGEX_PATTERNS["MRN_OR_ID"].sub("[REDACTED_ID]", sanitized)
        return sanitized

    def validate_narrative_storage(self, store_raw_narrative: bool) -> None:
        """
        Validates raw clinical narrative storage policy.
        Raises RawNarrativeStoreForbiddenError if store_raw_narrative is True.
        """
        if store_raw_narrative:
            raise RawNarrativeStoreForbiddenError()

    def check_access(
        self,
        user_role: str,
        resource_id: str,
        action: str = "POST",
        context: Optional[IntegrationContext] = None
    ) -> bool:
        """
        Evaluates RBAC least-privilege permissions based on ACCESS_CONTROL_MATRIX.json.
        Raises AccessDeniedError if role lacks permission.
        """
        canonical_role = ROLE_ALIASES.get(user_role.upper() if user_role else "", user_role)
        allowed_roles = RESOURCE_PERMISSIONS.get(resource_id, set())

        if canonical_role not in allowed_roles:
            raise AccessDeniedError(
                message=f"Role '{user_role}' (canonical: '{canonical_role}') is denied access to resource '{resource_id}'",
                details={"user_role": user_role, "resource_id": resource_id, "action": action}
            )

        return True
