"""Acción narrativa de diálogo e interacción con NPCs."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, Type

from pydantic import BaseModel, Field, field_validator

from domains import ContextType, ResponseType
from domains.npcs import NPCMotivations
from engines.game.actions.base_action import BaseAction
from engines.game.state_controller import GameStateController
from engines.game.utils import MarkdownFormatter


class DialogueNPCInfo(BaseModel):
    """Información simplificada del NPC para el prompt de diálogo."""

    name: str
    occupation: str
    description: str
    motivations: NPCMotivations = Field(default_factory=NPCMotivations)


class DialogueNarratorCtx(ContextType):
    """Contexto estructurado para la acción de diálogo con un NPC."""

    npc: DialogueNPCInfo
    conversation_history: List[Dict[str, str]] = Field(default_factory=list)
    player_input: str = ""
    directive: Optional[str] = None


class DialogueNarratorResponse(ResponseType):
    """Respuesta estructurada del LLM para el diálogo."""

    msg: str = Field(description="Siguiente respuesta del NPC en la conversación (1 a 3 frases).")
    affinity: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Puntuación de afinidad de 0.0 a 1.0 evaluando el mensaje del jugador.",
    )

    @field_validator("affinity", mode="before")
    @classmethod
    def parse_affinity(cls, v: Any) -> float:
        if isinstance(v, (int, float)):
            return max(0.0, min(1.0, float(v)))
        if isinstance(v, str):
            try:
                return max(0.0, min(1.0, float(v.strip())))
            except ValueError:
                mapping = {"VERY_GOOD": 1.0, "GOOD": 0.8, "NORMAL": 0.5, "BAD": 0.2}
                return mapping.get(v.strip().upper(), 0.5)
        return 0.5


class DialogueAction(BaseAction[DialogueNarratorCtx, DialogueNarratorResponse]):
    """Acción de diálogo: construye contexto de conversación y genera réplica del NPC."""

    def __init__(self, target_npc: str, directive: Optional[str] = None):
        self.target_npc = target_npc
        self.directive = directive

    @property
    def rules_path(self) -> str:
        return r"Resources/system_data/rules/dialogue.md"

    @property
    def response_model(self) -> Type[DialogueNarratorResponse]:
        return DialogueNarratorResponse

    @property
    def profile_name(self) -> str:
        return "dialogue_narrator"

    def get_template_tags(self, ctx: DialogueNarratorCtx) -> Dict[str, str]:
        return MarkdownFormatter.dialogue_tags(ctx)

    def to_markdown(self, ctx: DialogueNarratorCtx) -> str:
        return MarkdownFormatter.dialogue_markdown(ctx)

    def build_context(
            self,
            controller: GameStateController,
            player_input: str = "",
    ) -> DialogueNarratorCtx:
        npc = controller.npcs_by_id.get(self.target_npc)
        if not npc:
            npc_info = DialogueNPCInfo(
                name=self.target_npc,
                occupation="Desconocido",
                description="Un personaje en este lugar.",
            )
        else:
            npc_info = DialogueNPCInfo(
                name=npc.name,
                occupation=getattr(npc, "occupation", "") or npc.name,
                description=npc.description,
                motivations=getattr(npc, "motivations", None) or NPCMotivations(),
            )

        history = controller.get_conversation(self.target_npc)
        return DialogueNarratorCtx(
            npc=npc_info,
            conversation_history=history,
            player_input=player_input,
            directive=self.directive,
        )

    def fallback_narrative(self, controller: GameStateController, ctx: DialogueNarratorCtx) -> Tuple[str, Any]:
        if not ctx.player_input:
            return "¡Saludos, viajero! ¿En qué puedo ayudarte?", None
        return "He escuchado lo que dices. Déjame pensar en ello.", None
