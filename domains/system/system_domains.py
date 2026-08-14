from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from domains.world import Place
from domains.npcs import NPC
from domains.conversation import Conversation


class NPCProjection(BaseModel):
    """Proyección simplificada de un NPC que contiene sólo id y nombre."""
    id: str
    name: str


class PlayerState(BaseModel):
    """Representa la proyección del estado y percepción del jugador (Scope reducido).
    Este objeto es idóneo para convertirse a JSON y enviarse al LLM.
    """
    player_id: str
    player_name: str
    player_description: str
    player_state: str
    player_target: str
    
    # Entidades dentro del alcance visual del jugador (lugar completo)
    current_place: Optional[Place] = None
    visible_npcs: List[NPCProjection] = Field(default_factory=list)
    active_conversations: Optional[Conversation] = None


class ActionItem(BaseModel):
    """Representa una acción individual identificada en la entrada del jugador."""
    action: str
    targets: Optional[List[str]] = Field(default_factory=list)
    content: Optional[str] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)


class Actions(BaseModel):
    """Contenedor de una o más acciones traducidas del lenguaje natural."""
    actions: List[ActionItem] = Field(..., min_length=1)


class Turn(BaseModel):
    """Representa el resultado final y consolidado de un turno completo."""
    action: Actions
    player_state: PlayerState
    player_input: str
    narration: str


class PreActionContext(BaseModel):
    """Contexto de entrada enviado al clasificador semántico."""
    player_state: PlayerState
    player_input: str


class PostActionContext(BaseModel):
    """Contexto de salida después de ejecutar las acciones en el juego."""
    player_state: PlayerState
    clas_action: Actions


class NarrativeContext(BaseModel):
    """Contexto completo estructurado para el generador de narrativa (DungeonMaster/Narrador)."""
    previous_player_state: PlayerState
    current_player_state: PlayerState
    
    previous_place: Optional[Place] = None
    current_place: Optional[Place] = None
    
    npcs_context: Dict[str, NPC] = Field(default_factory=dict)
    player_input: str
    executed_actions: Actions


class NarrationResponse(BaseModel):
    """Respuesta narrativa estructurada del Dungeon Master."""
    narration: str


class DialogueResponse(BaseModel):
    """Respuesta estructurada del NPC para interacciones de diálogo."""
    narration: str
    dialogue_state: str  # "TALK" o "NORMAL"
