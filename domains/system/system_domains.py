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
    player_state: str = "NORMAL"
    player_target: str = ""
    current_place: Optional[PlaceProjection] = None
    prev_place: Optional[PlaceProjection] = None


class GameState(BaseModel):
    """Representa la proyección del estado y percepción del jugador (Scope reducido).
    Este objeto es idóneo para convertirse a JSON y enviarse al LLM.
    """
    state: RuntimeState
    player: Player
    npcs: Dict[str, NPC] = Field(default_factory=dict)
    place: Optional[Place] = None




class ActionResponse(ResponseType):
    """Respuesta del clasificador de acciones del jugador."""
    action: Optional[str] = None
    target: Optional[List[str]] = None

class ActionCtx(ContextType):
    """Contexto de entrada para el clasificador de acciones."""
    places: List[PlaceProjection] = Field(default_factory=list)
    npc: List[NPCProjection] = Field(default_factory=list)
    player_input: str

    def to_markdown(self) -> str:
        md = "## LUGARES EN LA LOCALIZACIÓN\n"
        if self.places:
            for p in self.places:
                md += f"- `{p.id}`: {p.name}\n"
        else:
            md += "- (Ninguno)\n"
            
        md += "\n## NPCS EN LA LOCALIZACIÓN\n"
        if self.npc:
            for n in self.npc:
                md += f"- `{n.id}`: {n.name}\n"
        else:
            md += "- (Ninguno)\n"
            
        md += f"\n* **player_input**: \"{self.player_input}\""
        return md


# =====================================================================
# MODELOS PARA EL NARRADOR
# =====================================================================

class NarrativeCtx(BaseModel):
    """Contexto del entorno físico y NPCs visibles en el turno actual."""
    current_place: Optional[Place] = None
    visible_npcs: List[NPC] = Field(default_factory=list)


class NarrativeContext(ContextType):
    """Contenedor del contexto de narración enviado al LLM del narrador."""
    narrative_ctx: NarrativeCtx
    player_input: str

    def to_markdown(self) -> str:
        md = "## LUGAR ACTUAL\n"
        cp = self.narrative_ctx.current_place
        if cp:
            md += f"* **Nombre**: {cp.name}\n"
            md += f"* **Descripción**: {cp.description}\n"
        else:
            md += "* (Ninguno)\n"

        md += "\n## NPCS VISIBLES AQUÍ\n"
        v_npcs = self.narrative_ctx.visible_npcs
        if v_npcs:
            for n in v_npcs:
                md += f"* **{n.name}** (`{n.id}`): {n.description}\n"
        else:
            md += "* (Ninguno)\n"

        md += f"\n* **player_input**: \"{self.player_input}\""
        return md


class NarrativeResponse(ResponseType):
    """Respuesta del narrador (Dungeon Master)."""
    msg: str


# =====================================================================
# MODELOS PARA EL DIÁLOGO
# =====================================================================

class DialogueCtx(BaseModel):
    """Contexto específico de la conversación con el NPC."""
    npc: NPC
    conversation: Optional[ConversationRecord] = None


class DialogueContext(ContextType):
    """Contenedor del contexto de diálogo enviado al LLM de conversación."""
    dialogue_ctx: DialogueCtx
    player_input: str

    def to_markdown(self) -> str:
        n = self.dialogue_ctx.npc
        md = "## NPC CON EL QUE HABLAS\n"
        md += f"* **Nombre**: {n.name} (ID: `{n.id}`)\n"
        md += f"* **Descripción**: {n.description}\n"
        if n.services:
            md += "\n## SERVICIOS QUE OFRECE ESTE NPC\n"
            for s in n.services:
                md += f"* `{s.id}` (tipo: {s.type}): {s.description}"
                if s.cost is not None:
                    md += f" (costo: {s.cost} oro)"
                md += "\n"

        md += "\n## HISTORIAL DE CONVERSACIÓN\n"
        conv = self.dialogue_ctx.conversation
        if conv and conv.msg:
            for line in conv.msg:
                sender = list(line.keys())[0]
                text = line[sender]
                md += f"* **{sender}**: {text}\n"
        else:
            md += "* (No hay mensajes previos)\n"

        md += f"\n* **player_input**: \"{self.player_input}\""
        return md


class DialogueResponse(ResponseType):
    """Respuesta estructurada del NPC en el diálogo."""
    msg: str
    state: str
    service: Optional[str] = None


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

    def to_markdown(self) -> str:
        md = "# TRANSICIÓN DE MOVIMIENTO\n"
        if self.origin_place:
            md += f"## ORIGEN\n* **Nombre**: {self.origin_place.name}\n* **Descripción**: {self.origin_place.description}\n"
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
