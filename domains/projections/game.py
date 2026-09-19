"""Modelos de proyección (DTOs) exclusivos para la interfaz de usuario de juego (Game UI)."""

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

from domains.projections.debug import RagEvaluationProjection, TurnDebugProjection


class ActionCommandProjection(BaseModel):
    """Comando directo de acción emitido por la interfaz de usuario hacia el motor."""

    action: str
    target: str


# Alias para ergonomía y compatibilidad
ActionCommand = ActionCommandProjection


class PlaceProjection(BaseModel):
    """Proyección simplificada de un lugar para visualización en clientes de juego."""

    id: str
    name: str
    status: Literal["visited", "visible", "hidden"] = "visible"


class LocationHierarchyProjection(BaseModel):
    """Proyección de una localización con sus lugares y personajes visibles."""

    location_name: str
    places: List[PlaceProjection] = Field(default_factory=list)
    npcs: List[str] = Field(default_factory=list)


class WorldHierarchyProjection(BaseModel):
    """Proyección jerárquica del mapa descubierto bajo las reglas de la niebla de guerra."""

    locations: List[LocationHierarchyProjection] = Field(default_factory=list)


class MoveOptionProjection(BaseModel):
    """Opción de desplazamiento inmediato disponible para el jugador."""

    direction: str
    target: str
    distance: int
    terrain: str


class AvailableActionsProjection(BaseModel):
    """Conjunto de acciones y objetivos válidos para el turno actual."""

    moves: List[MoveOptionProjection] = Field(default_factory=list)
    npcs: List[str] = Field(default_factory=list)
    look_targets: List[str] = Field(default_factory=list)


class UIStateProjection(BaseModel):
    """Información consolidada para el HUD o barra de estado de la interfaz de juego."""

    player_name: str
    gold: int
    current_location: str
    formatted_time: str
    game_state: str = "EXPLORE"
    player_target: Optional[str] = None
    active_npc_affinity: Optional[float] = None
    can_send_message: bool = False
    allowed_actions: List[str] = Field(default_factory=list)


class TurnResultProjection(BaseModel):
    """Resultado de turno de juego consumido por la interfaz de usuario.
    
    Para una UI de juego convencional, únicamente son relevantes `author`, `msg` e `info_msg`.
    Los detalles técnicos y de diagnóstico de IA se encapsulan en el DTO opcional `debug`.
    """

    author: str
    msg: str
    info_msg: Optional[str] = None
    popup_message: Optional[str] = None
    popup_title: Optional[str] = None
    debug: Optional[TurnDebugProjection] = None

    def __init__(self, **data: Any):
        # Compatibilidad transparente con constructores legacy que pasaban campos debug sueltos
        if "debug" not in data or data["debug"] is None:
            prompt = data.pop("debug_prompt", None)
            raw = data.pop("debug_raw_response", None)
            struct = data.pop("debug_structured_response", None)
            res = data.pop("debug_engine_result", None)
            rag = data.pop("rag_evaluation", None)
            if any(x is not None for x in (prompt, raw, struct, res, rag)):
                data["debug"] = TurnDebugProjection(
                    prompt=prompt,
                    raw_response=raw,
                    structured_response=struct,
                    engine_result=res,
                    rag_evaluation=rag,
                )
        else:
            data.pop("debug_prompt", None)
            data.pop("debug_raw_response", None)
            data.pop("debug_structured_response", None)
            data.pop("debug_engine_result", None)
            data.pop("rag_evaluation", None)

        super().__init__(**data)

    # =========================================================================
    # Propiedades de compatibilidad para herramientas de depuración e inspección
    # =========================================================================

    @property
    def debug_prompt(self) -> Optional[str]:
        return self.debug.prompt if self.debug else None

    @property
    def debug_raw_response(self) -> Optional[str]:
        return self.debug.raw_response if self.debug else None

    @property
    def debug_structured_response(self) -> Optional[str]:
        return self.debug.structured_response if self.debug else None

    @property
    def debug_engine_result(self) -> Optional[str]:
        return self.debug.engine_result if self.debug else None

    @property
    def rag_evaluation(self) -> Optional[RagEvaluationProjection]:
        return self.debug.rag_evaluation if self.debug else None
