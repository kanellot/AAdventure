from typing import List, Dict
from pydantic import BaseModel, Field

class ConversationRecord(BaseModel):
    """Representa el registro estructurado de una conversación con un NPC."""
    id: str
    msg: List[Dict[str, str]] = Field(default_factory=list)
