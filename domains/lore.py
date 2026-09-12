"""Modelos de dominio para el sistema de Lore dinámico y condicional."""

from typing import Any, List, Optional
from pydantic import BaseModel, Field


class LoreConditions(BaseModel):
    """Condiciones requeridas para activar o revelar un bloque de lore."""

    min_affinity: float = 0.0
    max_affinity: float = 1.0
    required_quests: List[str] = Field(default_factory=list)
    required_items: List[str] = Field(default_factory=list)
    required_gold: int = 0


class LoreEffects(BaseModel):
    """Efectos o mutaciones aplicadas al estado del juego al activarse el lore."""

    give_items: List[str] = Field(default_factory=list)
    take_items: List[str] = Field(default_factory=list)
    give_gold: int = 0
    take_gold: int = 0
    affinity_delta: float = 0.0
    unlock_quests: List[str] = Field(default_factory=list)
    unlock_places: List[str] = Field(default_factory=list)


class LoreBlock(BaseModel):
    """Bloque de información, secreto o reacción condicional para NPCs o lugares."""

    id: str
    title: Optional[str] = None
    trigger_phrases: List[str] = Field(default_factory=list)
    trigger_mode: str = "reactive"
    conditions: LoreConditions = Field(default_factory=LoreConditions)
    once: bool = True
    revealed: bool = False
    directive: str = ""
    effects: LoreEffects = Field(default_factory=LoreEffects)
