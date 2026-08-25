from typing import Type, Optional, Tuple, List
from pydantic import BaseModel, Field
from domains import ContextType, ResponseType, ResultType
from game_engine.actions.behaviour import Behaviour
from game_engine.state import GameStateController

### DATA CLASSES ###

class DialogueServiceInfo(BaseModel):
    """Representa la información simplificada de un servicio ofrecido por el NPC."""
    id: str
    nombre: str
    descripcion: str

class DialogueClassificatorCtx(ContextType):
    """Contexto para el clasificador de diálogo."""
    services: List[DialogueServiceInfo] = Field(default_factory=list)
    player_input: str

    def to_markdown(self) -> str:
        md = "## SERVICIOS DISPONIBLES DEL NPC\n"
        if self.services:
            for s in self.services:
                md += f"- `{s.id}` (Nombre: {s.nombre}): {s.descripcion}\n"
        else:
            md += "- (Ninguno)\n"
        md += f"\n* **player_input**: \"{self.player_input}\""
        return md

class DialogueClassificatorResponse(ResponseType):
    """Respuesta estructurada del LLM para la clasificación de diálogo."""
    status: str  # TALK o END_TALK
    service: Optional[str] = None

class DialogueClassificatorResult(ResultType):
    """Resultado del Game Engine para la clasificación de diálogo."""
    status: str
    service: Optional[str] = None

### ACTION CLASS ###

class DialogueClassificatorAction(Behaviour[DialogueClassificatorCtx, DialogueClassificatorResponse]):
    """Paso del turno en estado de conversación: clasifica si se continúa, finaliza o solicita un servicio."""

    STATUSES = ["TALK", "END_TALK"]

    def __init__(self, target_npc: str):
        self.target_npc = target_npc

    @property
    def rules_path(self) -> str:
        return r"Resources/system_data/rules/DialogueClassificator.md"

    @property
    def response_model(self) -> Type[DialogueClassificatorResponse]:
        return DialogueClassificatorResponse

    @property
    def profile_name(self) -> str:
        return "dialogue_classificator"

    def generar_ctx(
        self, 
        game_state_controller: GameStateController, 
        player_input: str
    ) -> DialogueClassificatorCtx:
        npc = None
        for n in game_state_controller.data.npcs.values():
            if n.id == self.target_npc or n.name == self.target_npc:
                npc = n
                break
        if not npc:
            npc = game_state_controller.load_npc(self.target_npc)

        services = []
        if npc and npc.services:
            for s in npc.services:
                # Mapear el ID de servicio y su descripción a la estructura simplificada
                services.append(DialogueServiceInfo(id=s.id, nombre=s.id, descripcion=s.description))

        return DialogueClassificatorCtx(
            services=services,
            player_input=player_input
        )

    def validate(
        self, 
        game_state_controller: GameStateController, 
        player_input: str,
        llm_response: Optional[DialogueClassificatorResponse] = None
    ) -> Tuple[bool, Optional[str], Optional[dict]]:
        if llm_response is None:
            return True, None, None

        status = llm_response.status.upper() if llm_response.status else None
        service = llm_response.service if llm_response.service else None

        metadata = {
            "status": status,
            "service": service,
            "action": "dialogue_classification"  # Añadido para que main.py lo filtre al imprimir en consola
        }

        if not status:
            return False, "No se especificó ningún status.", metadata
        if status not in self.STATUSES:
            return False, f"Status de diálogo '{status}' desconocido.", metadata

        # Si se solicita un servicio, comprobar que el NPC realmente lo tenga
        if service:
            npc = None
            for n in game_state_controller.data.npcs.values():
                if n.id == self.target_npc or n.name == self.target_npc:
                    npc = n
                    break
            if not npc:
                npc = game_state_controller.load_npc(self.target_npc)

            if not npc or not any(s.id == service for s in npc.services):
                return False, f"El servicio '{service}' no es ofrecido por este NPC.", metadata

        return True, "Diálogo clasificado correctamente.", metadata

    def mutate(
        self, 
        game_state_controller: GameStateController, 
        player_input: str, 
        llm_response: DialogueClassificatorResponse, 
        is_valid: bool, 
        metadata: Optional[dict]
    ) -> None:
        # Por ahora los servicios sólo se clasifican y no mutan el estado global aquí.
        # Tampoco mutamos player_state aquí porque lo mutará la acción de narración subsiguiente.
        pass

    def build_result(
        self,
        game_state_controller: GameStateController,
        player_input: str,
        llm_response: DialogueClassificatorResponse,
        is_valid: bool,
        reason: Optional[str],
        metadata: Optional[dict]
    ) -> DialogueClassificatorResult:
        status = metadata.get("status") if metadata else "TALK"
        service = metadata.get("service") if metadata else None
        
        # Asegurar que metadata tiene la clave action para ser filtrada por la consola de main.py
        if metadata is None:
            metadata = {}
        metadata["action"] = "dialogue_classification"

        return DialogueClassificatorResult(
            success=is_valid,
            message=reason or "Clasificación de diálogo exitosa.",
            status=status,
            service=service,
            data=metadata
        )
