"""Controlador de estado de juego y proyección de entidades del mundo."""

import json
from typing import Dict, List, Optional
from domains import (
    GameState,
    NPC,
    Place,
    PlaceProjection,
    Player,
    RuntimeState,
    World,
)
from engines.game.utils import FogWar, PathCalculator, TimeCalculator


class WorldState:
    """Administra el estado dinámico global de todo el mundo de juego."""

    def __init__(self, world_json_path: str, npcs_json_path: str, player_json_path: str):
        self.world_json_path = world_json_path
        self.npcs_json_path = npcs_json_path
        self.player_json_path = player_json_path

        self.world: Optional[World] = None
        self.npcs: Dict[str, NPC] = {}
        self.player: Optional[Player] = None

        self.places_by_name: Dict[str, Place] = {}
        self.places_by_id: Dict[str, Place] = {}
        self.npcs_by_name: Dict[str, NPC] = {}

        self.load_initial_state()

    def load_initial_state(self) -> None:
        """Carga y valida los archivos JSON de inicialización del mundo."""
        with open(self.world_json_path, "r", encoding="utf-8") as f:
            world_data = json.load(f)
        self.world = World.model_validate(world_data["world"])

        for loc in self.world.locations:
            for place in loc.places:
                self.places_by_name[place.name] = place
                self.places_by_id[place.id] = place

        with open(self.npcs_json_path, "r", encoding="utf-8") as f:
            npcs_data = json.load(f)
        for npc_data in npcs_data["NPCS"]:
            npc = NPC.model_validate(npc_data)
            self.npcs[npc.id] = npc
            self.npcs_by_name[npc.name] = npc

        with open(self.player_json_path, "r", encoding="utf-8") as f:
            player_data = json.load(f)
        self.player = Player.model_validate(player_data["player"])


class GameStateController:
    """Gestiona la lógica activa, mutación y persistencia de GameState."""

    def __init__(self, data: GameState, world_state: WorldState, fog_war: Optional[FogWar] = None):
        self.data = data
        self.world_state = world_state

        if fog_war is not None:
            self.fog_war = fog_war
        else:
            visited = getattr(data.player, "visited_places", []) or []
            initial = data.place.name if data.place else (data.player.player_location if data.player else None)
            self.fog_war = FogWar(
                places=world_state.places_by_name,
                initial_place=initial,
                visited_places=visited,
                world=world_state.world,
                npcs=world_state.npcs,
            )

        if self.data.place:
            self.fog_war.visit(self.data.place.name)
            if hasattr(self.data.player, "visited_places"):
                if self.data.place.name not in self.data.player.visited_places:
                    self.data.player.visited_places.append(self.data.place.name)

    @classmethod
    def create_from_world(
        cls,
        world_state: WorldState,
        target: str = "",
        prev_place: Optional[PlaceProjection] = None,
    ) -> "GameStateController":
        """Genera una proyección del GameState basada en el estado global del mundo."""
        player = world_state.player
        if not player:
            raise ValueError("No se puede crear GameState sin un jugador cargado en WorldState.")

        current_place_orig = world_state.places_by_name.get(player.player_location)
        current_place = current_place_orig.model_copy(deep=True) if current_place_orig else None

        current_place_proj = None
        if current_place:
            current_place_proj = PlaceProjection(id=current_place.id, name=current_place.name)

        initial_state = player.state.upper() if player.state else "EXPLORE"
        if initial_state not in ["TALK", "LOOK"]:
            initial_state = "EXPLORE"

        runtime_state = RuntimeState(
            player_state=initial_state,
            player_target=target,
            current_place=current_place_proj,
            prev_place=prev_place,
            travel_speed=player.travel_speed,
            elapsed_time=player.elapsed_time,
        )

        player_copy = player.model_copy(deep=True)

        npcs = {}
        if current_place:
            for entity_id in current_place.visible_entities:
                if entity_id in world_state.npcs:
                    npc_full = world_state.npcs[entity_id]
                    npcs[npc_full.id] = npc_full.model_copy(deep=True)

        data = GameState(
            state=runtime_state,
            player=player_copy,
            npcs=npcs,
            place=current_place,
        )

        controller = cls(data, world_state)

        if player.state.upper() == "TALK" and target:
            loaded_npc = controller.load_npc(target)
            if loaded_npc:
                controller.data.state.active_npc_affinity = round(loaded_npc.affinity, 4)

        return controller

    def load_npc(self, npc_id_or_name: str) -> Optional[NPC]:
        """Carga un NPC del world_state al game_state local."""
        npc_full = None
        if npc_id_or_name in self.world_state.npcs:
            npc_full = self.world_state.npcs[npc_id_or_name]
        elif npc_id_or_name in self.world_state.npcs_by_name:
            npc_full = self.world_state.npcs_by_name[npc_id_or_name]

        if npc_full:
            if npc_full.id not in self.data.npcs:
                npc_copy = npc_full.model_copy(deep=True)
                self.data.npcs[npc_copy.id] = npc_copy
                return npc_copy
            return self.data.npcs[npc_full.id]
        return None

    def calculate_path_travel_time(self, start_name: str, end_name: str) -> int:
        """Calcula el tiempo total de viaje en minutos entre dos lugares."""
        return TimeCalculator.calculate_travel_time_between_places(
            self.world_state.places_by_name,
            start_name,
            end_name,
            travel_speed=self.data.state.travel_speed,
        )

    def find_shortest_path_places(self, start_name: str, end_name: str) -> List[Place]:
        """Retorna la lista de lugares intermedios en la ruta óptima."""
        return PathCalculator.find_intermediate_places(
            self.world_state.places_by_name,
            start_name,
            end_name,
        )

    def update_location(self, new_location_name_or_id: str) -> None:
        """Actualiza la ubicación del jugador si el lugar existe por ID o nombre."""
        dest_place_full = None
        if new_location_name_or_id in self.world_state.places_by_id:
            dest_place_full = self.world_state.places_by_id[new_location_name_or_id]
        elif new_location_name_or_id in self.world_state.places_by_name:
            dest_place_full = self.world_state.places_by_name[new_location_name_or_id]

        if dest_place_full:
            self.fog_war.visit(dest_place_full.name)
            if hasattr(self.data.player, "visited_places"):
                if dest_place_full.name not in self.data.player.visited_places:
                    self.data.player.visited_places.append(dest_place_full.name)

            if self.data.place and self.data.place.name != dest_place_full.name:
                travel_time = self.calculate_path_travel_time(self.data.place.name, dest_place_full.name)
                self.data.state.elapsed_time += travel_time

            self.data.state.prev_place = self.data.state.current_place
            self.data.state.current_place = PlaceProjection(id=dest_place_full.id, name=dest_place_full.name)
            self.data.place = dest_place_full.model_copy(deep=True)

            self.data.npcs = {}
            for entity_id in dest_place_full.visible_entities:
                if entity_id in self.world_state.npcs:
                    npc_full = self.world_state.npcs[entity_id]
                    self.data.npcs[npc_full.id] = npc_full.model_copy(deep=True)

    def update_state(self, new_state: str) -> None:
        """Actualiza el estado dinámico del jugador (ej. EXPLORE, TALK o LOOK)."""
        self.data.state.player_state = new_state.upper()
        if self.data.state.player_state != "TALK":
            self.data.state.active_npc_affinity = None
        else:
            self.sync_active_npc_affinity()

    def sync_active_npc_affinity(self) -> Optional[float]:
        """Sincroniza el nivel de afinidad del NPC activo en RuntimeState si el estado es TALK."""
        if self.data.state.player_state.upper() == "TALK":
            target = self.data.state.player_target
            if target:
                npc = None
                for n in self.data.npcs.values():
                    if n.id == target or n.name == target:
                        npc = n
                        break
                if not npc and hasattr(self, "world_state") and self.world_state:
                    npc = self.load_npc(target)
                if npc:
                    self.data.state.active_npc_affinity = round(npc.affinity, 4)
                    return self.data.state.active_npc_affinity
        self.data.state.active_npc_affinity = None
        return None

    def save(self) -> None:
        """Sincroniza y guarda los cambios de GameState de vuelta en WorldState."""
        world_state = self.world_state
        if world_state.player:
            world_state.player.state = self.data.state.player_state
            world_state.player.gold = self.data.player.gold
            world_state.player.active_quest = self.data.player.active_quest
            world_state.player.completed_quests = self.data.player.completed_quests
            world_state.player.travel_speed = self.data.state.travel_speed
            world_state.player.elapsed_time = self.data.state.elapsed_time
            if hasattr(world_state.player, "visited_places"):
                world_state.player.visited_places = self.fog_war.get_visited_places()
            if self.data.place:
                world_state.player.player_location = self.data.place.name

        for npc_id, npc_local in self.data.npcs.items():
            if npc_id in world_state.npcs:
                npc_world = world_state.npcs[npc_id]
                npc_world.affinity = npc_local.affinity
                npc_world.conversation = npc_local.conversation
                npc_world.state = npc_local.state

    def get_current_location(self) -> Optional[dict]:
        """Devuelve el ID y nombre de la localización actual del jugador."""
        current_place = self.data.place
        if current_place and self.world_state.world:
            for location in self.world_state.world.locations:
                if any(p.id == current_place.id for p in location.places):
                    return {"id": location.id, "name": location.name}
        return None

    def get_location_list(self) -> list[dict]:
        """Devuelve una lista con el ID y nombre de todas las localizaciones del mundo."""
        if not self.world_state.world:
            return []
        return [{"id": loc.id, "name": loc.name} for loc in self.world_state.world.locations]

    def get_places_list(self) -> list[dict]:
        """Devuelve una lista con el ID y nombre de todos los lugares dentro de la localización actual."""
        current_place = self.data.place
        if current_place and self.world_state.world:
            for location in self.world_state.world.locations:
                if any(p.id == current_place.id for p in location.places):
                    return [{"id": p.id, "name": p.name} for p in location.places]
        return []

    def get_npc_list(self) -> list[dict]:
        """Devuelve una lista con el ID y nombre de todos los NPCs en la localización actual."""
        current_place = self.data.place
        if current_place and self.world_state.world:
            for location in self.world_state.world.locations:
                if any(p.id == current_place.id for p in location.places):
                    npc_ids = set()
                    for p in location.places:
                        for entity_id in p.visible_entities:
                            npc_ids.add(entity_id)

                    npcs = []
                    for nid in npc_ids:
                        if nid in self.world_state.npcs:
                            npc = self.world_state.npcs[nid]
                            npcs.append({"id": npc.id, "name": npc.name})
                    return npcs
        return []
