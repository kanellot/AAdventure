"""Modelos de dominio para personajes no jugadores (NPCs) y sus servicios."""

from typing import List, Optional
from pydantic import BaseModel, Field
from domains.base import Entity
from domains.conversation import ConversationRecord
from domains.lore import LoreBlock


class NPCInfo(BaseModel):
    """Información simplificada de un NPC."""

    id: str
    name: str = ""


class NPCMotivations(BaseModel):
    """Motivaciones y preferencias de un NPC para modular afinidad."""

    likes: List[str] = Field(default_factory=list)
    dislikes: List[str] = Field(default_factory=list)


class Service(BaseModel):
    """Servicio u oferta que un NPC puede ofrecer al jugador."""

    id: str
    type: str
    min_affinity: float = 0.0
    max_affinity: float = 1.0
    cost: Optional[int] = None
    description: str


class NPC(Entity):
    """Personaje no jugador (Non-Player Character) dentro del mundo."""

    state: str = "none"
    occupation: Optional[str] = None
    current_location: Optional[str] = None
    conversation: Optional[ConversationRecord] = None
    services: List[Service] = Field(default_factory=list)
    affinity: float = 0.5
    motivations: NPCMotivations = Field(default_factory=NPCMotivations)
    dynamic_lore: List[LoreBlock] = Field(default_factory=list)
