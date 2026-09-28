"""Modelo de dominio para ítems y objetos del juego."""

from typing import Optional
from domains.base import Entity


class Item(Entity):
    """Representa un ítem u objeto del juego que puede estar ubicado en un lugar o en el inventario."""

    state: str = "default"
    initial_location: Optional[str] = None

