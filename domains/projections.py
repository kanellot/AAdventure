"""Modelos de proyección (DTOs) para la comunicación con la interfaz de usuario y clientes externos."""

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class PlaceProjection(BaseModel):
    """Proyección simplificada de un lugar para visualización en clientes."""

    id: str
    name: str
    status: Literal["visited", "visible", "hidden"] = "visible"


class LocationHierarchyProjection(BaseModel):
    """Proyección de una localización con sus lugares y personajes visibles."""

    location_name: str
    places: List[PlaceProjection] = Field(default_factory=list)
    npcs: List[str] = Field(default_factory=list)


class WorldHierarchyProjection(BaseModel):
    """Proyección jerárquica completa del mundo descubierto."""

    locations: List[LocationHierarchyProjection] = Field(default_factory=list)


class MoveOptionProjection(BaseModel):
    """Opción de desplazamiento inmediato disponible para el jugador."""

    direction: str
    target: str
    distance: int
    terrain: str


class AvailableActionsProjection(BaseModel):
    """Conjunto de acciones disponibles en el turno actual."""

    moves: List[MoveOptionProjection] = Field(default_factory=list)
    npcs: List[str] = Field(default_factory=list)
    look_targets: List[str] = Field(default_factory=list)


class UIStateProjection(BaseModel):
    """Información consolidada para el HUD o barra de estado de la interfaz."""

    player_name: str
    gold: int
    current_location: str
    formatted_time: str
    game_state: str = "EXPLORE"
    player_target: Optional[str] = None
    active_npc_affinity: Optional[float] = None
    can_send_message: bool = False
    allowed_actions: List[str] = Field(default_factory=list)



class PlayerSummaryProjection(BaseModel):
    """Ficha resumida y segura del jugador para la interfaz."""

    id: str
    name: str
    description: str = ""
    gold: int = 0
    player_location: Optional[str] = None
    state: str = "EXPLORE"
    active_quest: Optional[str] = None
    completed_quests: List[str] = Field(default_factory=list)
    inventory: List[str] = Field(default_factory=list)
    visited_places: List[str] = Field(default_factory=list)


class GameSnapshotProjection(BaseModel):
    """Instantánea inmutable del estado de juego para herramientas de inspección o guardado."""

    player: PlayerSummaryProjection
    current_place: Optional[str] = None
    prev_place: Optional[str] = None
    game_state: str = "EXPLORE"
    player_target: Optional[str] = None
    elapsed_time: int = 0
    formatted_time: str = ""
    discovered_places: List[str] = Field(default_factory=list)
    visible_npcs: List[str] = Field(default_factory=list)


class ConnectionProjection(BaseModel):
    """Proyección de una conexión de salida de un lugar."""

    direction: str
    target: str
    distance: int
    terrain_type: str = "normal"


class PlaceDetailProjection(BaseModel):
    """Detalle completo del lugar actual para el inspector."""

    id: str
    name: str
    description: str = ""
    visible_entities: List[str] = Field(default_factory=list)
    connections: List[ConnectionProjection] = Field(default_factory=list)


class GameStateProjection(BaseModel):
    """Proyección exhaustiva del estado del juego para el inspector visual."""

    player: PlayerSummaryProjection
    player_state: str = "EXPLORE"
    player_target: str = ""
    active_npc_affinity: Optional[float] = None
    current_place: Optional[str] = None
    current_place_detail: Optional[PlaceDetailProjection] = None
    prev_place: Optional[str] = None
    travel_speed: float = 4.5
    elapsed_time: int = 0
    formatted_time: str = ""
    discovered_places: List[str] = Field(default_factory=list)
    visible_npcs: List[str] = Field(default_factory=list)
    active_lore_blocks: List[str] = Field(default_factory=list)
    done_lore_blocks: List[str] = Field(default_factory=list)


class RagAntennaScoreProjection(BaseModel):
    """Puntuación y estado de una antena (frase gatillo) evaluada frente al prompt."""

    antenna: str
    lore_id: str
    lore_title: str
    score: float
    threshold: float = 0.65
    conditions_met: bool = True
    is_matched: bool = False
    is_injected: bool = False


class RagEvaluationProjection(BaseModel):
    """Evaluación semántica RAG del turno actual."""

    player_input: str = ""
    threshold: float = 0.65
    matched_lore_id: Optional[str] = None
    matched_antenna: Optional[str] = None
    injected_directive: Optional[str] = None
    antennas: List[RagAntennaScoreProjection] = Field(default_factory=list)


class TurnResultProjection(BaseModel):
    """Resultado estructurado de un turno de juego para clientes."""

    author: str
    msg: str
    info_msg: Optional[str] = None
    debug_prompt: Optional[str] = None
    debug_raw_response: Optional[str] = None
    debug_structured_response: Optional[str] = None
    debug_engine_result: Optional[str] = None
    rag_evaluation: Optional[RagEvaluationProjection] = None


class LoreConditionDetailProjection(BaseModel):
    """Detalle proyectado de una condición de activación o salida de LoreBlock."""

    entity_type: str
    entity_id: str
    sub_condition: str
    value: Optional[Any] = None
    is_negated: bool = False
    is_met: bool = False
    display_text: str = ""


class LoreBlockDetailProjection(BaseModel):
    """Proyección detallada de un LoreBlock para el inspector y visor gráfico de depuración."""

    id: str
    name: str
    title: str
    state: str = "unknown"  # "active", "done", "unknown"
    is_accessible: bool = True
    parent_id: Optional[str] = None
    trigger_mode: str = "proactive"
    rag_enabled: bool = False
    trigger_phrases: List[str] = Field(default_factory=list)
    conditions: List[LoreConditionDetailProjection] = Field(default_factory=list)
    exit_conditions: List[LoreConditionDetailProjection] = Field(default_factory=list)
    exit_rag_enabled: bool = False
    exit_trigger_phrases: List[str] = Field(default_factory=list)
    directive: str = ""
    force_action: bool = False
    on_active_summary: str = ""
    on_done_summary: str = ""


class LoreGraphProjection(BaseModel):
    """Proyección global de todos los LoreBlocks del juego para el visor gráfico HSM."""

    blocks: List[LoreBlockDetailProjection] = Field(default_factory=list)
    total_count: int = 0
    active_count: int = 0
    done_count: int = 0
    unknown_count: int = 0


