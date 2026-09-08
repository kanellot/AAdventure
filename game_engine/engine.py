import os
from typing import Optional, List, Union
from pydantic import BaseModel, Field
from game_engine.state import WorldState, GameStateController
from domains import NPC, ResultType, Place, ActionCommand
from transformer_engine import DungeonMaster
from adventure_packager import AdventurePackager
from game_engine.actions import (
    Behaviour, MoveNarratorAction, ExplainLookNarratorAction, DialogueNarratorAction
)

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

    def get_npc_place(self, npc_id_or_name: str) -> Optional[Place]:
        """Devuelve el objeto Place donde reside el NPC buscando en visible_entities."""
        npc = self.get_npc_by_name_or_id(npc_id_or_name)
        if not npc:
            return None
        for place in self.world_state.places_by_id.values():
            if npc.id in place.visible_entities or npc.name in place.visible_entities:
                return place
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

    def get_all_target_names(self) -> List[str]:
        """Devuelve una lista ordenada con los nombres de todos los lugares y NPCs del mundo."""
        place_names = sorted(list(self.world_state.places_by_name.keys()))
        npc_names = sorted(list(self.world_state.npcs_by_name.keys()))
        return place_names + npc_names

    def get_world_entities_hierarchy(self) -> List[dict]:
        """
        Devuelve una estructura jerárquica de las localizaciones, sus lugares (solo nombre)
        y todos los NPCs presentes en cada localización (solo nombre).
        """
        hierarchy = []
        if not self.world_state or not self.world_state.world:
            return hierarchy

        all_npcs_accounted = set()

        for loc in self.world_state.world.locations:
            places_list = []
            npcs_in_loc = []
            seen_loc_npcs = set()

            for place in loc.places:
                places_list.append(place.name)
                for ent_id in place.visible_entities:
                    npc = self.get_npc_by_name_or_id(ent_id)
                    if npc and npc.name not in seen_loc_npcs:
                        npcs_in_loc.append(npc.name)
                        seen_loc_npcs.add(npc.name)
                        all_npcs_accounted.add(npc.id)
                        all_npcs_accounted.add(npc.name)

            hierarchy.append({
                "location_name": loc.name,
                "places": sorted(places_list),
                "npcs": sorted(npcs_in_loc)
            })

        # Comprobar si hay NPCs no asignados directamente a lugares conocidos
        remaining_npcs = []
        for npc_id, npc in self.world_state.npcs.items():
            if npc_id not in all_npcs_accounted and npc.name not in all_npcs_accounted:
                remaining_npcs.append(npc.name)
                all_npcs_accounted.add(npc_id)
                all_npcs_accounted.add(npc.name)

        if remaining_npcs:
            hierarchy.append({
                "location_name": "Otras Entidades",
                "places": [],
                "npcs": sorted(remaining_npcs)
            })

        return hierarchy


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

    def execute_turn(
        self, 
        action: Union[ActionCommand, str], 
        target: Optional[str] = None, 
        player_input: str = "", 
        dm: Optional[DungeonMaster] = None
    ) -> TurnOutput:
        """
        Ejecuta un turno directo de 1 solo paso según la acción solicitada (MOVE, LOOK, TALK).
        """
        self.turn_debug_steps.clear()

        # Permitir compatibilidad si dm fue pasado posicionalmente en target o player_input
        if target is not None and not isinstance(target, str):
            if dm is None and hasattr(target, "execute"):
                dm = target
                target = None
        if player_input is not None and not isinstance(player_input, str):
            if dm is None and hasattr(player_input, "execute"):
                dm = player_input
                player_input = ""

        # Parsear comando de acción
        if isinstance(action, ActionCommand):
            action_type = action.action.upper()
            target_name = action.target
        elif isinstance(action, str):
            clean_str = action.strip()
            first_word = clean_str.split(maxsplit=1)[0].upper() if clean_str else ""
            if first_word in ["MOVE", "LOOK", "TALK", "EXPLAIN", "EXPLORE"]:
                parts = clean_str.split(maxsplit=1)
                action_type = parts[0].upper()
                target_name = parts[1].strip() if len(parts) > 1 else (target or "")
            else:
                if self.game_state_controller.data.state.player_state.upper() == "TALK":
                    action_type = "TALK"
                    target_name = self.game_state_controller.data.state.player_target or (target or "")
                    if not player_input:
                        player_input = action
                else:
                    action_type = action.upper()
                    target_name = target or ""
        else:
            raise ValueError(f"Acción inválida: {action}")

        step = None
        final_author = "Player"

        if action_type in ["MOVE", "EXPLORE"]:
            self.game_state_controller.update_state("EXPLORE")
            self.game_state_controller.data.state.player_target = ""
            step = MoveNarratorAction(target_name)
            final_author = "Dungeon Master"

        elif action_type in ["LOOK", "EXPLAIN"]:
            self.game_state_controller.update_state("EXPLORE")
            step = ExplainLookNarratorAction(target_name)
            final_author = "Dungeon Master"

        elif action_type == "TALK":
            npc = self.get_npc_by_name_or_id(target_name)
            if npc:
                # Si el usuario hace talk con un NPC pero no se encuentra en el mismo place,
                # se actualiza automáticamente el lugar del jugador al lugar donde reside el NPC.
                npc_place = self.get_npc_place(npc.id)
                if npc_place and (not self.game_state_controller.data.place or self.game_state_controller.data.place.id != npc_place.id):
                    self.game_state_controller.update_location(npc_place.name)

                self.game_state_controller.load_npc(npc.id)
                self.game_state_controller.update_state("TALK")
                self.game_state_controller.data.state.player_target = npc.name
                final_author = npc.name
            else:
                final_author = target_name

            step = DialogueNarratorAction(target_name)
        else:
            return self._create_debug_turn_output(author="SYSTEM", msg=f"Acción desconocida: '{action_type}'")

        res = self._run_step(step, player_input, dm)
        if not res.success:
            return self._create_debug_turn_output(author="SYSTEM", msg=res.message)

        return self._create_debug_turn_output(msg=res.message, author=final_author)

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
            "game_state": state.player_state.upper() if state else "EXPLORE"
        }


