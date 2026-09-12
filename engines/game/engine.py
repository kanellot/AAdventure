"""Motor principal de juego (Fachada) que coordina acciones, estado y reglas."""

import os
import shutil
from typing import List, Optional, Union
from pydantic import BaseModel
from adventure_packager import AdventurePackager
from domains import (
    ActionCommand,
    AvailableActionsProjection,
    ConnectionProjection,
    GameStateProjection,
    LocationHierarchyProjection,
    MoveOptionProjection,
    NPC,
    Place,
    PlaceDetailProjection,
    PlaceProjection,
    PlayerSummaryProjection,
    ResultType,
    TurnResultProjection,
    UIStateProjection,
    WorldHierarchyProjection,
)
from engines.game.actions import BaseAction, DialogueAction, LookAction, MoveAction
from engines.game.lore_router import LoreRouter
from engines.game.state_controller import GameStateController, WorldState
from engines.game.utils import TimeCalculator
from engines.transformer import TransformerEngine

# TurnOutput es canónicamente TurnResultProjection (mantiene compatibilidad 100%)
TurnOutput = TurnResultProjection


class GameEngine:
    """Coordinador y fachada principal del motor de juego."""

    def __init__(
        self,
        world_json_path: str,
        npcs_json_path: Optional[str] = None,
        player_json_path: Optional[str] = None,
    ):
        self.temp_dir: Optional[str] = None
        self.turn_debug_steps: List[dict] = []

        if world_json_path.lower().endswith(".aad"):
            self.temp_dir = AdventurePackager.unpack_to_temp(world_json_path)
            world_path = os.path.join(self.temp_dir, "world.json")
            npcs_path = os.path.join(self.temp_dir, "npcs.json")
            player_path = os.path.join(self.temp_dir, "player.json")
        else:
            world_path = world_json_path
            npcs_path = npcs_json_path
            player_path = player_json_path

        self.world_state = WorldState(world_path, npcs_path, player_path)
        self.game_state_controller = GameStateController.create_from_world(self.world_state)
        self.fog_war = self.game_state_controller.fog_war

    def __del__(self) -> None:
        self.cleanup()

    def cleanup(self) -> None:
        """Limpia el directorio temporal si se extrajo un paquete .aad."""
        if hasattr(self, "temp_dir") and self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
            except Exception:
                pass
            self.temp_dir = None

    def get_npc_by_name_or_id(self, target: str) -> Optional[NPC]:
        """Busca un NPC por su ID o su nombre en el estado del mundo."""
        if target in self.world_state.npcs:
            return self.world_state.npcs[target]
        if target in self.world_state.npcs_by_name:
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

    def change_npc_affinity(self, npc_name_or_id: str, delta: float) -> None:
        """Modifica la afinidad de un NPC."""
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
        return TimeCalculator.format_elapsed_time(self.game_state_controller.data.state.elapsed_time)

    def get_all_target_names(self) -> List[str]:
        """Devuelve una lista ordenada con los nombres de todos los lugares y NPCs."""
        place_names = sorted(list(self.world_state.places_by_name.keys()))
        npc_names = sorted(list(self.world_state.npcs_by_name.keys()))
        return place_names + npc_names

    def get_discovered_target_names(self) -> List[str]:
        """Devuelve una lista ordenada con los nombres de lugares y NPCs descubiertos (según la niebla de guerra)."""
        if hasattr(self, "fog_war") and self.fog_war:
            places = self.fog_war.get_all_discovered_places()
            npcs = self.fog_war.get_visible_npcs()
            return sorted(places + npcs)
        return self.get_all_target_names()

    def get_world_entities_hierarchy(self, use_fog_of_war: bool = True) -> List[dict]:
        """
        Devuelve una estructura jerárquica de localizaciones, lugares y NPCs.
        Si use_fog_of_war es True, delega en self.fog_war para aplicar la niebla de guerra.
        """
        if use_fog_of_war and hasattr(self, "fog_war") and self.fog_war:
            return self.fog_war.get_entities_hierarchy(self.world_state.world, self.world_state.npcs)

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
                "npcs": sorted(npcs_in_loc),
            })

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
                "npcs": sorted(remaining_npcs),
            })

        return hierarchy

    def save(self) -> None:
        """Sincroniza y persiste los cambios del controlador al WorldState."""
        self.game_state_controller.save()

    def _create_debug_turn_output(
        self,
        msg: str,
        author: str,
        info_msg: Optional[str] = None,
    ) -> TurnResultProjection:
        """Empaqueta TurnResultProjection junto con los registros de depuración y RAG."""
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

        rag_eval = LoreRouter.get_instance().get_last_evaluation()

        return TurnResultProjection(
            msg=msg,
            author=author,
            info_msg=info_msg,
            debug_prompt="\n\n".join(debug_prompts) if debug_prompts else None,
            debug_raw_response="\n\n".join(debug_raws) if debug_raws else None,
            debug_structured_response="\n\n".join(debug_structureds) if debug_structureds else None,
            debug_engine_result="\n\n".join(debug_results) if debug_results else None,
            rag_evaluation=rag_eval,
        )

    def execute_turn(
        self,
        action: Union[ActionCommand, str],
        target: Optional[str] = None,
        player_input: str = "",
        dm: Optional[TransformerEngine] = None,
    ) -> TurnResultProjection:
        """Ejecuta un turno de juego según la acción solicitada (MOVE, LOOK, TALK)."""
        self.turn_debug_steps.clear()
        LoreRouter.get_instance().reset_evaluation(player_input=player_input or "")

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
                curr_state = self.game_state_controller.data.state.player_state.upper()
                if curr_state == "TALK":
                    action_type = "TALK"
                    target_name = self.game_state_controller.data.state.player_target or (target or "")
                    if not player_input:
                        player_input = action
                elif curr_state == "LOOK":
                    action_type = "LOOK"
                    target_name = self.game_state_controller.data.state.player_target or (target or "")
                    if not player_input:
                        player_input = action
                else:
                    action_type = action.upper()
                    target_name = target or ""
        else:
            raise ValueError(f"Acción inválida: {action}")

        if action_type in ["MOVE", "EXPLORE"]:
            self.game_state_controller.update_state("EXPLORE")
            self.game_state_controller.data.state.player_target = ""
            self.game_state_controller.data.state.active_npc_affinity = None
            if hasattr(self.game_state_controller.data.state, "inspection_history"):
                self.game_state_controller.data.state.inspection_history.clear()
            step = MoveAction(target_name)
            final_author = "Dungeon Master"

        elif action_type in ["LOOK", "EXPLAIN"]:
            if self.game_state_controller.data.state.player_target != target_name:
                if hasattr(self.game_state_controller.data.state, "inspection_history"):
                    self.game_state_controller.data.state.inspection_history.clear()
            self.game_state_controller.update_state("LOOK")
            self.game_state_controller.data.state.player_target = target_name
            self.game_state_controller.data.state.active_npc_affinity = None
            step = LookAction(target_name)
            final_author = "Dungeon Master"

        elif action_type == "TALK":
            if hasattr(self.game_state_controller.data.state, "inspection_history"):
                self.game_state_controller.data.state.inspection_history.clear()
            npc = self.get_npc_by_name_or_id(target_name)
            if npc:
                npc_place = self.get_npc_place(npc.id)
                if npc_place and (
                    not self.game_state_controller.data.place
                    or self.game_state_controller.data.place.id != npc_place.id
                ):
                    self.game_state_controller.update_location(npc_place.name)

                loaded_npc = self.game_state_controller.load_npc(npc.id)
                self.game_state_controller.update_state("TALK")
                self.game_state_controller.data.state.player_target = npc.name
                actual_npc = loaded_npc or npc
                self.game_state_controller.data.state.active_npc_affinity = round(actual_npc.affinity, 4)
                final_author = npc.name
            else:
                self.game_state_controller.update_state("TALK")
                self.game_state_controller.data.state.player_target = target_name
                self.game_state_controller.sync_active_npc_affinity()
                final_author = target_name

            step = DialogueAction(target_name)
        else:
            return self._create_debug_turn_output(author="SYSTEM", msg=f"Acción desconocida: '{action_type}'")

        res = self._run_step(step, player_input, dm)
        if not res.success:
            return self._create_debug_turn_output(author="SYSTEM", msg=res.message)

        return self._create_debug_turn_output(msg=res.message, author=final_author)

    def _run_step(self, step: BaseAction, player_input: str, dm: TransformerEngine) -> ResultType:
        """Ejecuta el ciclo de vida del step contra el transformer engine."""
        ctx = step.build_context(self.game_state_controller, player_input)
        prompt = step.build_prompt(ctx, player_input)
        response_schema = step.get_response_schema()
        schema_name = getattr(step.response_model, "__name__", "StructuredResponse")

        llm_raw = dm.execute(
            prompt=prompt,
            response_schema=response_schema,
            response_model=step.response_model,
            profile_name=step.profile_name,
            schema_name=schema_name,
        )
        llm_response = step.response_model.model_validate(llm_raw)
        result = step.execute(self.game_state_controller, player_input, llm_response)

        self.save()

        debug_info = {
            "step_name": step.__class__.__name__,
            "prompt": prompt,
            "raw_response": str(llm_raw),
            "structured_response": (
                llm_response.model_dump_json(indent=2)
                if hasattr(llm_response, "model_dump_json")
                else str(llm_response)
            ),
            "result": (
                result.model_dump_json(indent=2)
                if hasattr(result, "model_dump_json")
                else str(result)
            ),
        }
        self.turn_debug_steps.append(debug_info)

        if self.game_state_controller.data.state.player_state.upper() not in ["TALK", "LOOK"]:
            current_target = self.game_state_controller.data.state.player_target
            current_prev_place = self.game_state_controller.data.state.prev_place
            self.game_state_controller = GameStateController.create_from_world(
                self.world_state,
                target=current_target,
                prev_place=current_prev_place,
            )

        return result

    def _build_world_hierarchy_projection(self, raw_hierarchy: List[dict]) -> WorldHierarchyProjection:
        """Convierte una lista jerárquica cruda a WorldHierarchyProjection."""
        locations_proj = []
        for loc in raw_hierarchy:
            places_proj = []
            visited_list = loc.get("visited_places", [])
            for p in loc.get("places", []):
                if isinstance(p, PlaceProjection):
                    places_proj.append(p)
                elif isinstance(p, dict):
                    places_proj.append(
                        PlaceProjection(
                            id=p.get("id", p.get("name", "")),
                            name=p.get("name", ""),
                            status=p.get("status", "visible"),
                        )
                    )
                else:
                    p_name = str(p)
                    p_status = getattr(p, "status", None)
                    if not p_status:
                        p_status = "visited" if p_name in visited_list else "visible"
                    places_proj.append(
                        PlaceProjection(
                            id=getattr(p, "id", p_name),
                            name=p_name,
                            status=p_status,
                        )
                    )
            locations_proj.append(
                LocationHierarchyProjection(
                    location_name=loc.get("location_name", "Desconocido"),
                    places=places_proj,
                    npcs=loc.get("npcs", []),
                )
            )
        return WorldHierarchyProjection(locations=locations_proj)

    def get_navigation_hierarchy(self) -> WorldHierarchyProjection:
        """Devuelve la jerarquía del mundo filtrada según fog_war (percepción del jugador)."""
        raw_list = self.get_world_entities_hierarchy(use_fog_of_war=True)
        return self._build_world_hierarchy_projection(raw_list)

    def get_entities_hierarchy(self) -> WorldHierarchyProjection:
        """Devuelve la jerarquía completa de todas las entidades del mundo sin niebla (para depuración)."""
        raw_list = self.get_world_entities_hierarchy(use_fog_of_war=False)
        return self._build_world_hierarchy_projection(raw_list)

    def get_game_state_projection(self) -> GameStateProjection:
        """Devuelve una proyección exhaustiva del estado actual para el inspector visual."""
        state = self.game_state_controller.data.state
        player = self.game_state_controller.data.player
        place = self.game_state_controller.data.place

        player_summary = PlayerSummaryProjection(
            id=player.id if player else "player",
            name=player.name if player else "Jugador",
            description=player.description if player else "",
            gold=player.gold if player else 0,
            player_location=player.player_location if player else "",
            state=player.state if player else "EXPLORE",
            active_quest=player.active_quest if player else None,
            completed_quests=list(player.completed_quests) if player else [],
            inventory=list(player.inventory) if player else [],
            visited_places=list(player.visited_places) if player else [],
        )

        place_detail = None
        if place:
            connections_proj = []
            for direction, conn in (place.connections or {}).items():
                connections_proj.append(
                    ConnectionProjection(
                        direction=direction,
                        target=conn.target,
                        distance=conn.distance,
                        terrain_type=getattr(conn, "terrain_type", "normal") or "normal",
                    )
                )
            place_detail = PlaceDetailProjection(
                id=place.id,
                name=place.name,
                description=place.description,
                visible_entities=list(place.visible_entities or []),
                connections=connections_proj,
            )

        discovered = (
            self.fog_war.get_all_discovered_places()
            if hasattr(self, "fog_war") and self.fog_war
            else []
        )
        visible_npcs = (
            self.fog_war.get_visible_npcs()
            if hasattr(self, "fog_war") and self.fog_war
            else []
        )

        active_affinity = None
        if state and state.player_state.upper() == "TALK":
            active_affinity = self.game_state_controller.sync_active_npc_affinity()
            if active_affinity is None:
                active_affinity = getattr(state, "active_npc_affinity", None)

        return GameStateProjection(
            player=player_summary,
            player_state=state.player_state if state else "EXPLORE",
            player_target=state.player_target if state else "",
            active_npc_affinity=active_affinity,
            current_place=place.name if place else None,
            current_place_detail=place_detail,
            prev_place=state.prev_place.name if state and state.prev_place else None,
            travel_speed=state.travel_speed if state else 4.5,
            elapsed_time=state.elapsed_time if state else 0,
            formatted_time=self.get_formatted_time(),
            discovered_places=discovered,
            visible_npcs=visible_npcs,
        )

    def get_ui_state_projection(self) -> UIStateProjection:
        """Devuelve un resumen del estado del juego en formato DTO para la interfaz."""
        state = self.game_state_controller.data.state
        player = self.game_state_controller.data.player
        place = self.game_state_controller.data.place

        active_affinity = None
        if state and state.player_state.upper() == "TALK":
            active_affinity = self.game_state_controller.sync_active_npc_affinity()
            if active_affinity is None:
                active_affinity = getattr(state, "active_npc_affinity", None)

        return UIStateProjection(
            player_name=player.name if player else "Jugador",
            gold=player.gold if player else 0,
            current_location=place.name if place else "Desconocido",
            formatted_time=self.get_formatted_time(),
            game_state=state.player_state.upper() if state else "EXPLORE",
            player_target=state.player_target if state else None,
            active_npc_affinity=active_affinity,
        )

    def get_active_npc_affinity(self) -> Optional[float]:
        """Devuelve la afinidad del NPC activo en conversación, o None si no está en TALK."""
        return self.game_state_controller.sync_active_npc_affinity()

    def get_available_actions_projection(self) -> AvailableActionsProjection:
        """Devuelve las acciones disponibles en formato DTO para la interfaz de usuario."""
        current_place = self.game_state_controller.data.place
        moves = []
        if current_place and current_place.connections:
            for direction, conn in current_place.connections.items():
                moves.append(
                    MoveOptionProjection(
                        direction=direction,
                        target=conn.target,
                        distance=conn.distance,
                        terrain=conn.terrain_type or "normal",
                    )
                )

        npcs = []
        for npc_info in self.game_state_controller.get_npc_list():
            npcs.append(npc_info["name"])

        look_targets = [current_place.name] if current_place else []

        return AvailableActionsProjection(
            moves=moves,
            npcs=npcs,
            look_targets=look_targets,
        )

    def get_available_actions(self) -> dict:
        """Devuelve las acciones disponibles para la interfaz de usuario (compatibilidad dict)."""
        return self.get_available_actions_projection().model_dump()

    def get_ui_state(self) -> dict:
        """Devuelve un resumen del estado del juego para la barra de interfaz (compatibilidad dict)."""
        return self.get_ui_state_projection().model_dump()
