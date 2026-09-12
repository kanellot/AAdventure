"""Modelo de dominio para el jugador y su estado."""

from typing import List, Optional
from pydantic import Field
from domains.base import Entity


class Player(Entity):
    """Representa al jugador, su inventario, misiones y posición en el mundo."""

    player_location: Optional[str] = None
    state: str = "EXPLORE"
    gold: int = 10
    active_quest: Optional[str] = None
    completed_quests: List[str] = Field(default_factory=list)
    inventory: List[str] = Field(default_factory=list)
    unlocked_places: List[str] = Field(default_factory=list)
    visited_places: List[str] = Field(default_factory=list)
    travel_speed: float = 4.5
    elapsed_time: int = 0
