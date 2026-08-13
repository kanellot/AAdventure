from pydantic import BaseModel, ConfigDict

class Entity(BaseModel):
    """Clase base para todas las entidades del mundo de AAdventure."""
    model_config = ConfigDict(extra='allow')
    id: str
    name: str
    description: str
