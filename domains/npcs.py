"""Modelos de dominio para personajes no jugadores (NPCs)."""

from typing import List, Optional

from pydantic import BaseModel, Field

from domains.base import Entity
from domains.conversation import ConversationRecord


class NPCMotivations(BaseModel):
    """Motivaciones y preferencias de un NPC para modular afinidad."""

    likes: List[str] = Field(default_factory=list)
    dislikes: List[str] = Field(default_factory=list)


class NPC(Entity):
    """Personaje no jugador (Non-Player Character) dentro del mundo."""

    state: str = "none"
    occupation: Optional[str] = None
    initial_location: Optional[str] = None
    conversation: Optional[ConversationRecord] = None
    affinity: float = 0.5
    motivations: NPCMotivations = Field(default_factory=NPCMotivations)
