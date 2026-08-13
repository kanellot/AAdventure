from typing import Optional
from domains.base import Entity

class NPC(Entity):
    """Representa un personaje no jugador (Non-Player Character) en el mundo."""
    state: str = "none"
    current_location: Optional[str] = None
