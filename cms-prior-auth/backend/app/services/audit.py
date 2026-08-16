import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from app.db.connection import db_connection
from app.models.review import AuditEvent

class AuditLogService:
    @classmethod
    def log_event(
        cls,
        authorization_id: str,
        event_type: str,
        actor_id: str = "system",
        actor_type: str = "SYSTEM",
        related_object_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Logs an audit event in the database for end-to-end trace mapping."""
        db = db_connection.get_db()
        evt = AuditEvent(
            event_id=f"EVT-{authorization_id}-{uuid.uuid4().hex[:8]}",
            authorization_id=authorization_id,
            event_type=event_type,
            actor_type=actor_type,
            actor_id=actor_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            related_object_id=related_object_id,
            metadata=metadata or {}
        )
        db["audit_events"].insert_one(evt.model_dump())
        return evt.model_dump()
        
    @classmethod
    def get_events(cls, authorization_id: str) -> List[Dict[str, Any]]:
        """Gets all audit logs for a given authorization ID."""
        db = db_connection.get_db()
        events = list(db["audit_events"].find({"authorization_id": authorization_id}).sort("timestamp", 1))
        for e in events:
            e["_id"] = str(e["_id"])
        return events
