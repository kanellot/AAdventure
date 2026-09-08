from typing import Optional, List
from pydantic import Field
from domains.base import Entity

class Player(Entity):
    """Representa al jugador dentro del juego con su estado y localización actual."""
    player_location: Optional[str] = None
    state: str = "EXPLORE"
    gold: int = 10
    active_quest: Optional[str] = None
    completed_quests: List[str] = Field(default_factory=list)
    travel_speed: float = 4.5
    elapsed_time: int = 0
