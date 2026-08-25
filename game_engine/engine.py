from typing import Optional, List
from pydantic import BaseModel, Field
from game_engine.state import WorldState, GameStateController
from domains import NPC, ResultType
from transformer_engine import DungeonMaster
from game_engine.actions import Behaviour, ExplorationClassifierAction, MoveNarratorAction, ExplainLookNarratorAction, DialogueClassificatorAction, DialogueNarratorAction

class TurnOutput(BaseModel):
    """Representa la respuesta unificada de un turno de juego para la interfaz."""
    msg: str
    author: str
    info_msg: Optional[str] = None


class GameEngine:
    """Clase orquestadora principal (Fachada) que coordina las reglas, mutaciones y contextos del juego."""

    def __init__(self, world_json_path: str, npcs_json_path: str, player_json_path: str):
        # 1. Cargar el estado inicial del mundo
        self.world_state = WorldState(world_json_path, npcs_json_path, player_json_path)
        
        # 2. Inicializar la proyección del GameState
        self.game_state_controller = GameStateController.create_from_world(self.world_state)

    def get_npc_by_name_or_id(self, target: str) -> Optional[NPC]:
        """Busca un NPC por su ID o su nombre en el estado del mundo."""
        if target in self.world_state.npcs:
            return self.world_state.npcs[target]
        elif target in self.world_state.npcs_by_name:
            return self.world_state.npcs_by_name[target]
        return None

    def change_npc_affinity(self, npc_name_or_id: str, delta: float):
        """Modifica externamente la afinidad de un NPC."""
        npc = self.get_npc_by_name_or_id(npc_name_or_id)
        if npc:
            npc.affinity = round(max(0.0, min(1.0, npc.affinity + delta)), 4)
        for n in self.game_state_controller.data.npcs.values():
            if n.id == npc_name_or_id or n.name == npc_name_or_id:
                n.affinity = round(max(0.0, min(1.0, n.affinity + delta)), 4)

    def get_player_name(self) -> str:
        """Devuelve el nombre del jugador cargado en el estado."""
        if self.game_state_controller.data.player:
            return self.game_state_controller.data.player.name
        return "Jugador"

    def save(self):
        """Sincroniza y persiste los cambios del controlador de vuelta al WorldState."""
        self.game_state_controller.save()

    # =====================================================================
    # ORQUESTACIÓN DE TURNOS POR COMPORTAMIENTO (BEHAVIOUR)
    # =====================================================================

    def execute_turn(self, player_input: str, dm: DungeonMaster) -> TurnOutput:
        """Ejecuta un turno completo de juego, procesando la lógica de estado y seleccionando acciones."""
        # 1. Determinar el estado antes de procesar el turno
        was_talking = self.game_state_controller.data.state.player_state.upper() == "TALK"
        target_npc_before = self.game_state_controller.data.state.player_target

        current_state = self.game_state_controller.data.state.player_state.upper()

        final_msg = ""
        final_author = "Dungeon Master"

        # 2. Seleccionar y ejecutar los pasos del turno
        if current_state == "TALK":
            # Si el jugador está conversando con un NPC, el primer paso es clasificar el input
            step_1 = DialogueClassificatorAction(target_npc_before)
            res_1 = self._run_step(step_1, player_input, dm)
            if not res_1.success:
                return TurnOutput(author="SYSTEM", msg=res_1.message)

            status = "TALK"
            if hasattr(res_1, "status"):
                status = res_1.status
            elif res_1.data and "status" in res_1.data:
                status = res_1.data["status"]

            # Con el estado clasificado (TALK o END_TALK), ejecutamos el narrador de diálogo
            step_2 = DialogueNarratorAction(target_npc_before, status=status)
            res_2 = self._run_step(step_2, player_input, dm)
            if not res_2.success:
                return TurnOutput(author="SYSTEM", msg=res_2.message)

            # Buscar el nombre real del NPC para usarlo como autor
            npc = self.get_npc_by_name_or_id(target_npc_before)
            final_author = npc.name if npc else target_npc_before
            final_msg = res_2.message
        else:
            # En exploración normal, el primer paso es clasificar el input del jugador
            step_1 = ExplorationClassifierAction()
            res_1 = self._run_step(step_1, player_input, dm)
            
            # Si el paso 1 falló (ej. movimiento no permitido, npc no existe)
            if not res_1.success:
                if res_1.data and "reason" in res_1.data:
                    # ejecutamos el narrador para describir orgánicamente el fallo al jugador
                    step_2 = ExplainLookNarratorAction(target=res_1.data.get("target"), failed_reason=res_1.data["reason"])
                    res_2 = self._run_step(step_2, player_input, dm)
                    if not res_2.success:
                        return TurnOutput(author="SYSTEM", msg=res_2.message)
                    final_author = "Dungeon Master"
                    final_msg = res_2.message
                else:
                    return TurnOutput(author="SYSTEM", msg=res_1.message)
            else:
                # Si el clasificador tuvo éxito, ejecutamos la acción correspondiente
                if res_1.data and "action" in res_1.data:
                    action = res_1.data["action"]
                    target = res_1.data.get("target")

                    step_2 = None
                    if action == "MOVE":
                        step_2 = MoveNarratorAction(target)
                        final_author = "Dungeon Master"
                    elif action == "TALK":
                        step_2 = DialogueNarratorAction(target, status="TALK")
                        npc = self.get_npc_by_name_or_id(target)
                        final_author = npc.name if npc else target
                    elif action in ["LOOK", "EXPLAIN"]:
                        step_2 = ExplainLookNarratorAction(target)
                        final_author = "Dungeon Master"

                    if step_2:
                        res_2 = self._run_step(step_2, player_input, dm)
                        if not res_2.success:
                            return TurnOutput(author="SYSTEM", msg=res_2.message)
                        final_msg = res_2.message
                    else:
                        # Si no hay step_2 pero fue exitoso
                        final_msg = res_1.message
                else:
                    final_msg = res_1.message

        # 3. Determinar si la conversación finalizó durante este turno para agregar info_msg
        info_msg = None
        is_talking_now = self.game_state_controller.data.state.player_state.upper() == "TALK"
        if was_talking and not is_talking_now:
            info_msg = f"[INFO] Conversación finalizada con {target_npc_before}. Volviendo a exploración."

        return TurnOutput(msg=final_msg, author=final_author, info_msg=info_msg)

    def _run_step(self, step: Behaviour, player_input: str, dm: DungeonMaster) -> ResultType:
        """Ejecuta las fases del Step: generar contexto -> llamar LLM -> validar -> execute."""
        # 1. Generar contexto estructurado (MarkdownContext/ContextType)
        ctx = step.generar_ctx(self.game_state_controller, player_input)

        # 2. Obtener respuesta estructurada del LLM usando DungeonMaster
        llm_raw = dm.execute(
            rules_path=step.rules_path,
            gamecontext=ctx,
            player_input=player_input,
            response_model=step.response_model,
            profile_name=step.profile_name
        )
        llm_response = step.response_model.model_validate(llm_raw)

        # 3. Ejecutar lógica, validaciones y mutación del estado
        result = step.execute(self.game_state_controller, player_input, llm_response)

        # Persistir cambios del GameState al WorldState y guardar archivos
        self.save()

        # Re-inicializar el controlador si volvimos/estamos en exploración normal para mantener consistencia
        if self.game_state_controller.data.state.player_state.upper() != "TALK":
            current_target = self.game_state_controller.data.state.player_target
            current_prev_place = self.game_state_controller.data.state.prev_place
            self.game_state_controller = GameStateController.create_from_world(
                self.world_state, 
                target=current_target,
                prev_place=current_prev_place
            )

        return result

