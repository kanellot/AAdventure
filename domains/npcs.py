from typing import Optional, List
from domains.base import Entity
from domains.conversation import ConversationRecord
from pydantic import BaseModel, Field

class Service(BaseModel):
    """Representa un servicio que un NPC puede ofrecer al jugador."""
    id: str
    type: str
    affinity: Optional[float] = None
    cost: Optional[int] = None
    description: str

class NPC(Entity):
    """Representa un personaje no jugador (Non-Player Character) en el mundo."""
    state: str = "none"
    current_location: Optional[str] = None
    conversation: Optional[ConversationRecord] = None
    services: List[Service] = Field(default_factory=list)
    affinity: float = 0.5
