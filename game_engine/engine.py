import os
from typing import Optional, List
from pydantic import BaseModel, Field
from game_engine.state import WorldState, GameStateController
from domains import NPC, ResultType
from transformer_engine import DungeonMaster
from game_engine.actions import Behaviour, ExplorationClassifierAction, MoveNarratorAction, ExplainLookNarratorAction, DialogueClassificatorAction, DialogueNarratorAction
from adventure_packager import AdventurePackager

class TurnOutput(BaseModel):
    """Representa la respuesta unificada de un turno de juego para la interfaz."""
    msg: str
    author: str
    info_msg: Optional[str] = None
    debug_prompt: Optional[str] = None
    debug_raw_response: Optional[str] = None
    debug_structured_response: Optional[str] = None
    debug_engine_result: Optional[str] = None


class GameEngine:
    """Clase orquestadora principal (Fachada) que coordina las reglas, mutaciones y contextos del juego."""

    def __init__(self, world_json_path: str, npcs_json_path: Optional[str] = None, player_json_path: Optional[str] = None):
        self.temp_dir = None
        self.turn_debug_steps = []
        
        # Si es un archivo de aventura .aad, lo desempaquetamos
        if world_json_path.lower().endswith(".aad"):
            self.temp_dir = AdventurePackager.unpack_to_temp(world_json_path)
            world_path = os.path.join(self.temp_dir, "world.json")
            npcs_path = os.path.join(self.temp_dir, "npcs.json")
            player_path = os.path.join(self.temp_dir, "player.json")
        else:
            world_path = world_json_path
            npcs_path = npcs_json_path
            player_path = player_json_path

        # 1. Cargar el estado inicial del mundo
        self.world_state = WorldState(world_path, npcs_path, player_path)
        
        # 2. Inicializar la proyección del GameState
        self.game_state_controller = GameStateController.create_from_world(self.world_state)

    def __del__(self):
        self.cleanup()

    def cleanup(self):
        """Limpia el directorio temporal si se creó uno."""
        if hasattr(self, "temp_dir") and self.temp_dir and os.path.exists(self.temp_dir):
            try:
                import shutil
                shutil.rmtree(self.temp_dir)
            except Exception:
                pass
            self.temp_dir = None

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

    def get_formatted_time(self) -> str:
        """Devuelve el tiempo transcurrido formateado en 'Día X, HH:MM'."""
        elapsed = self.game_state_controller.data.state.elapsed_time
        days = elapsed // 1440
        hours = (elapsed // 60) % 24
        minutes = elapsed % 60
        return f"Día {days}, {hours:02d}:{minutes:02d}"


    def save(self):
        """Sincroniza y persiste los cambios del controlador de vuelta al WorldState."""
        self.game_state_controller.save()

    # =====================================================================
    # ORQUESTACIÓN DE TURNOS POR COMPORTAMIENTO (BEHAVIOUR)
    # =====================================================================

    def _create_debug_turn_output(self, msg: str, author: str, info_msg: Optional[str] = None) -> TurnOutput:
        """Helper para empaquetar TurnOutput junto con los registros acumulados de depuración."""
        debug_prompts = []
        debug_raws = []
        debug_structureds = []
        debug_results = []
        
        for idx, debug in enumerate(self.turn_debug_steps, 1):
            header = f"--- PASO {idx}: {debug['step_name']} ---\n"
            debug_prompts.append(header + debug["prompt"])
            debug_raws.append(header + debug["raw_response"])
            debug_structureds.append(header + debug["structured_response"])
            debug_results.append(header + debug["result"])

        return TurnOutput(
            msg=msg,
            author=author,
            info_msg=info_msg,
            debug_prompt="\n\n".join(debug_prompts) if debug_prompts else None,
            debug_raw_response="\n\n".join(debug_raws) if debug_raws else None,
            debug_structured_response="\n\n".join(debug_structureds) if debug_structureds else None,
            debug_engine_result="\n\n".join(debug_results) if debug_results else None
        )

    def execute_turn(self, player_input: str, dm: DungeonMaster) -> TurnOutput:
        """Ejecuta un turno completo de juego, procesando la lógica de estado y seleccionando acciones."""
        self.turn_debug_steps.clear()
        
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
                return self._create_debug_turn_output(author="SYSTEM", msg=res_1.message)

            status = "TALK"
            if hasattr(res_1, "status"):
                status = res_1.status
            elif res_1.data and "status" in res_1.data:
                status = res_1.data["status"]

            # Con el estado clasificado (TALK o END_TALK), ejecutamos el narrador de diálogo
            step_2 = DialogueNarratorAction(target_npc_before, status=status)
            res_2 = self._run_step(step_2, player_input, dm)
            if not res_2.success:
                return self._create_debug_turn_output(author="SYSTEM", msg=res_2.message)

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
                        return self._create_debug_turn_output(author="SYSTEM", msg=res_2.message)
                    final_author = "Dungeon Master"
                    final_msg = res_2.message
                else:
                    return self._create_debug_turn_output(author="SYSTEM", msg=res_1.message)
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
                            return self._create_debug_turn_output(author="SYSTEM", msg=res_2.message)
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

        return self._create_debug_turn_output(msg=final_msg, author=final_author, info_msg=info_msg)

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

        # Capturar información de depuración del paso actual
        debug_info = {
            "step_name": step.__class__.__name__,
            "prompt": ctx.to_markdown() if hasattr(ctx, "to_markdown") else str(ctx),
            "raw_response": str(llm_raw),
            "structured_response": llm_response.model_dump_json(indent=2) if hasattr(llm_response, "model_dump_json") else str(llm_response),
            "result": result.model_dump_json(indent=2) if hasattr(result, "model_dump_json") else str(result)
        }
        self.turn_debug_steps.append(debug_info)

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

    def execute_direct_action(self, action: str, target: str, player_input: str, dm: DungeonMaster) -> TurnOutput:
        """
        Para clics en botones de la UI (omite la clasificación por IA).
        Ejecuta directamente la acción (MOVE, TALK, LOOK, EXPLAIN, END_TALK) sobre el target.
        """
        self.turn_debug_steps.clear()
        action = action.upper()
        was_talking = self.game_state_controller.data.state.player_state.upper() == "TALK"
        target_npc_before = self.game_state_controller.data.state.player_target

        # 1. Mutar estado preliminar si es TALK y no estábamos conversando ya
        if action == "TALK" and not was_talking:
            npc = self.get_npc_by_name_or_id(target)
            if npc:
                self.game_state_controller.load_npc(npc.id)
                self.game_state_controller.update_state("TALK")
                self.game_state_controller.data.state.player_target = npc.name
                
                npc_place = None
                for place in self.world_state.places_by_id.values():
                    if npc.id in place.visible_entities:
                        npc_place = place
                        break
                if npc_place:
                    self.game_state_controller.update_location(npc_place.name)

        # 2. Seleccionar el comportamiento correspondiente
        step_2 = None
        final_author = "Dungeon Master"

        if action == "MOVE":
            step_2 = MoveNarratorAction(target)
            final_author = "Dungeon Master"
        elif action == "TALK":
            step_2 = DialogueNarratorAction(target, status="TALK")
            npc = self.get_npc_by_name_or_id(target)
            final_author = npc.name if npc else target
        elif action == "END_TALK":
            step_2 = DialogueNarratorAction(target, status="END_TALK")
            npc = self.get_npc_by_name_or_id(target)
            final_author = npc.name if npc else target
        elif action in ["LOOK", "EXPLAIN"]:
            step_2 = ExplainLookNarratorAction(target)
            final_author = "Dungeon Master"

        if step_2:
            res_2 = self._run_step(step_2, player_input, dm)
            if not res_2.success:
                return self._create_debug_turn_output(author="SYSTEM", msg=res_2.message)
            final_msg = res_2.message
        else:
            final_msg = f"Acción directa '{action}' no reconocida o no soportada."

        # 3. Determinar si finalizó la conversación
        info_msg = None
        is_talking_now = self.game_state_controller.data.state.player_state.upper() == "TALK"
        if was_talking and not is_talking_now:
            info_msg = f"[INFO] Conversación finalizada con {target_npc_before}. Volviendo a exploración."

        return self._create_debug_turn_output(msg=final_msg, author=final_author, info_msg=info_msg)

    def get_available_actions(self) -> dict:
        """
        Devuelve las acciones e interacciones válidas que la UI puede dibujar como botones.
        """
        current_place = self.game_state_controller.data.place
        moves = []
        if current_place and current_place.connections:
            for direction, conn in current_place.connections.items():
                moves.append({
                    "direction": direction,
                    "target": conn.target,
                    "distance": conn.distance,
                    "terrain": conn.terrain_type
                })

        npcs = []
        for npc_info in self.game_state_controller.get_npc_list():
            npcs.append({
                "id": npc_info["id"],
                "name": npc_info["name"]
            })

        look_targets = [current_place.name] if current_place else []

        return {
            "moves": moves,
            "npcs": npcs,
            "look_targets": look_targets
        }

    def get_ui_state(self) -> dict:
        """
        Devuelve información simplificada para actualizar la barra de estado de la UI.
        """
        state = self.game_state_controller.data.state
        player = self.game_state_controller.data.player
        place = self.game_state_controller.data.place

        return {
            "player_name": player.name if player else "Jugador",
            "gold": player.gold if player else 0,
            "current_location": place.name if place else "Desconocido",
            "formatted_time": self.get_formatted_time(),
            "game_state": state.player_state.upper() if state else "EXPLORATION"
        }


