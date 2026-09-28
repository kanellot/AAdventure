"""Modelo de dominio para el jugador y su estado inicial."""

from typing import List, Optional, Any
from pydantic import Field, model_validator
from domains.base import Entity


class Player(Entity):
    """Representa al jugador, su inventario inicial, bloque activo y posición inicial en el mundo."""

    gold: int = 10
    inventory: List[str] = Field(default_factory=list)
    active_block: Optional[str] = None
    initial_location: str = ""

    # Campos de soporte y estado
    state: str = "EXPLORE"
    travel_speed: float = 4.5
    elapsed_time: int = 0
    active_quest: Optional[str] = None
    completed_quests: List[str] = Field(default_factory=list)
    known_npcs: List[str] = Field(default_factory=list)
    known_items: List[str] = Field(default_factory=list)
    visited_places: List[str] = Field(default_factory=list)
    unlocked_places: List[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def sync_active_block(cls, values: Any) -> Any:
        if isinstance(values, dict):
            d = dict(values)
            ab = d.get("active_block")
            aq = d.get("active_quest")
            if not ab and aq:
                d["active_block"] = aq
            elif ab and not aq:
                d["active_quest"] = ab
            return d

# Re-exportación para compatibilidad de importación
from domains.game_state import GameState

__all__ = ["Player", "GameState"]
