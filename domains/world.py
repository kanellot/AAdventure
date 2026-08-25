from typing import List, Dict
from pydantic import BaseModel, Field
from domains.base import Entity

class LocationInfo(BaseModel):
    """Información simplificada de una localización."""
    id: str
    nombre: str

class PlaceInfo(BaseModel):
    """Información simplificada de un lugar (lugar/sub-zona)."""
    id: str
    nombre: str

class Place(Entity):
    """Un lugar o sub-zona específica dentro de una localización."""
    visible_entities: List[str] = Field(default_factory=list)
    connections: Dict[str, str] = Field(default_factory=dict)

class Location(Entity):
    """Una localización mayor dentro del mundo (por ejemplo, un pueblo o una mazmorra)."""
    places: List[Place] = Field(default_factory=list)

class World(Entity):
    """Representa el mundo completo del juego, que contiene múltiples localizaciones."""
    locations: List[Location] = Field(default_factory=list)
