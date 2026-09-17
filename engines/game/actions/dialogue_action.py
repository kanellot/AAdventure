"""Acción de narración y gestión de diálogos e interacción con NPCs."""

from typing import Any, Dict, List, Optional, Tuple, Type
from pydantic import BaseModel, Field, field_validator
from domains import ContextType, ConversationRecord, ResponseType, ResultType
from domains.npcs import NPCMotivations
from engines.game.actions.base_action import BaseAction
from engines.game.lore_router import LoreRouter
from engines.game.state_controller import GameStateController
from engines.game.utils import MarkdownFormatter, TimeCalculator


class DialogueNPCInfo(BaseModel):
    """Información simplificada y enfocada del NPC para la acción de diálogo."""

    name: str
    occupation: str
    description: str
    motivations: NPCMotivations


class DialogueNarratorCtx(ContextType):
    """Contexto estructurado para la acción de diálogo con un NPC."""

    npc: DialogueNPCInfo
    conversation_history: List[Dict[str, str]] = Field(default_factory=list)
    player_input: str
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


class DialogueNarratorResult(ResultType):
    """Resultado de la ejecución del diálogo."""

    pass


class DialogueAction(BaseAction[DialogueNarratorCtx, DialogueNarratorResponse]):
    """Acción de diálogo: narra la réplica del NPC y actualiza afinidad y lore."""

    def __init__(self, target_npc: str):
        self.target_npc = target_npc
        self._triggered_lore = None

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
        """Genera los tags runtime formateados para la plantilla de diálogo."""
        return MarkdownFormatter.dialogue_tags(ctx)

    def to_markdown(self, ctx: DialogueNarratorCtx) -> str:
        """Genera la representación Markdown de respaldo del contexto."""
        return MarkdownFormatter.dialogue_markdown(ctx)

    def build_context(
        self,
        game_state_controller: GameStateController,
        player_input: str,
    ) -> DialogueNarratorCtx:
        """Construye el contexto del diálogo evaluando lore dinámico de NPC."""
        npc = game_state_controller.load_npc(self.target_npc)
        if not npc:
            raise ValueError(f"NPC '{self.target_npc}' no encontrado.")

        if not npc.conversation:
            npc.conversation = ConversationRecord(id=f"c_{npc.id}", msg=[])

        occupation = npc.occupation or npc.name

        npc_info = DialogueNPCInfo(
            name=npc.name,
            occupation=occupation,
            description=npc.description,
            motivations=npc.motivations,
        )

        router = LoreRouter.get_instance()
        self._triggered_lore = None
        directive = None

        reactive_match = router.find_reactive_lore(player_input, npc, game_state_controller, npc=npc)
        if reactive_match:
            self._triggered_lore, _ = reactive_match
            if router.last_evaluation and router.last_evaluation.injected_directive:
                directive = router.last_evaluation.injected_directive
            else:
                directive = self._triggered_lore.get_directive_for_entity(npc.id) if hasattr(self._triggered_lore, "get_directive_for_entity") else self._triggered_lore.directive
        else:
            proactive_block = router.find_proactive_lore(npc, game_state_controller, npc=npc)
            if proactive_block:
                self._triggered_lore = proactive_block
                directive = self._triggered_lore.get_directive_for_entity(npc.id) if hasattr(self._triggered_lore, "get_directive_for_entity") else self._triggered_lore.directive

        return DialogueNarratorCtx(
            npc=npc_info,
            conversation_history=npc.conversation.msg,
            player_input=player_input,
            directive=directive,
        )

    def validate(
        self,
        game_state_controller: GameStateController,
        player_input: str,
        llm_response: Optional[DialogueNarratorResponse] = None,
    ) -> Tuple[bool, Optional[str], Optional[dict]]:
        if llm_response is None:
            return True, None, None

        if not (0.0 <= llm_response.affinity <= 1.0):
            return False, f"Puntuación de afinidad '{llm_response.affinity}' fuera del rango [0.0, 1.0].", None

        metadata = {
            "affinity_eval": llm_response.affinity,
            "msg": llm_response.msg,
        }
        return True, "Diálogo narrado correctamente.", metadata

    def mutate(
        self,
        game_state_controller: GameStateController,
        player_input: str,
        llm_response: DialogueNarratorResponse,
        is_valid: bool,
        metadata: Optional[dict],
    ) -> None:
        if not is_valid:
            return

        npc = game_state_controller.load_npc(self.target_npc)

        if npc:
            if not npc.conversation:
                npc.conversation = ConversationRecord(id=f"c_{npc.id}", msg=[])
            npc.conversation.msg.append({"Player": player_input})
            npc.conversation.msg.append({"Npc": llm_response.msg})

            delta = (llm_response.affinity - 0.5) * 0.35
            npc.affinity = round(max(0.0, min(1.0, npc.affinity + delta)), 4)
            game_state_controller.game_state.active_npc_affinity = npc.affinity

            if self._triggered_lore:
                router = LoreRouter.get_instance()
                router.apply_effects(self._triggered_lore, game_state_controller, npc=npc)

        TimeCalculator.add_dialogue_time(game_state_controller)

    def build_result(
        self,
        game_state_controller: GameStateController,
        player_input: str,
        llm_response: DialogueNarratorResponse,
        is_valid: bool,
        reason: Optional[str],
        metadata: Optional[dict],
    ) -> DialogueNarratorResult:
        msg = llm_response.msg if is_valid else (reason or "")
        return DialogueNarratorResult(
            success=is_valid,
            message=msg,
            data=metadata,
        )
