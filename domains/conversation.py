from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from domains.base import Entity

class Message(BaseModel):
    """Representa un mensaje individual enviado por una entidad en una conversación."""
    model_config = ConfigDict(extra='allow')
    id: str
    character: str  # Puede ser el nombre o ID del personaje
    msg: str        # Contenido del mensaje

# Alias para compatibilidad con la especificación original de MESSAGES
Messages = Message

class Conversation(Entity):
    """Representa un hilo de conversación activo entre el jugador y un NPC."""
    name: str = ""
    description: str = ""
    characters: List[str] = Field(default_factory=list)
    messages: List[Message] = Field(default_factory=list)
    location: Optional[str] = None
    place: Optional[str] = None
    npc: Optional[str] = None
