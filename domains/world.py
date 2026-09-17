"""Modelos de dominio del mundo: localizaciones, lugares y conexiones."""

from typing import Dict, List
from pydantic import BaseModel, Field
from domains.base import Entity
from domains.items import Item


class Connection(BaseModel):
    """Conexión física entre dos lugares con distancia y tipo de terreno."""

    target: str
    distance: int
    terrain_type: str
    passable: bool = True



class Place(Entity):
    """Lugar o sub-zona específica dentro de una localización."""

    visible_entities: List[str] = Field(default_factory=list)
    items: List[Item] = Field(default_factory=list)
    connections: Dict[str, Connection] = Field(default_factory=dict)


class Location(Entity):
    """Localización mayor del mundo (ej. pueblo, bosque o mazmorra)."""

    places: List[Place] = Field(default_factory=list)


class World(Entity):
    """Mundo completo que agrupa todas las localizaciones."""

    locations: List[Location] = Field(default_factory=list)
