"""
controlled_integration/exceptions.py
-----------------------------------
Isolated exception hierarchy for integration errors.
"""

class IntegrationException(Exception):
    """Base exception for all integration errors."""
    def __init__(self, message: str, code: str = "ERR_INT_BASE", details: dict = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}

class BoundaryViolationError(IntegrationException):
    """Raised when an unreviewed novelty item attempts to cross into Gate D."""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, code="ERR_BND_01", details=details)

class FeatureFlagError(IntegrationException):
    """Raised when an invalid feature flag combination or mode is requested."""
    def __init__(self, message: str, code: str = "ERR_FF_02", details: dict = None):
        super().__init__(message, code=code, details=details)

class UnreviewedNoveltyLeakError(BoundaryViolationError):
    """Specific violation when DISCOVERY_ONLY or PENDING_HUMAN_REVIEW novelty reaches Gate D boundary."""
    def __init__(self, candidate_id: str, status: str, review_status: str):
        msg = f"Candidate '{candidate_id}' blocked from crossing boundary: status={status!r}, review_status={review_status!r}"
        super().__init__(msg, details={"candidate_id": candidate_id, "status": status, "review_status": review_status})

class ExternalIOCallForbiddenError(IntegrationException):
    """Raised if live network, Neo4j, or LLM I/O is attempted in adapter layer."""
    def __init__(self, operation: str):
        super().__init__(f"Operation '{operation}' violates zero external I/O isolation rule.", code="ERR_DEP_IO")

class KnowledgeWriteForbiddenError(IntegrationException):
    """Raised if write to official knowledge or persistent graph is attempted."""
    def __init__(self, target: str):
        super().__init__(f"Write operation to '{target}' is strictly forbidden.", code="ERR_DEP_WRITE")

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
