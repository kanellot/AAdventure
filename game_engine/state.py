import json
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from domains import World, Player, NPC, Place, Location, GameState, RuntimeState, PlaceProjection, NPCProjection, ActionResponse, TurnSummary

class WorldState:
    """Administra el estado dinámico global de todo el mundo de juego."""
    
    def __init__(self, world_json_path: str, npcs_json_path: str, player_json_path: str):
        self.world_json_path = world_json_path
        self.npcs_json_path = npcs_json_path
        self.player_json_path = player_json_path
        
        self.world: Optional[World] = None
        self.npcs: Dict[str, NPC] = {}
        self.player: Optional[Player] = None
        
        # Índices rápidos para búsquedas eficientes
        self.places_by_name: Dict[str, Place] = {}
        self.places_by_id: Dict[str, Place] = {}
        self.npcs_by_name: Dict[str, NPC] = {}
        
        self.load_initial_state()

    def load_initial_state(self):
        """Carga y valida los archivos JSON de entrada."""
        # 1. Cargar Mundo
        with open(self.world_json_path, "r", encoding="utf-8") as f:
            world_data = json.load(f)
        self.world = World.model_validate(world_data["world"])
        
        # Construir índices de lugares
        for loc in self.world.locations:
            for place in loc.places:
                self.places_by_name[place.name] = place
                self.places_by_id[place.id] = place
                
        # 2. Cargar NPCs
        with open(self.npcs_json_path, "r", encoding="utf-8") as f:
            npcs_data = json.load(f)
        for npc_data in npcs_data["NPCS"]:
            npc = NPC.model_validate(npc_data)
            self.npcs[npc.id] = npc
            self.npcs_by_name[npc.name] = npc
            
        # 3. Cargar Jugador
        with open(self.player_json_path, "r", encoding="utf-8") as f:
            player_data = json.load(f)
        self.player = Player.model_validate(player_data["player"])


class GameStateController:
    """Gestiona la lógica activa, mutación y persistencia de GameState (datos del dominio)."""
    
    def __init__(self, data: GameState, world_state: WorldState):
        self.data = data
        self.world_state = world_state

    @classmethod
    def create_from_world(
        cls, 
        world_state: WorldState, 
        target: str = "", 
        prev_place: Optional[PlaceProjection] = None
    ) -> "GameStateController":
        """Genera una proyección del GameState basada en el estado global del mundo."""
        player = world_state.player
        if not player:
            raise ValueError("No se puede crear GameState sin un jugador cargado en WorldState.")
            
        # Obtener el lugar actual por nombre de localización
        current_place_orig = world_state.places_by_name.get(player.player_location)
        current_place = current_place_orig.model_copy(deep=True) if current_place_orig else None
        
        # Proyección de lugar para RuntimeState
        current_place_proj = None
        if current_place:
            current_place_proj = PlaceProjection(id=current_place.id, name=current_place.name)
            
        runtime_state = RuntimeState(
            player_state=player.state,
            player_target=target,
            current_place=current_place_proj,
            prev_place=prev_place
        )
        
        # Hacer copia profunda de player
        player_copy = player.model_copy(deep=True)
        
        # Cargar todos los NPCs visibles en este lugar
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
            place=current_place
        )
        
        controller = cls(data, world_state)
        
        # Asegurar que el NPC target de conversación está cargado (por si acaso no es visible inicialmente)
        if player.state.upper() == "TALK" and target:
            controller.load_npc(target)
            
        return controller

    def load_npc(self, npc_id_or_name: str) -> Optional[NPC]:
        """Carga un NPC del world_state al game_state local (como copia)."""
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
            else:
                return self.data.npcs[npc_full.id]
        return None

    def update_location(self, new_location_name_or_id: str):
        """Actualiza la ubicación del jugador si el lugar existe por ID o nombre."""
        dest_place_full = None
        if new_location_name_or_id in self.world_state.places_by_id:
            dest_place_full = self.world_state.places_by_id[new_location_name_or_id]
        elif new_location_name_or_id in self.world_state.places_by_name:
            dest_place_full = self.world_state.places_by_name[new_location_name_or_id]

        if dest_place_full:
            # Actualizar prev_place con el current_place actual
            self.data.state.prev_place = self.data.state.current_place
            self.data.state.current_place = PlaceProjection(id=dest_place_full.id, name=dest_place_full.name)
            self.data.place = dest_place_full.model_copy(deep=True)
            
            # Vaciar NPCs anteriores y cargar los visibles en la nueva ubicación
            self.data.npcs = {}
            for entity_id in dest_place_full.visible_entities:
                if entity_id in self.world_state.npcs:
                    npc_full = self.world_state.npcs[entity_id]
                    self.data.npcs[npc_full.id] = npc_full.model_copy(deep=True)

    def update_state(self, new_state: str):
        """Actualiza el estado dinámico del jugador."""
        self.data.state.player_state = new_state

    def save(self):
        """Sincroniza y guarda los cambios de GameState de vuelta en WorldState."""
        world_state = self.world_state
        if world_state.player:
            world_state.player.state = self.data.state.player_state
            world_state.player.gold = self.data.player.gold
            world_state.player.active_quest = self.data.player.active_quest
            world_state.player.completed_quests = self.data.player.completed_quests
            if self.data.place:
                world_state.player.player_location = self.data.place.name
                
        # Sincronizar todos los NPCs cargados en el game_state local de vuelta a WorldState
        for npc_id, npc_local in self.data.npcs.items():
            if npc_id in world_state.npcs:
                npc_world = world_state.npcs[npc_id]
                npc_world.affinity = npc_local.affinity
                npc_world.conversation = npc_local.conversation
                npc_world.state = npc_local.state

    def get_current_location(self) -> Optional[dict]:
        """Devuelve el ID y nombre de la localización actual del jugador."""
        current_place = self.data.place
        if current_place:
            for location in self.world_state.world.locations:
                if any(p.id == current_place.id for p in location.places):
                    return {"id": location.id, "name": location.name}
        return None

    def get_location_list(self) -> list[dict]:
        """Devuelve una lista con el ID y nombre de todas las localizaciones del mundo."""
        return [{"id": loc.id, "name": loc.name} for loc in self.world_state.world.locations]

    def get_places_list(self) -> list[dict]:
        """Devuelve una lista con el ID y nombre de todos los lugares dentro de la localización actual."""
        current_place = self.data.place
        if current_place:
            for location in self.world_state.world.locations:
                if any(p.id == current_place.id for p in location.places):
                    return [{"id": p.id, "name": p.name} for p in location.places]
        return []

    def get_npc_list(self) -> list[dict]:
        """Devuelve una lista con el ID y nombre de todos los NPCs que hay en la localización actual."""
        current_place = self.data.place
        if current_place:
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


