from typing import Optional, List
from domains.base import Entity
from domains.conversation import ConversationRecord
from pydantic import BaseModel, Field

class NPCInfo(BaseModel):
    """Información simplificada de un NPC."""
    id: str
    nombre: str

class NPCMotivations(BaseModel):
    """Representa las motivaciones y preferencias de un NPC para modular la afinidad."""
    likes: List[str] = Field(default_factory=list)
    dislikes: List[str] = Field(default_factory=list)

class Service(BaseModel):
    """Representa un servicio que un NPC puede ofrecer al jugador."""
    id: str
    type: str
    min_affinity: float = 0.0
    max_affinity: float = 1.0
    cost: Optional[int] = None
    description: str

class LoreBlock(BaseModel):
    """Representa un fragmento de información/secreto que se desbloquea bajo ciertas condiciones."""
    id: str
    required_affinity: float = 0.0
    required_quests: List[str] = Field(default_factory=list)
    content: str

class NPC(Entity):
    """Representa un personaje no jugador (Non-Player Character) en el mundo."""
    state: str = "none"
    current_location: Optional[str] = None
    conversation: Optional[ConversationRecord] = None
    services: List[Service] = Field(default_factory=list)
    affinity: float = 0.5
    motivations: NPCMotivations = Field(default_factory=NPCMotivations)
    dynamic_lore: List[LoreBlock] = Field(default_factory=list)
