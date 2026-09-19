"""Motor principal de juego (Fachada) que coordina acciones, estado y reglas."""

import os
import shutil
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel
from adventure_packager import AdventurePackager
from domains import (
    ActionCommand,
    AvailableActionsProjection,
    ConnectionProjection,
    GameState,
    GameStateProjection,
    LocationHierarchyProjection,
    LoreBlockDetailProjection,
    LoreConditionDetailProjection,
    LoreGraphProjection,
    MoveOptionProjection,
    NPC,
    Place,
    PlaceDetailProjection,
    PlaceProjection,
    PlayerSummaryProjection,
    ResultType,
    TurnDebugProjection,
    TurnResultProjection,
    UIStateProjection,
    WorldHierarchyProjection,
)
from engines.game.actions import BaseAction, DialogueAction, LookAction, MoveAction
from engines.game.lore_router import LoreRouter
from engines.game.state_controller import GameStateController, WorldState
from engines.game.utils import TimeCalculator
from engines.transformer import TransformerEngine


class GameEngine:
    """Coordinador y fachada principal del motor de juego."""

    def __init__(
        self,
        world_json_path: str,
        npcs_json_path: Optional[str] = None,
        player_json_path: Optional[str] = None,
        objects_json_path: Optional[str] = None,
        lore_json_path: Optional[str] = None,
        config_json_path: Optional[str] = None,
    ):
        self.temp_dir: Optional[str] = None
        self.turn_debug_steps: List[dict] = []

        if world_json_path.lower().endswith(".aad"):
            self.temp_dir = AdventurePackager.unpack_to_temp(world_json_path)
            world_path = os.path.join(self.temp_dir, "world.json")
            npcs_path = os.path.join(self.temp_dir, "npcs.json")
            player_path = os.path.join(self.temp_dir, "player.json")
            objects_path = os.path.join(self.temp_dir, "objects.json")
            lore_path = os.path.join(self.temp_dir, "loreblocks.json")
            config_path = os.path.join(self.temp_dir, "story_config.json")
        else:
            base_dir = os.path.dirname(world_json_path)
            base_name = os.path.basename(world_json_path)
            suffix = ("_" + base_name.split("_", 1)[1]) if ("_" in base_name and not base_name.startswith("world.")) else ""

            world_path = world_json_path
            npcs_path = npcs_json_path or (os.path.join(base_dir, f"npcs{suffix}") if os.path.exists(os.path.join(base_dir, f"npcs{suffix}")) else os.path.join(base_dir, "npcs.json"))
            player_path = player_json_path or (os.path.join(base_dir, f"player{suffix}") if os.path.exists(os.path.join(base_dir, f"player{suffix}")) else os.path.join(base_dir, "player.json"))
            objects_path = objects_json_path or (os.path.join(base_dir, f"objects{suffix}") if os.path.exists(os.path.join(base_dir, f"objects{suffix}")) else os.path.join(base_dir, "objects.json"))
            lore_path = lore_json_path or (os.path.join(base_dir, f"loreblocks{suffix}") if os.path.exists(os.path.join(base_dir, f"loreblocks{suffix}")) else os.path.join(base_dir, "loreblocks.json"))
            config_path = config_json_path or (os.path.join(base_dir, f"story_config{suffix}") if os.path.exists(os.path.join(base_dir, f"story_config{suffix}")) else os.path.join(base_dir, "story_config.json"))

        self.world_state = WorldState(
            world_path,
            npcs_path,
            player_path,
            objects_path,
            lore_path,
            config_path,
        )
        self.game_state_controller = GameStateController.create_from_world(self.world_state)
        self.fog_war = self.game_state_controller.fog_war
        LoreRouter.get_instance().update_lore_state_machine(self.game_state_controller)

    @property
    def game_state(self) -> GameState:
        return self.game_state_controller.game_state

    @property
    def gold(self) -> int:
        return self.game_state.gold

    @property
    def inventory(self) -> List[str]:
        return self.game_state.inventory

    @property
    def current_location(self) -> str:
        return self.game_state.current_location

    @property
    def visited_places(self) -> List[str]:
        return self.game_state.visited_places

    @property
    def known_places(self) -> List[str]:
        return self.game_state.known_places

    @property
    def known_npcs(self) -> List[str]:
        return self.game_state.known_npcs

    @property
    def known_objs(self) -> List[str]:
        return self.game_state.known_objs

    @property
    def visible_npcs(self) -> List[str]:
        return self.game_state.visible_npcs

    @property
    def visible_objs(self) -> List[str]:
        return self.game_state.visible_objs

    @property
    def active_lore_blocks(self) -> List[str]:
        return self.game_state.active_lore_blocks

    @property
    def done_lore_blocks(self) -> List[str]:
        return self.game_state.done_lore_blocks

    def move_to(self, target: str) -> None:
        self.game_state_controller.update_location(target)

    def spawn_npc(self, npc_id: str, place_id: Optional[str] = None) -> None:
        self.game_state_controller.spawn_npc(npc_id, place_id)

    def spawn_object(self, object_id: str, place_id: Optional[str] = None) -> None:
        self.game_state_controller.spawn_object(object_id, place_id)

    def give_item_to_player(self, object_id: str) -> None:
        self.game_state_controller.give_item_to_player(object_id)

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
        """Devuelve el objeto Place donde reside el NPC buscando en ubicación dinámica o visible_entities."""
        npc = self.get_npc_by_name_or_id(npc_id_or_name)
        if not npc:
            return None
        if hasattr(self, "game_state_controller") and self.game_state_controller:
            pid = self.game_state_controller.npc_locations.get(npc.id)
            if pid:
                p = self.world_state.places_by_id.get(pid) or self.world_state.places_by_name.get(pid)
                if p:
                    return p
        for place in self.world_state.places_by_id.values():
            if npc.id in place.visible_entities or npc.name in place.visible_entities:
                return place
        return None

    def change_npc_affinity(self, npc_name_or_id: str, delta: float) -> None:
        """Modifica la afinidad de un NPC si el sistema está activo."""
        if not getattr(self.world_state.story_config, "affinity", True):
            return
        npc = self.get_npc_by_name_or_id(npc_name_or_id)
        if npc:
            npc.affinity = round(max(0.0, min(1.0, npc.affinity + delta)), 4)
        for n in self.game_state_controller.data.npcs.values():
            if n.id == npc_name_or_id or n.name == npc_name_or_id:
                n.affinity = round(max(0.0, min(1.0, n.affinity + delta)), 4)

    def get_player_name(self) -> str:
        """Devuelve el nombre del jugador cargado en el estado."""
        if self.game_state_controller.player:
            return self.game_state_controller.player.name
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

        debug_proj = TurnDebugProjection(
            prompt="\n\n".join(debug_prompts) if debug_prompts else None,
            raw_response="\n\n".join(debug_raws) if debug_raws else None,
            structured_response="\n\n".join(debug_structureds) if debug_structureds else None,
            engine_result="\n\n".join(debug_results) if debug_results else None,
            rag_evaluation=rag_eval,
        )

        return TurnResultProjection(
            msg=msg,
            author=author,
            info_msg=info_msg,
            debug=debug_proj,
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
        LoreRouter.get_instance().update_lore_state_machine(self.game_state_controller)

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
                    not self.game_state_controller.place
                    or self.game_state_controller.place.id != npc_place.id
                ):
                    self.game_state_controller.update_location(npc_place.name)

                loaded_npc = self.game_state_controller.load_npc(npc.id)
                self.game_state_controller.update_state("TALK")
                self.game_state_controller.data.state.player_target = npc.name
                actual_npc = loaded_npc or npc
                if getattr(self.world_state.story_config, "affinity", True):
                    self.game_state_controller.data.state.active_npc_affinity = round(actual_npc.affinity, 4)
                else:
                    self.game_state_controller.data.state.active_npc_affinity = None
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

        final_msg = res.message
        triggered = getattr(step, "_triggered_lore", None)

        # Si una acción MOVE atravesó un lugar intermedio que disparó un LoreBlock:
        intermediate_place = getattr(step, "_triggered_intermediate_place", None)
        is_blocked = getattr(step, "_is_blocked", False)
        if not is_blocked and intermediate_place and triggered and dm:
            explain_step = LookAction(intermediate_place.name)
            explain_prompt = getattr(triggered, "directive", "") or f"(Durante el trayecto se observa detalladamente {intermediate_place.name})."
            self.game_state_controller._is_executing_forced_action = True
            try:
                explain_res = self._run_step(explain_step, explain_prompt, dm)
            finally:
                self.game_state_controller._is_executing_forced_action = False
            if explain_res and explain_res.message:
                final_msg = f"{final_msg}\n\n[En el trayecto por {intermediate_place.name}]: {explain_res.message}"

        if triggered and not is_blocked:
            eff = triggered.on_active if hasattr(triggered, "on_active") else None
            force_action = getattr(triggered, "force_action", False)
            act_type = getattr(eff, "trigger_action_type", None) if eff else None
            act_tgt = (getattr(eff, "trigger_action_target", None) or getattr(eff, "target", None)) if eff else None

            if force_action and not act_type and act_tgt:
                act_type = "TALK" if self.get_npc_by_name_or_id(act_tgt) else "EXPLAIN"

            if act_type:
                act_type = act_type.upper()

            if act_type and act_tgt:
                if act_type in ["MOVE", "EXPLORE"]:
                    self.game_state_controller.update_location(act_tgt)
                    self.game_state_controller.update_state("EXPLORE")
                    self.game_state_controller.data.state.player_target = ""
                    self.save()
                elif act_type == "TALK":
                    self.game_state_controller.update_state("TALK")
                    self.game_state_controller.data.state.player_target = act_tgt
                    self.game_state_controller.load_npc(act_tgt)
                    self.game_state_controller.sync_active_npc_affinity()
                    self.save()

                    # Ejecución automatizada de TALK con el LLM
                    if force_action and dm and (not isinstance(step, DialogueAction) or step.target_npc != act_tgt):
                        auto_prompt = getattr(triggered, "directive", "") or f"(El personaje {act_tgt} inicia la conversación)."
                        auto_step = DialogueAction(act_tgt)
                        self.game_state_controller._is_executing_forced_action = True
                        try:
                            auto_res = self._run_step(auto_step, auto_prompt, dm)
                        finally:
                            self.game_state_controller._is_executing_forced_action = False
                        if auto_res and auto_res.message:
                            final_msg = f"{final_msg}\n\n[{act_tgt}]: {auto_res.message}"
                            final_author = act_tgt

                elif act_type in ["LOOK", "EXPLAIN"]:
                    self.game_state_controller.update_state("LOOK")
                    self.game_state_controller.data.state.player_target = act_tgt
                    self.save()

                    # Ejecución automatizada de EXPLAIN/LOOK con el LLM
                    if force_action and dm and (not isinstance(step, LookAction) or step.target != act_tgt):
                        auto_step = LookAction(act_tgt)
                        auto_prompt = getattr(triggered, "directive", "") or f"(Se describe detalladamente {act_tgt})."
                        self.game_state_controller._is_executing_forced_action = True
                        try:
                            auto_res = self._run_step(auto_step, auto_prompt, dm)
                        finally:
                            self.game_state_controller._is_executing_forced_action = False
                        if auto_res and auto_res.message:
                            final_msg = f"{final_msg}\n\n{auto_res.message}"
                            final_author = "Dungeon Master"

        LoreRouter.get_instance().update_lore_state_machine(self.game_state_controller)
        return self._create_debug_turn_output(msg=final_msg, author=final_author)

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
        player = self.game_state_controller.player
        place = self.game_state_controller.place

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
        affinity_enabled = getattr(self.world_state.story_config, "affinity", True)
        if affinity_enabled and state and state.player_state.upper() == "TALK":
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
            active_lore_blocks=list(getattr(self.game_state_controller, "active_lore_blocks", [])),
            done_lore_blocks=list(getattr(self.game_state_controller, "done_lore_blocks", [])),
        )

    def get_ui_state_projection(self) -> UIStateProjection:
        """Devuelve un resumen del estado del juego en formato DTO para la interfaz."""
        state = self.game_state_controller.data.state
        player = self.game_state_controller.player
        place = self.game_state_controller.place

        active_affinity = None
        affinity_enabled = getattr(self.world_state.story_config, "affinity", True)
        if affinity_enabled and state and state.player_state.upper() == "TALK":
            active_affinity = self.game_state_controller.sync_active_npc_affinity()
            if active_affinity is None:
                active_affinity = getattr(state, "active_npc_affinity", None)

        game_st = state.player_state.upper() if state else "EXPLORE"
        can_send = game_st in ("TALK", "LOOK")
        allowed = ["MOVE", "LOOK", "TALK"]

        return UIStateProjection(
            player_name=player.name if player else "Jugador",
            gold=player.gold if player else 0,
            current_location=place.name if place else "Desconocido",
            formatted_time=self.get_formatted_time(),
            game_state=game_st,
            player_target=state.player_target if (state and state.player_target) else None,
            active_npc_affinity=active_affinity,
            can_send_message=can_send,
            allowed_actions=allowed,
        )

    def get_active_npc_affinity(self) -> Optional[float]:
        """Devuelve la afinidad del NPC activo en conversación, o None si no está en TALK."""
        return self.game_state_controller.sync_active_npc_affinity()

    def get_available_actions_projection(self) -> AvailableActionsProjection:
        """Devuelve las acciones disponibles en formato DTO para la interfaz de usuario."""
        current_place = self.game_state_controller.place
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

    def get_lore_graph_projection(self) -> LoreGraphProjection:
        """Genera una proyección exhaustiva de todos los LoreBlocks y sus condiciones evaluadas en tiempo real."""
        router = LoreRouter.get_instance()
        all_blocks = router._get_all_blocks(self.game_state_controller)

        active_blocks = set(getattr(self.game_state_controller, "active_lore_blocks", []))
        done_blocks = set(getattr(self.game_state_controller, "done_lore_blocks", []))

        block_projections: List[LoreBlockDetailProjection] = []
        active_cnt = 0
        done_cnt = 0
        unknown_cnt = 0

        for b in all_blocks:
            # 1. Determinar estado canónico
            if b.id in done_blocks or b.state == "done":
                st = "done"
                done_cnt += 1
            elif b.id in active_blocks or b.state == "active":
                st = "active"
                active_cnt += 1
            else:
                st = "unknown"
                unknown_cnt += 1

            is_acc = router.is_block_accessible(b, self.game_state_controller)

            # 2. Proyectar condiciones de activación (conditions)
            cond_projections: List[LoreConditionDetailProjection] = []
            for cond in getattr(b, "conditions", []) or []:
                is_met = router.evaluate_single_condition(cond, self.game_state_controller, evaluating_block=b)
                disp = self._format_condition_display(cond, is_met)
                cond_projections.append(
                    LoreConditionDetailProjection(
                        entity_type=cond.entity_type,
                        entity_id=cond.entity_id or "",
                        sub_condition=cond.sub_condition,
                        value=cond.value,
                        is_negated=cond.is_negated,
                        is_met=is_met,
                        display_text=disp,
                    )
                )

            # 3. Proyectar condiciones de salida (exit_conditions)
            exit_cond_projections: List[LoreConditionDetailProjection] = []
            for cond in getattr(b, "exit_conditions", []) or []:
                is_met = router.evaluate_single_condition(cond, self.game_state_controller, evaluating_block=b)
                disp = self._format_condition_display(cond, is_met)
                exit_cond_projections.append(
                    LoreConditionDetailProjection(
                        entity_type=cond.entity_type,
                        entity_id=cond.entity_id or "",
                        sub_condition=cond.sub_condition,
                        value=cond.value,
                        is_negated=cond.is_negated,
                        is_met=is_met,
                        display_text=disp,
                    )
                )

            # 4. Resúmenes de efectos
            act_effects = b.get_effects_for_timing("active") if hasattr(b, "get_effects_for_timing") else [getattr(b, "on_active", None)]
            don_effects = b.get_effects_for_timing("done") if hasattr(b, "get_effects_for_timing") else [getattr(b, "on_done", None)]
            act_sum = self._format_effects_summary(act_effects)
            don_sum = self._format_effects_summary(don_effects)

            block_projections.append(
                LoreBlockDetailProjection(
                    id=b.id,
                    name=b.name or b.title or b.id,
                    title=b.title or b.name or b.id,
                    state=st,
                    is_accessible=is_acc,
                    parent_id=b.parent_id,
                    trigger_mode=getattr(b, "trigger_mode", "proactive"),
                    rag_enabled=getattr(b, "rag_enabled", False),
                    trigger_phrases=list(getattr(b, "trigger_phrases", []) or []),
                    conditions=cond_projections,
                    exit_conditions=exit_cond_projections,
                    exit_rag_enabled=getattr(b, "exit_rag_enabled", False),
                    exit_trigger_phrases=list(getattr(b, "exit_trigger_phrases", []) or []),
                    directive=getattr(b, "directive", "") or (b.on_active.directive if getattr(b, "on_active", None) else "") or "",
                    force_action=bool(getattr(b, "force_action", False) or (b.on_active.force_action if getattr(b, "on_active", None) else False)),
                    on_active_summary=act_sum,
                    on_done_summary=don_sum,
                )
            )

        return LoreGraphProjection(
            blocks=block_projections,
            total_count=len(block_projections),
            active_count=active_cnt,
            done_count=done_cnt,
            unknown_count=unknown_cnt,
        )

    def _format_condition_display(self, cond: Any, is_met: bool) -> str:
        """Formatea una condición en texto descriptivo para el depurador."""
        etype = getattr(cond, "entity_type", "")
        eid = getattr(cond, "entity_id", "")
        sub = getattr(cond, "sub_condition", "")
        val = getattr(cond, "value", None)
        neg = getattr(cond, "is_negated", False)

        neg_prefix = "NO " if neg else ""

        if etype == "place":
            curr_loc = getattr(self.game_state_controller, "current_location", "")
            name_info = eid
            if hasattr(self, "world_state") and self.world_state:
                p = self.world_state.places_by_id.get(eid) or self.world_state.places_by_name.get(eid)
                if p:
                    name_info = f"'{p.name}'"
            if sub == "current_location":
                if is_met:
                    return f"{neg_prefix}Llegar a {name_info} (Actual: {curr_loc})"
                return f"{neg_prefix}Estar en {name_info} (Actual: {curr_loc or 'desconocido'})"
            elif sub == "visited":
                return f"{neg_prefix}Haber visitado el lugar {name_info}"
            elif sub == "unlocked":
                return f"{neg_prefix}Lugar {name_info} desbloqueado"

        elif etype == "npc":
            npc = self.get_npc_by_name_or_id(eid) if eid else None
            npc_name = npc.name if npc else (eid or "NPC")
            if sub == "talk":
                curr_state = getattr(self.game_state_controller.data.state, "player_state", "EXPLORE")
                curr_tgt = getattr(self.game_state_controller.data.state, "player_target", "")
                if is_met:
                    return f"{neg_prefix}Hablar con {npc_name} (En diálogo actualmente)"
                return f"{neg_prefix}Iniciar diálogo con {npc_name} (Actual: {curr_state} -> '{curr_tgt}')"
            elif sub == "affinity":
                aff_val = float(val or 0.5)
                curr_aff = npc.affinity if npc else 0.5
                aff_enabled = getattr(self.world_state.story_config, "affinity", True)
                if aff_enabled:
                    return f"{neg_prefix}Afinidad con {npc_name} >= {aff_val:.2f} (Actual: {curr_aff:.2f})"
                return f"{neg_prefix}Afinidad con {npc_name} >= {aff_val:.2f} (Desactivada en opciones)"
            elif sub == "known":
                return f"{neg_prefix}Conocer a {npc_name}"

        elif etype == "item":
            if sub == "have":
                qty = int(val or 1)
                curr_inv = getattr(self.game_state_controller.player, "inventory", []) if self.game_state_controller.player else []
                has_item = eid in curr_inv
                return f"{neg_prefix}Tener en inventario '{eid}' (Req: {qty}, Posee: {'Sí' if has_item else 'No'})"

        elif etype == "loreblock":
            if sub == "child_done":
                return f"{neg_prefix}Algún sub-bloque hijo completado (done)"
            elif sub == "active":
                return f"{neg_prefix}LoreBlock '{eid}' en estado ACTIVE"
            elif sub == "done":
                return f"{neg_prefix}LoreBlock '{eid}' completado (DONE)"

        elif etype == "gold":
            req_gold = int(val or 0)
            curr_gold = getattr(self.game_state_controller, "gold", 0)
            return f"{neg_prefix}Oro >= {req_gold} (Actual: {curr_gold})"

        return f"{neg_prefix}{etype}:{eid} ({sub}={val})"

    def _format_effects_summary(self, effects: Any) -> str:
        """Resume los efectos de un LoreEffects o lista de LoreEffects en una cadena amigable."""
        if not effects:
            return "(Sin efectos)"
        if isinstance(effects, list):
            items_str = []
            for eff in effects:
                s = self._format_single_effect_summary(eff)
                if s and s != "(Sin mutaciones de estado)":
                    tgt_prefix = f"[{eff.target}]: " if getattr(eff, "target", None) else ""
                    items_str.append(f"{tgt_prefix}{s}")
                elif getattr(eff, "directive", ""):
                    tgt_prefix = f"[{eff.target}]: " if getattr(eff, "target", None) else ""
                    dir_snip = eff.directive[:25] + "..." if len(eff.directive) > 25 else eff.directive
                    items_str.append(f"{tgt_prefix}\"{dir_snip}\"")
            return " | ".join(items_str) if items_str else "(Sin efectos)"
        return self._format_single_effect_summary(effects)

    def _format_single_effect_summary(self, effects: Any) -> str:
        if not effects:
            return "(Sin efectos)"
        parts = []
        if getattr(effects, "give_gold", 0) > 0:
            parts.append(f"+{effects.give_gold} oro")
        if getattr(effects, "gold_delta", 0) != 0:
            parts.append(f"{effects.gold_delta:+d} oro")
        if getattr(effects, "affinity_delta", 0.0) != 0:
            parts.append(f"Afinidad {effects.affinity_delta:+.2f}")
        for it in getattr(effects, "give_items", []):
            parts.append(f"+Ítem: {it}")
        for it in getattr(effects, "take_items", []):
            parts.append(f"-Ítem: {it}")
        for q in getattr(effects, "unlock_quests", []):
            parts.append(f"Misión: {q}")
        for p in getattr(effects, "unlock_places", []):
            parts.append(f"Lugar: {p}")
        if getattr(effects, "force_action", False):
            act_t = getattr(effects, "trigger_action_type", "") or "Auto"
            act_tg = getattr(effects, "trigger_action_target", "") or getattr(effects, "target", "")
            parts.append(f"⚡ Forzar {act_t} -> {act_tg}")
        for blk in getattr(effects, "block_connections", []):
            parts.append(f"🚫 Bloquear: {blk}")
        for alw in getattr(effects, "allow_connections", []):
            parts.append(f"🟢 Abrir: {alw}")
        return ", ".join(parts) if parts else "(Sin mutaciones de estado)"

