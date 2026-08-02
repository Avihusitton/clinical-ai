from typing import List, Dict, Any, Optional
from .models import ConsultationAuditEvent
import uuid
from datetime import datetime

class AuditTrail:
    def __init__(self):
        self.events: List[ConsultationAuditEvent] = []

    def log_event(self, event_type: str, therapist_id: str, request_id: Optional[str], details: Dict[str, Any]) -> ConsultationAuditEvent:
        event = ConsultationAuditEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            request_id=request_id,
            therapist_id=therapist_id,
            details=details,
            timestamp=datetime.utcnow()
        )
        self.events.append(event)
        return event

    def get_events_for_request(self, request_id: str) -> List[ConsultationAuditEvent]:
        return [e for e in self.events if e.request_id == request_id]
