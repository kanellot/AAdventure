"""Entidad base del dominio del juego."""

from typing import List
from pydantic import BaseModel, ConfigDict, Field
from domains.lore import LoreBlock


class Entity(BaseModel):
    """Entidad base para todos los objetos, lugares y personajes del juego."""

    model_config = ConfigDict(extra="allow")

    id: str
    name: str
    description: str
    dynamic_lore: List[LoreBlock] = Field(default_factory=list)
