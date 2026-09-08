from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field
from domains.world import Place
from domains.npcs import NPC
from domains.player import Player
from domains.conversation import ConversationRecord



# =====================================================================
# MODELOS BASE PARA LA ARQUITECTURA DE COMPORTAMIENTOS (BEHAVIOUR)
# =====================================================================

class ContextType(BaseModel):
    """Clase base para todos los modelos de contexto que se envían al LLM."""
    pass


class ResponseType(BaseModel):
    """Clase base para todos los modelos de respuesta estructurada que genera el LLM."""
    pass


class ResultType(BaseModel):
    """Clase base para todos los modelos de respuesta estructurada que genera el Game engine."""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


# =====================================================================
# MODELOS DE DOMINIO Y PROYECCIÓN
# =====================================================================

class PlaceProjection(BaseModel):
    """Proyección simplificada de un lugar (Place) que contiene sólo id y nombre."""
    id: str
    name: str


class NPCProjection(BaseModel):
    """Proyección simplificada de un NPC que contiene sólo id y nombre."""
    id: str
    name: str


class TurnSummary(BaseModel):
    """Representa un resumen simplificado de un turno anterior."""
    player_input: str
    narration: str


class RuntimeState(BaseModel):
    """Información puramente de runtime y control de juego."""
    player_state: str = "EXPLORE"
    player_target: str = ""
    current_place: Optional[PlaceProjection] = None
    prev_place: Optional[PlaceProjection] = None
    travel_speed: float = 4.5
    elapsed_time: int = 0


class GameState(BaseModel):
    """Representa la proyección del estado y percepción del jugador (Scope reducido).
    Este objeto es idóneo para convertirse a JSON y enviarse al LLM.
    """
    state: RuntimeState
    player: Player
    npcs: Dict[str, NPC] = Field(default_factory=dict)
    place: Optional[Place] = None




class ActionCommand(BaseModel):
    """Comando directo de acción emitido desde la UI o consola."""
    action: str  # "MOVE", "LOOK", "TALK"
    target: str  # Nombre o ID del lugar o NPC


class MarkdownContext(ContextType):
    """Contenedor genérico para pasar un contexto en formato Markdown al LLM."""
    markdown_content: str

    def to_markdown(self) -> str:
        return self.markdown_content


# =====================================================================
# MODELOS PARA MOVE NARRATOR Y EXPLAIN LOOK NARRATOR
# =====================================================================

class MoveNarratorCtx(ContextType):
    """Contexto para la acción de narración de desplazamiento."""
    origin_place: Optional[Place] = None
    destination_place: Optional[Place] = None
    player_input: Optional[str] = None
    path_taken: List[Place] = Field(default_factory=list)

    def to_markdown(self) -> str:
        md = "# TRANSICIÓN DE MOVIMIENTO\n"
        if self.origin_place:
            md += f"## ORIGEN\n* **Nombre**: {self.origin_place.name}\n* **Descripción**: {self.origin_place.description}\n"
        if self.path_taken:
            md += "## CAMINO RECORRIDO (LUGARES INTERMEDIOS)\n"
            for p in self.path_taken:
                md += f"* **Nombre**: {p.name}\n* **Descripción**: {p.description}\n"
        if self.destination_place:
            md += f"## DESTINO\n* **Nombre**: {self.destination_place.name}\n* **Descripción**: {self.destination_place.description}\n"
        if self.player_input:
            md += f"\n* **player_input**: \"{self.player_input}\""
        return md


class MoveNarratorResponse(ResponseType):
    """Respuesta del LLM para la narración de desplazamiento."""
    msg: str


class MoveNarratorResult(ResultType):
    """Resultado del Game Engine para la narración de desplazamiento."""
    pass


class ExplainLookNarratorCtx(ContextType):
    """Contexto para la acción de explicación/inspección de entidades."""
    entity: Optional[Union[Place, NPC]] = None
    player_input: Optional[str] = None
    failed_reason: Optional[str] = None

    def to_markdown(self) -> str:
        md = "# DETALLE DE ENTIDAD\n"
        if self.entity:
            md += f"## ENTIDAD: {self.entity.name}\n"
            md += f"* **ID**: {self.entity.id}\n"
            md += f"* **Descripción actual**: {self.entity.description}\n"
        if self.player_input:
            md += f"\n* **player_input**: \"{self.player_input}\""
        if self.failed_reason:
            md += f"\n\n> [!WARNING]\n> La acción del jugador falló. Razón: {self.failed_reason}. Narra de manera inmersiva por qué falló o no fue posible en este entorno."
        return md


class ExplainLookResponse(ResponseType):
    """Respuesta descriptiva del LLM para la acción de explicación/inspección."""
    msg: str


class ExplainLookResult(ResultType):
    """Resultado del Game Engine para la acción de explicación/inspección."""
    pass
