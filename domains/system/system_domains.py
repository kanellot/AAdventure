"""Modelos del sistema, contextos de ejecución y proyecciones de estado."""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from domains.base import Entity
from domains.npcs import NPC
from domains.projections import PlaceProjection
from domains.world import Place


class ContextType(BaseModel):
    """Contexto base transferible al LLM para la generación de contenido."""

    directive: Optional[str] = None


class ResponseType(BaseModel):
    """Respuesta estructurada base devuelta por el LLM."""

    pass


class ResultType(BaseModel):
    """Resultado estructurado base devuelto por la ejecución de una acción."""

    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


class RuntimeState(BaseModel):
    """Estado volátil de runtime y control de juego."""

    player_state: str = "EXPLORE"
    player_target: str = ""
    current_place: Optional[PlaceProjection] = None
    prev_place: Optional[PlaceProjection] = None
    travel_speed: float = 4.5
    elapsed_time: int = 0
    inspection_history: List[Dict[str, str]] = Field(default_factory=list)
    active_npc_affinity: Optional[float] = None


class MoveNarratorCtx(ContextType):
    """Contexto estructurado para la narración de desplazamiento."""

    origin_place: Optional[Place] = None
    destination_place: Optional[Place] = None
    player_input: Optional[str] = None
    path_taken: List[Place] = Field(default_factory=list)
    estimated_travel_time: int = 0
    directive: Optional[str] = None


class MoveNarratorResponse(ResponseType):
    """Respuesta generada por el LLM para narrar el movimiento."""

    msg: str = Field(description="Descripción inmersiva del viaje y llegada al nuevo lugar (2 a 4 frases).")


class MoveNarratorResult(ResultType):
    """Resultado de la ejecución de una acción de desplazamiento."""

    pass


class ExplainLookNarratorCtx(ContextType):
    """Contexto estructurado para la narración de inspección o explicación."""

    entity: Optional[Union[Place, NPC, Entity]] = None
    inspection_history: List[Dict[str, str]] = Field(default_factory=list)
    player_input: Optional[str] = None
    directive: Optional[str] = None
    failed_reason: Optional[str] = None


class ExplainLookResponse(ResponseType):
    """Respuesta generada por el LLM para narrar una inspección."""

    msg: str = Field(description="Respuesta explicativa o descriptiva del Dungeon Master (1 a 3 frases).")


class ExplainLookResult(ResultType):
    """Resultado de la ejecución de una acción de inspección."""

    pass


ExplainLookNarratorCtx.model_rebuild()
