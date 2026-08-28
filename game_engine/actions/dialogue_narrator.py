from typing import Type, Optional, Tuple, List, Dict
from pydantic import BaseModel, Field
from domains import ContextType, ResponseType, ResultType, ConversationRecord
from domains.npcs import NPCMotivations
from game_engine.actions.behaviour import Behaviour
from game_engine.state import GameStateController

### DATA CLASSES ###

class DialogueNPCInfo(BaseModel):
    """Representación simplificada del NPC con afinidad, motivaciones e historial completo."""
    id: str
    nombre: str
    descripcion: str
    motivations: NPCMotivations
    affinity: float
    conversacion_actual: List[Dict[str, str]] = Field(default_factory=list)

class DialogueNarratorCtx(ContextType):
    """Contexto de entrada para el narrador de diálogo."""
    npc: DialogueNPCInfo
    player_input: str

    def to_markdown(self) -> str:
        n = self.npc
        md = "## NPC CON EL QUE HABLAS\n"
        md += f"* **ID**: {n.id}\n"
        md += f"* **Nombre**: {n.nombre}\n"
        md += f"* **Descripción**: {n.descripcion}\n"
        md += f"* **Afinidad**: {n.affinity:.2f}\n"

        md += "\n### Motivaciones\n"
        md += f"- Likes: {', '.join(n.motivations.likes) if n.motivations.likes else '(Ninguno)'}\n"
        md += f"- Dislikes: {', '.join(n.motivations.dislikes) if n.motivations.dislikes else '(Ninguno)'}\n"

        md += "\n## HISTORIAL DE CONVERSACIÓN\n"
        if n.conversacion_actual:
            for line in n.conversacion_actual:
                sender = list(line.keys())[0]
                text = line[sender]
                md += f"* **{sender}**: {text}\n"
        else:
            md += "* (No hay mensajes previos)\n"

        md += f"\n* **player_input**: \"{self.player_input}\""
        return md

class DialogueNarratorResponse(ResponseType):
    """Respuesta estructurada del LLM para el narrador de diálogo."""
    msg: str
    affinity: str  # VERY_GOOD, GOOD, NORMAL, BAD

class DialogueNarratorResult(ResultType):
    """Resultado del Game Engine para la narración de diálogo."""
    pass

### ACTION CLASS ###

class DialogueNarratorAction(Behaviour[DialogueNarratorCtx, DialogueNarratorResponse]):
    """Paso del turno: Narra e impersona al NPC, calculando y actualizando afinidad y conversación."""

    VALID_AFFINITIES = ["VERY_GOOD", "GOOD", "NORMAL", "BAD"]

    def __init__(self, target_npc: str, status: str = "TALK"):
        self.target_npc = target_npc
        self.status = status  # TALK o END_TALK

    @property
    def rules_path(self) -> str:
        return r"Resources/system_data/rules/DialogueNarrator.md"

    @property
    def response_model(self) -> Type[DialogueNarratorResponse]:
        return DialogueNarratorResponse

    @property
    def profile_name(self) -> str:
        return "dialogue_narrator"

    def generar_ctx(
        self, 
        game_state_controller: GameStateController, 
        player_input: str
    ) -> DialogueNarratorCtx:
        npc = None
        for n in game_state_controller.data.npcs.values():
            if n.id == self.target_npc or n.name == self.target_npc:
                npc = n
                break
        if not npc:
            npc = game_state_controller.load_npc(self.target_npc)

        if not npc.conversation:
            npc.conversation = ConversationRecord(id=f"c_{npc.id}", msg=[])

        npc_info = DialogueNPCInfo(
            id=npc.id,
            nombre=npc.name,
            descripcion=npc.description,
            motivations=npc.motivations,
            affinity=npc.affinity,
            conversacion_actual=npc.conversation.msg
        )

        return DialogueNarratorCtx(
            npc=npc_info,
            player_input=player_input
        )

    def validate(
        self, 
        game_state_controller: GameStateController, 
        player_input: str,
        llm_response: Optional[DialogueNarratorResponse] = None
    ) -> Tuple[bool, Optional[str], Optional[dict]]:
        if llm_response is None:
            return True, None, None

        affinity_eval = llm_response.affinity.upper() if llm_response.affinity else "NORMAL"
        msg = llm_response.msg

        metadata = {
            "affinity_eval": affinity_eval,
            "msg": msg
        }

        if affinity_eval not in self.VALID_AFFINITIES:
            return False, f"Puntuación de afinidad '{affinity_eval}' no válida.", metadata

        return True, "Diálogo narrado correctamente.", metadata

    def mutate(
        self, 
        game_state_controller: GameStateController, 
        player_input: str, 
        llm_response: DialogueNarratorResponse, 
        is_valid: bool, 
        metadata: Optional[dict]
    ) -> None:
        if not is_valid:
            return

        npc = None
        for n in game_state_controller.data.npcs.values():
            if n.id == self.target_npc or n.name == self.target_npc:
                npc = n
                break
        if not npc:
            npc = game_state_controller.load_npc(self.target_npc)

        if npc:
            # 1. Se añade ultima interaccion a npc.conversacion dentro de gamestate
            if not npc.conversation:
                npc.conversation = ConversationRecord(id=f"c_{npc.id}", msg=[])
            npc.conversation.msg.append({"Player": player_input})
            npc.conversation.msg.append({"Npc": llm_response.msg})

            # 2. Se actualiza el valor de affinity del npc: VERY_GOOD + 0.2, GOOD + 0.1, NORMAL + 0, BAD - 0.1
            affinity_eval = llm_response.affinity.upper()
            delta = 0.0
            if affinity_eval == "VERY_GOOD":
                delta = 0.2
            elif affinity_eval == "GOOD":
                delta = 0.1
            elif affinity_eval == "NORMAL":
                delta = 0.0
            elif affinity_eval == "BAD":
                delta = -0.1

            # Mantener afinidad entre 0.0 y 1.0
            npc.affinity = round(max(0.0, min(1.0, npc.affinity + delta)), 4)

        # 3. Si el estado es END_TALK se cambia el status del juego a EXPLORATION
        if self.status == "END_TALK":
            game_state_controller.update_state("EXPLORATION")
            game_state_controller.data.state.player_target = ""

    def build_result(
        self,
        game_state_controller: GameStateController,
        player_input: str,
        llm_response: DialogueNarratorResponse,
        is_valid: bool,
        reason: Optional[str],
        metadata: Optional[dict]
    ) -> DialogueNarratorResult:
        msg = llm_response.msg if is_valid else (reason or "")
        return DialogueNarratorResult(
            success=is_valid,
            message=msg,
            data=metadata
        )
