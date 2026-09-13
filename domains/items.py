"""Modelo de dominio para Objetos/Items en el mundo de juego."""

from typing import Optional
from domains.base import Entity


class Item(Entity):
    """Representa un objeto del mundo que puede estar ligado a un lugar o al inventario."""

    state: str = "default"
    initial_place: Optional[str] = None


# Alias canónico
GameObject = Item
