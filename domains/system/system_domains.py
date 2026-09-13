"""Modelos del sistema, contextos de ejecución y proyecciones de estado."""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, computed_field, model_validator
from domains.base import Entity
from domains.conversation import ConversationRecord
from domains.npcs import NPC
from domains.player import Player
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


from domains.projections import PlaceProjection


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


class GameState(BaseModel):
    """Estado activo simplificado del jugador y de la partida."""

    # Recursos e inventario
    gold: int = 0
    inventory: List[str] = Field(default_factory=list)

    # Percepción y lugares
    current_location: str = ""
    visited_places: List[str] = Field(default_factory=list)
    known_places: List[str] = Field(default_factory=list)

    # Entidades conocidas (nombradas o descubiertas)
    known_npcs: List[str] = Field(default_factory=list)
    known_objs: List[str] = Field(default_factory=list)

    # Entidades en el lugar actual (en tiempo real)
    visible_npcs: List[str] = Field(default_factory=list)
    visible_objs: List[str] = Field(default_factory=list)

    # Máquina de estados jerárquica de Lore
    active_lore_blocks: List[str] = Field(default_factory=list)
    done_lore_blocks: List[str] = Field(default_factory=list)

    # Runtime de interacción y simulación
    player_state: str = "EXPLORE"
    player_target: str = ""
    active_npc_affinity: Optional[float] = None
    elapsed_time: int = 0
    travel_speed: float = 4.5

    # Campos opcionales para retrocompatibilidad total
    player: Optional[Player] = None
    place: Optional[Place] = None
    prev_place: Optional[Any] = None
    current_place: Optional[Any] = None
    npcs: Dict[str, NPC] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _sync_legacy_init(cls, data: Any) -> Any:
        if isinstance(data, dict):
            p = data.get("player")
            if p:
                if isinstance(p, dict):
                    data.setdefault("gold", p.get("gold", 0))
                    data.setdefault("inventory", p.get("inventory", []))
                    data.setdefault("current_location", p.get("initial_place") or p.get("player_location", ""))
                    data.setdefault("visited_places", p.get("visited_places", []))
                    data.setdefault("known_places", p.get("unlocked_places", []))
                    data.setdefault("known_npcs", p.get("known_npcs", []))
                    data.setdefault("known_objs", p.get("known_items", []))
                elif hasattr(p, "gold"):
                    data.setdefault("gold", getattr(p, "gold", 0))
                    data.setdefault("inventory", list(getattr(p, "inventory", [])))
                    data.setdefault("current_location", getattr(p, "initial_place", None) or getattr(p, "player_location", ""))
                    data.setdefault("visited_places", list(getattr(p, "visited_places", [])))
                    data.setdefault("known_places", list(getattr(p, "unlocked_places", [])))
                    data.setdefault("known_npcs", list(getattr(p, "known_npcs", [])))
                    data.setdefault("known_objs", list(getattr(p, "known_items", [])))
            plc = data.get("place")
            if plc:
                p_name = plc.get("name") if isinstance(plc, dict) else getattr(plc, "name", "")
                p_id = plc.get("id") if isinstance(plc, dict) else getattr(plc, "id", "")
                if not data.get("current_location"):
                    data["current_location"] = p_id or p_name
            if not data.get("current_location"):
                data["current_location"] = ""
        return data

    # Shims de compatibilidad para evitar roturas durante la transición
    @property
    def data(self) -> "GameState":
        return self

    @property
    def state(self) -> "GameState":
        return self


class ActionCommand(BaseModel):
    """Comando directo de acción emitido desde la interfaz de usuario."""

    action: str
    target: str


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
