"""Modelo de dominio para el jugador y su estado inicial."""

from typing import List, Optional
from pydantic import Field, model_validator
from domains.base import Entity


class Player(Entity):
    """Representa al jugador, su inventario inicial, bloque activo y posición inicial en el mundo."""

    gold: int = 10
    inventory: List[str] = Field(default_factory=list)
    active_block: Optional[str] = None
    initial_place: str = ""

    # Campos de soporte y compatibilidad
    player_location: Optional[str] = None
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
    def sync_locations(cls, values: dict):
        if isinstance(values, dict):
            # Sincronizar initial_place y player_location
            init_p = values.get("initial_place")
            loc = values.get("player_location")
            if not init_p and loc:
                values["initial_place"] = loc
            elif init_p and not loc:
                values["player_location"] = init_p
            # Sincronizar active_block y active_quest
            ab = values.get("active_block")
            aq = values.get("active_quest")
            if not ab and aq:
                values["active_block"] = aq
            elif ab and not aq:
                values["active_quest"] = ab
        return values
