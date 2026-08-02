class GateDException(Exception):
    """Base exception for Gate D Consultation Engine."""
    pass

class SafetyViolationError(GateDException):
    """Raised when a safety boundary is crossed (e.g., PII detected, diagnosis attempted)."""
    pass

class EvidenceMissingError(GateDException):
    """Raised when unsupported claims are made."""
    pass

class UnauthorizedDataError(GateDException):
    """Raised when using unreviewed Gate C novelty."""
    pass

class PIIRejectedError(SafetyViolationError):
    """Raised when live patient data or PII is detected."""
    pass
