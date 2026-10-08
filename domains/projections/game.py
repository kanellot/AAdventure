"""Modelos de proyección (DTOs) para la interfaz de usuario de juego (Game UI)."""

from typing import List, Literal, Optional, Union

from pydantic import BaseModel, Field

from domains.game_state import NotebookEntry
from domains.projections.debug import TurnDebugProjection


class ActionCommandProjection(BaseModel):
    """Comando directo de acción emitido por la interfaz de usuario hacia el motor."""

    action: str
    target: str


class TurnOutput(BaseModel):
    """Mensaje y estado emitido en el turno actual."""

    author: str
    type: Literal["msg", "popup"] = "msg"
    msg: str
    player_state: str = "EXPLORE"
    popup_title: Optional[str] = None
    popup_message: Optional[str] = None


class MapItemDTO(BaseModel):
    """Ítem visible en un lugar del mapa."""

    id: str
    name: str
    visible: bool = True


class MapNPCDTO(BaseModel):
    """NPC en un lugar del mapa con su estado de conocimiento."""

    id: str
    name: str
    status: Literal["visible", "Known"] = "visible"


class MapPlaceDTO(BaseModel):
    """Lugar del mapa con su estado de niebla de guerra y entidades contenidas."""

    id: str
    name: str
    status: Literal["visited", "visible", "hidden"] = "visible"
    entities: List[Union[MapNPCDTO, MapItemDTO]] = Field(default_factory=list)


class MapLocationDTO(BaseModel):
    """Localización que agrupa lugares en el mapa."""

    id: str
    name: str
    places: List[MapPlaceDTO] = Field(default_factory=list)


class WorldMapProjection(BaseModel):
    """Mapa consolidado del mundo descubierto según la niebla de guerra."""

    locations: List[MapLocationDTO] = Field(default_factory=list)


class InventoryItemDTO(BaseModel):
    """Ítem en posesión del jugador."""

    id: str
    name: str
    description: str = ""


class InventoryProjection(BaseModel):
    """Inventario consolidado con ítems y oro del jugador."""

    items: List[InventoryItemDTO] = Field(default_factory=list)
    gold: int = 0


class NotebookProjection(BaseModel):
    """Cuaderno de misiones activas y completadas."""

    quests: List[NotebookEntry] = Field(default_factory=list)


class TurnResultProjection(BaseModel):
    """Resultado unificado de turno entregado a la UI en cada turno."""

    output: TurnOutput
    map: WorldMapProjection
    inventory: InventoryProjection
    notebook: NotebookProjection
    debug: Optional[TurnDebugProjection] = None


# DTOs complementarios para clientes UI
class PlaceProjection(BaseModel):
    """Proyección simplificada de un lugar."""

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
