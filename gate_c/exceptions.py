class NoveltyDiscoveryError(Exception):
    """Base exception for novelty discovery engine."""
    pass

class MissingProvenanceError(NoveltyDiscoveryError):
    """Raised when evidence lacks valid provenance."""
    pass

class PHIDetectedError(NoveltyDiscoveryError):
    """Raised when identifiable patient information is detected."""
    pass

class OutOfScopeError(NoveltyDiscoveryError):
    """Raised for out of scope actions, such as autonomous clinical requests."""
    pass

class UnknownThresholdError(NoveltyDiscoveryError):
    """Raised when a threshold is undefined or unknown (fails closed)."""
    pass
