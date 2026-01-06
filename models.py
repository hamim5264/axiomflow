from pydantic import BaseModel
from typing import Dict, Optional, Any


class Event(BaseModel):
    event_type: str
    actor_id: Optional[str] = None
    message: Optional[str] = None
    metadata: Dict[str, Any] = {}
