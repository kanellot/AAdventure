"""Controlador de estado de juego y proyección de entidades del mundo."""

import json
import os
from typing import Dict, List, Optional
from domains import (
    GameState,
    Item,
    LoreBlock,
    NPC,
    Place,
    PlaceProjection,
    Player,
    RuntimeState,
    StoryConfig,
    World,
)
from engines.game.utils import FogWar, PathCalculator, TimeCalculator


class WorldState:
    """Administra los catálogos y datos del mundo de juego cargados desde los 6 archivos JSON."""

    def __init__(
        self,
        world_json_path: str,
        npcs_json_path: Optional[str] = None,
        player_json_path: Optional[str] = None,
        objects_json_path: Optional[str] = None,
        lore_json_path: Optional[str] = None,
        config_json_path: Optional[str] = None,
    ):
        base_dir = os.path.dirname(world_json_path)
        self.world_json_path = world_json_path
        self.npcs_json_path = npcs_json_path or os.path.join(base_dir, "npcs.json")
        self.player_json_path = player_json_path or os.path.join(base_dir, "player.json")
        self.objects_json_path = objects_json_path or os.path.join(base_dir, "objects.json")
        self.lore_json_path = lore_json_path or os.path.join(base_dir, "loreblocks.json")
        self.config_json_path = config_json_path or os.path.join(base_dir, "story_config.json")

        self.world: Optional[World] = None
        self.npcs: Dict[str, NPC] = {}
        self.player: Optional[Player] = None
        self.objects: Dict[str, Item] = {}
        self.lore_blocks: Dict[str, LoreBlock] = {}
        self.story_config: StoryConfig = StoryConfig()

        self.places_by_name: Dict[str, Place] = {}
        self.places_by_id: Dict[str, Place] = {}
        self.npcs_by_name: Dict[str, NPC] = {}
        self.objects_by_name: Dict[str, Item] = {}

        self.load_initial_state()

    def load_initial_state(self) -> None:
        """Carga y valida los 6 archivos JSON de inicialización del mundo."""
        # 1. World
        if os.path.exists(self.world_json_path):
            with open(self.world_json_path, "r", encoding="utf-8") as f:
                world_data = json.load(f)
            self.world = World.model_validate(world_data.get("world", world_data))
            for loc in self.world.locations:
                for place in loc.places:
                    self.places_by_name[place.name] = place
                    self.places_by_id[place.id] = place

        # 2. NPCs
        if os.path.exists(self.npcs_json_path):
            with open(self.npcs_json_path, "r", encoding="utf-8") as f:
                npcs_data = json.load(f)
            raw_npcs = npcs_data.get("npcs", npcs_data.get("NPCS", []))
            for npc_data in raw_npcs:
                npc = NPC.model_validate(npc_data)
                self.npcs[npc.id] = npc
                self.npcs_by_name[npc.name] = npc

        # 3. Player
        if os.path.exists(self.player_json_path):
            with open(self.player_json_path, "r", encoding="utf-8") as f:
                player_data = json.load(f)
            self.player = Player.model_validate(player_data.get("player", player_data))

        # 4. Objects
        if os.path.exists(self.objects_json_path):
            with open(self.objects_json_path, "r", encoding="utf-8") as f:
                obj_data = json.load(f)
            raw_objs = obj_data.get("objects", obj_data.get("items", []))
            for o_data in raw_objs:
                obj = Item.model_validate(o_data)
                self.objects[obj.id] = obj
                self.objects_by_name[obj.name] = obj

        # 5. LoreBlocks
        if os.path.exists(self.lore_json_path):
            with open(self.lore_json_path, "r", encoding="utf-8") as f:
                lore_data = json.load(f)
            raw_lbs = lore_data.get("lore_blocks", lore_data.get("loreblocks", []))
            for lb_data in raw_lbs:
                lb = LoreBlock.model_validate(lb_data)
                self.lore_blocks[lb.id] = lb

        # 6. Story Config
        if os.path.exists(self.config_json_path):
            with open(self.config_json_path, "r", encoding="utf-8") as f:
                cfg_data = json.load(f)
            self.story_config = StoryConfig.model_validate(cfg_data)


class GameStateController:
    """Gestiona la lógica activa, mutación y reactividad de GameState."""

    def __init__(self, game_state: GameState, world_state: WorldState):
        self.game_state = game_state
        self.world_state = world_state

        # Ubicaciones dinámicas de entidades (place_id o None)
        self.npc_locations: Dict[str, Optional[str]] = {}
        for nid, npc in world_state.npcs.items():
            init_p = getattr(npc, "initial_place", None) or getattr(npc, "current_location", None)
            resolved_p = None
            if init_p:
                if init_p in world_state.places_by_id:
                    resolved_p = init_p
                elif init_p in world_state.places_by_name:
                    resolved_p = world_state.places_by_name[init_p].id

            # Si no se pudo resolver por initial_place exacto (o no tenía), buscar en visible_entities del mundo
            if not resolved_p:
                for p in world_state.places_by_id.values():
                    if nid in p.visible_entities or (hasattr(npc, "name") and npc.name in p.visible_entities):
                        resolved_p = p.id
                        break

            # Fallback secundario si init_p sigue sin resolverse: coincidencia parcial por nombre
            if not resolved_p and init_p:
                for p in world_state.places_by_id.values():
                    if p.name.lower() in init_p.lower() or init_p.lower() in p.name.lower():
                        resolved_p = p.id
                        break

            self.npc_locations[nid] = resolved_p

        self.object_locations: Dict[str, Optional[str]] = {}
        for oid, obj in world_state.objects.items():
            if oid in self.game_state.inventory:
                self.object_locations[oid] = None
            else:
                init_p = getattr(obj, "initial_place", None)
                resolved_p = None
                if init_p:
                    if init_p in world_state.places_by_id:
                        resolved_p = init_p
                    elif init_p in world_state.places_by_name:
                        resolved_p = world_state.places_by_name[init_p].id

                if not resolved_p:
                    for p in world_state.places_by_id.values():
                        for it in getattr(p, "items", []):
                            if it.id == oid or it.name == getattr(obj, "name", None):
                                resolved_p = p.id
                                break
                        if resolved_p:
                            break

                if not resolved_p and init_p:
                    for p in world_state.places_by_id.values():
                        if p.name.lower() in init_p.lower() or init_p.lower() in p.name.lower():
                            resolved_p = p.id
                            break

                self.object_locations[oid] = resolved_p

        # Controlador de niebla de guerra
        self.fog_war = FogWar(
            places=world_state.places_by_name,
            initial_place=self.game_state.current_location,
            visited_places=self.game_state.visited_places,
            world=world_state.world,
            npcs=world_state.npcs,
        )

        self.refresh_perception()

    @property
    def data(self) -> GameState:
        """Shim de compatibilidad para evitar roturas por accesos tipo game_state_controller.data."""
        return self.game_state

    @property
    def gold(self) -> int:
        return self.game_state.gold

    @gold.setter
    def gold(self, val: int) -> None:
        self.game_state.gold = max(0, val)
        if self.world_state.player:
            self.world_state.player.gold = self.game_state.gold

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

    @property
    def place(self) -> Optional[Place]:
        """Devuelve el Place actual del jugador."""
        curr = self.game_state.current_location
        return self.world_state.places_by_id.get(curr) or self.world_state.places_by_name.get(curr)

    @property
    def npcs(self) -> Dict[str, NPC]:
        """Devuelve los NPCs visibles en la localización actual."""
        res = {}
        for nid in self.game_state.visible_npcs:
            if nid in self.world_state.npcs:
                res[nid] = self.world_state.npcs[nid]
        return res

    @property
    def player(self) -> Player:
        return self.world_state.player

    @property
    def travel_speed(self) -> float:
        return self.game_state.travel_speed

    @property
    def elapsed_time(self) -> int:
        return self.game_state.elapsed_time

    def add_time(self, minutes: int) -> None:
        """Avanza el tiempo transcurrido en minutos y sincroniza con el jugador."""
        self.game_state.elapsed_time += max(0, minutes)
        if self.world_state.player:
            self.world_state.player.elapsed_time = self.game_state.elapsed_time

    @classmethod
    def create_from_world(
        cls,
        world_state: WorldState,
        target: str = "",
        prev_place: Optional[PlaceProjection] = None,
    ) -> "GameStateController":
        """Inicializa GameStateController basándose en los datos iniciales de WorldState."""
        player = world_state.player
        if not player:
            raise ValueError("No se puede crear GameState sin un jugador cargado en WorldState.")

        # Determinar lugar inicial obligatorio
        initial_place_str = player.initial_place or player.player_location
        if not initial_place_str:
            all_places = list(world_state.places_by_id.values())
            if all_places:
                initial_place_str = all_places[0].id
            else:
                initial_place_str = ""

        # Resolver ID de lugar
        place_obj = world_state.places_by_id.get(initial_place_str) or world_state.places_by_name.get(initial_place_str)
        curr_id = place_obj.id if place_obj else initial_place_str

        # Bloques de lore activos iniciales
        active_lbs = []
        if player.active_block:
            active_lbs.append(player.active_block)
        elif player.active_quest:
            active_lbs.append(player.active_quest)

        game_state = GameState(
            gold=player.gold,
            inventory=list(player.inventory),
            current_location=curr_id,
            visited_places=[curr_id, place_obj.name] if (curr_id and place_obj) else ([curr_id] if curr_id else []),
            known_places=[],
            known_npcs=list(getattr(player, "known_npcs", []) or []),
            known_objs=list(getattr(player, "known_items", []) or []),
            visible_npcs=[],
            visible_objs=[],
            active_lore_blocks=active_lbs,
            done_lore_blocks=list(getattr(player, "completed_quests", []) or []),
            player_state=player.state.upper() if (player.state and player.state.upper() not in ["NONE", ""]) else "EXPLORE",
            player_target=target,
            elapsed_time=player.elapsed_time,
            travel_speed=player.travel_speed,
        )

        controller = cls(game_state, world_state)
        return controller

    def refresh_perception(self) -> None:
        """Actualiza las entidades visibles y conocidas según la ubicación actual y flags de historia."""
        curr = self.game_state.current_location
        if not curr:
            return

        # 1. Niebla de guerra y lugares conocidos
        if self.world_state.story_config.fog_war:
            self.fog_war.visit(curr)
            curr_place = self.place
            if curr_place:
                self.fog_war.visit(curr_place.name)
            disc = self.fog_war.get_all_discovered_places()
            disc_ids = set()
            for p_name in disc:
                p = self.world_state.places_by_name.get(p_name) or self.world_state.places_by_id.get(p_name)
                if p:
                    disc_ids.add(p.id)
            self.game_state.known_places = list(set(disc) | disc_ids | set(self.game_state.visited_places))
        else:
            self.game_state.known_places = list(self.world_state.places_by_id.keys()) + list(self.world_state.places_by_name.keys())

        # 2. NPCs visibles y conocidos
        curr_place = self.place
        vis_npcs = []
        for nid, pid in self.npc_locations.items():
            if pid and (pid == curr or (curr_place and (pid == curr_place.name or pid == curr_place.id))):
                vis_npcs.append(nid)
                if nid not in self.game_state.known_npcs:
                    self.game_state.known_npcs.append(nid)
                npc_obj = self.world_state.npcs.get(nid)
                if npc_obj and npc_obj.name not in self.game_state.known_npcs:
                    self.game_state.known_npcs.append(npc_obj.name)
        self.game_state.visible_npcs = vis_npcs

        # 3. Objetos visibles y conocidos
        vis_objs = []
        for oid, pid in self.object_locations.items():
            if pid and (pid == curr or (curr_place and (pid == curr_place.name or pid == curr_place.id))):
                if oid not in self.game_state.inventory:
                    vis_objs.append(oid)
                    if oid not in self.game_state.known_objs:
                        self.game_state.known_objs.append(oid)
                    obj_item = self.world_state.objects.get(oid)
                    if obj_item and obj_item.name not in self.game_state.known_objs:
                        self.game_state.known_objs.append(obj_item.name)
        self.game_state.visible_objs = vis_objs

    def update_location(self, new_location_name_or_id: str) -> None:
        """Traslada al jugador a una nueva localización, actualizando tiempo y percepción."""
        dest_place = (
            self.world_state.places_by_id.get(new_location_name_or_id)
            or self.world_state.places_by_name.get(new_location_name_or_id)
        )
        if not dest_place:
            return

        origin_place = self.place
        if origin_place and origin_place.id != dest_place.id:
            self.game_state.prev_place = PlaceProjection(id=origin_place.id, name=origin_place.name)
            # Calcular tiempo transcurrido si está activo
            if self.world_state.story_config.elapsed_time:
                travel_time = TimeCalculator.calculate_travel_time_between_places(
                    self.world_state.places_by_name,
                    origin_place.name,
                    dest_place.name,
                    travel_speed=self.game_state.travel_speed,
                )
                self.game_state.elapsed_time += travel_time

        self.game_state.current_location = dest_place.id
        self.game_state.current_place = PlaceProjection(id=dest_place.id, name=dest_place.name)
        if dest_place.id not in self.game_state.visited_places:
            self.game_state.visited_places.append(dest_place.id)
        if dest_place.name not in self.game_state.visited_places:
            self.game_state.visited_places.append(dest_place.name)

        if self.world_state.player:
            self.world_state.player.visited_places = list(self.game_state.visited_places)
            self.world_state.player.player_location = dest_place.name
            self.world_state.player.initial_place = dest_place.id

        self.refresh_perception()

    def spawn_npc(self, npc_id: str, place_id: Optional[str] = None) -> None:
        """Sitúa dinámicamente un NPC en un lugar durante la aventura."""
        target_place = place_id or self.game_state.current_location
        # Normalizar ID de lugar
        p = self.world_state.places_by_id.get(target_place) or self.world_state.places_by_name.get(target_place)
        resolved_pid = p.id if p else target_place

        self.npc_locations[npc_id] = resolved_pid
        if npc_id not in self.game_state.known_npcs:
            self.game_state.known_npcs.append(npc_id)
        npc_obj = self.world_state.npcs.get(npc_id)
        if npc_obj and npc_obj.name not in self.game_state.known_npcs:
            self.game_state.known_npcs.append(npc_obj.name)

        self.refresh_perception()

    def spawn_object(self, object_id: str, place_id: Optional[str] = None) -> None:
        """Sitúa dinámicamente un Objeto en un lugar durante la aventura."""
        target_place = place_id or self.game_state.current_location
        p = self.world_state.places_by_id.get(target_place) or self.world_state.places_by_name.get(target_place)
        resolved_pid = p.id if p else target_place

        self.object_locations[object_id] = resolved_pid
        if object_id not in self.game_state.known_objs:
            self.game_state.known_objs.append(object_id)
        obj_item = self.world_state.objects.get(object_id)
        if obj_item and obj_item.name not in self.game_state.known_objs:
            self.game_state.known_objs.append(obj_item.name)

        self.refresh_perception()

    def give_item_to_player(self, object_id: str) -> None:
        """Añade un objeto al inventario del jugador y lo retira de cualquier lugar físico."""
        self.object_locations[object_id] = None
        if object_id not in self.game_state.inventory:
            self.game_state.inventory.append(object_id)
        if self.world_state.player and object_id not in self.world_state.player.inventory:
            self.world_state.player.inventory.append(object_id)
        if object_id not in self.game_state.known_objs:
            self.game_state.known_objs.append(object_id)
        obj_item = self.world_state.objects.get(object_id)
        if obj_item and obj_item.name not in self.game_state.known_objs:
            self.game_state.known_objs.append(obj_item.name)

        self.refresh_perception()

    def remove_item_from_player(self, object_id: str) -> None:
        """Retira un objeto del inventario del jugador."""
        if object_id in self.game_state.inventory:
            self.game_state.inventory.remove(object_id)
        if self.world_state.player and object_id in self.world_state.player.inventory:
            self.world_state.player.inventory.remove(object_id)

        self.refresh_perception()

    def load_npc(self, npc_id_or_name: str) -> Optional[NPC]:
        """Retorna el NPC buscado por ID o nombre."""
        if hasattr(self, "game_state") and hasattr(self.game_state, "npcs") and self.game_state.npcs:
            if npc_id_or_name in self.game_state.npcs:
                return self.game_state.npcs[npc_id_or_name]
            for n in self.game_state.npcs.values():
                if n.name == npc_id_or_name:
                    return n
        if npc_id_or_name in self.world_state.npcs:
            return self.world_state.npcs[npc_id_or_name]
        return self.world_state.npcs_by_name.get(npc_id_or_name)

    def update_state(self, new_state: str) -> None:
        """Actualiza el estado de interacción del jugador (EXPLORE, TALK, LOOK)."""
        self.game_state.player_state = new_state.upper()
        if self.game_state.player_state != "TALK":
            self.game_state.active_npc_affinity = None

    def sync_active_npc_affinity(self) -> Optional[float]:
        """Sincroniza la afinidad del NPC activo si el estado es TALK."""
        if self.game_state.player_state.upper() == "TALK" and self.game_state.player_target:
            npc = self.load_npc(self.game_state.player_target)
            if npc:
                self.game_state.active_npc_affinity = round(npc.affinity, 4)
                return self.game_state.active_npc_affinity
        self.game_state.active_npc_affinity = None
        return None

    def save(self) -> None:
        """Sincroniza los cambios del GameState en WorldState."""
        if self.world_state.player:
            self.world_state.player.gold = self.game_state.gold
            self.world_state.player.inventory = list(self.game_state.inventory)
            self.world_state.player.initial_place = self.game_state.current_location
            self.world_state.player.player_location = self.game_state.current_location
            self.world_state.player.elapsed_time = self.game_state.elapsed_time
            self.world_state.player.visited_places = list(self.game_state.visited_places)
            self.world_state.player.known_npcs = list(self.game_state.known_npcs)
            self.world_state.player.known_items = list(self.game_state.known_objs)
            if self.game_state.active_lore_blocks:
                self.world_state.player.active_block = self.game_state.active_lore_blocks[0]
            self.world_state.player.completed_quests = list(self.game_state.done_lore_blocks)

    def get_current_location(self) -> Optional[dict]:
        """Devuelve el ID y nombre de la localización actual del jugador."""
        current_place = self.place
        if current_place and self.world_state.world:
            for location in self.world_state.world.locations:
                if any(p.id == current_place.id or p.name == current_place.name for p in location.places):
                    return {"id": location.id, "name": location.name}
        return None

    def get_location_list(self) -> list[dict]:
        """Devuelve una lista con el ID y nombre de todas las localizaciones del mundo."""
        if not self.world_state.world:
            return []
        return [{"id": loc.id, "name": loc.name} for loc in self.world_state.world.locations]

    def get_places_list(self) -> list[dict]:
        """Devuelve una lista con el ID y nombre de todos los lugares dentro de la localización actual."""
        current_place = self.place
        if current_place and self.world_state.world:
            for location in self.world_state.world.locations:
                if any(p.id == current_place.id or p.name == current_place.name for p in location.places):
                    return [{"id": p.id, "name": p.name} for p in location.places]
        return []

    def get_npc_list(self) -> list[dict]:
        """Devuelve una lista con el ID y nombre de todos los NPCs en la localización (región) actual."""
        current_place = self.place
        if current_place and self.world_state.world:
            for location in self.world_state.world.locations:
                if any(p.id == current_place.id or p.name == current_place.name for p in location.places):
                    loc_place_ids = {p.id for p in location.places} | {p.name for p in location.places}
                    npcs = []
                    for nid, pid in self.npc_locations.items():
                        if pid in loc_place_ids and nid in self.world_state.npcs:
                            npc = self.world_state.npcs[nid]
                            npcs.append({"id": npc.id, "name": npc.name})
                    return npcs
        return []
