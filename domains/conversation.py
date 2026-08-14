from typing import List
from pydantic import BaseModel, Field


class Message(BaseModel):
    """Representa un mensaje individual enviado por una entidad en una conversación."""
    id: str
    character: str  # Nombre o ID del personaje que envía el mensaje (ej: player o npc_id)
    msg: str        # Contenido textual del mensaje


class Conversation(BaseModel):
    """Representa un hilo de conversación activo o finalizado entre el jugador y un NPC."""
    id: str
    character_01: str  # Normalmente "Player" o el ID del jugador
    character_02: str  # ID o nombre del NPC (ej: npc_tabernero)
    messages: List[Message] = Field(default_factory=list)
