from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from domains.world import Place
from domains.npcs import NPC
from domains.conversation import ConversationRecord


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


class GameState(BaseModel):
    """Representa la proyección del estado y percepción del jugador (Scope reducido).
    Este objeto es idóneo para convertirse a JSON y enviarse al LLM.
    """
    player_id: str
    player_name: str
    player_description: str
    player_state: str
    player_target: str
    gold: int = 10
    active_quest: Optional[str] = None
    
    # Entidades dentro del alcance visual del jugador
    current_place: Optional[Place] = None
    visible_npcs: List[NPCProjection] = Field(default_factory=list)
    prev_turns: List[TurnSummary] = Field(default_factory=list)


# =====================================================================
# MODELOS PARA EL CLASIFICADOR
# =====================================================================

class ActionResponse(BaseModel):
    """Respuesta del clasificador de acciones del jugador."""
    action: Optional[str] = None
    target: Optional[List[str]] = None


class ActionCtx(BaseModel):
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


class NarrativeContext(BaseModel):
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


class NarrativeResponse(BaseModel):
    """Respuesta del narrador (Dungeon Master)."""
    msg: str


# =====================================================================
# MODELOS PARA EL DIÁLOGO
# =====================================================================

class DialogueCtx(BaseModel):
    """Contexto específico de la conversación con el NPC."""
    npc: NPC
    conversation: Optional[ConversationRecord] = None


class DialogueContext(BaseModel):
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


class DialogueResponse(BaseModel):
    """Respuesta estructurada del NPC en el diálogo."""
    msg: str
    state: str
    service: Optional[str] = None
