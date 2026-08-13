from typing import Optional
from domains.base import Entity

class Player(Entity):
    """Representa al jugador dentro del juego con su estado y localización actual."""
    player_location: Optional[str] = None
    state: str = "none"
