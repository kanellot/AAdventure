import json
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from domains import World, Player, NPC, Place, Location, PlayerState, NPCProjection, Actions

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



class LocalState:
    """Gestiona la lógica activa, mutación y persistencia de PlayerState."""
    
    def __init__(self, data: PlayerState):
        self.data = data

    @classmethod
    def create_from_world(cls, world_state: WorldState) -> "LocalState":
        """Genera una proyección del PlayerState basada en el estado global del mundo."""
        player = world_state.player
        if not player:
            raise ValueError("No se puede crear PlayerState sin un jugador cargado en WorldState.")
            
        # Obtener el lugar actual por nombre de localización
        current_place = world_state.places_by_name.get(player.player_location)
            
        # Recuperar NPCs visibles
        visible_npcs = []
        if current_place:
            for entity_id in current_place.visible_entities:
                if entity_id in world_state.npcs:
                    npc_full = world_state.npcs[entity_id]
                    visible_npcs.append(NPCProjection(id=npc_full.id, name=npc_full.name))
                    
        data = PlayerState(
            player_id=player.id,
            player_name=player.name,
            player_description=player.description,
            player_state=player.state,
            player_target="",
            current_place=current_place,
            visible_npcs=visible_npcs
        )
        return cls(data)

    def update_location(self, new_location_name: str, world_state: WorldState):
        """Actualiza la ubicación del jugador si el lugar existe."""
        if new_location_name in world_state.places_by_name:
            current_place_full = world_state.places_by_name[new_location_name]
            self.data.current_place = current_place_full
            
            # Actualizar NPCs visibles correspondientes a la nueva localización
            self.data.visible_npcs = []
            for entity_id in current_place_full.visible_entities:
                if entity_id in world_state.npcs:
                    npc_full = world_state.npcs[entity_id]
                    self.data.visible_npcs.append(NPCProjection(id=npc_full.id, name=npc_full.name))

    def update_state(self, new_state: str):
        """Actualiza el estado dinámico del jugador."""
        self.data.player_state = new_state

    def save(self, world_state: WorldState):
        """Sincroniza y guarda los cambios de PlayerState de vuelta en WorldState."""
        if world_state.player:
            world_state.player.state = self.data.player_state
            if self.data.current_place:
                world_state.player.player_location = self.data.current_place.name


class GameState:
    """Fachada controladora del estado general del juego."""
    
    def __init__(self, world_json_path: str, npcs_json_path: str, player_json_path: str):
        self.world_state = WorldState(world_json_path, npcs_json_path, player_json_path)
        # Inicializa la proyección del jugador envuelta en LocalState
        self.player_state = LocalState.create_from_world(self.world_state)

    def mutate(self, actions_input: Actions | dict):
        """Ejecuta las acciones clasificadas por el LLM y actualiza el estado del jugador y del mundo.

        Args:
            actions_input: Objeto Actions (Pydantic) o diccionario que contiene la lista de acciones.
        """
        # Asegurar que trabajamos con el objeto Pydantic Actions
        if isinstance(actions_input, dict):
            actions_obj = Actions.model_validate(actions_input)
        else:
            actions_obj = actions_input

        # Procesamos cada acción individual
        for act in actions_obj.actions:
            action_type = act.action.upper()

            if action_type == "MOVE":
                # Si hay targets para moverse, tomamos el primero
                if act.targets:
                    destination = act.targets[0]
                    self.player_state.update_location(destination, self.world_state)

            elif action_type == "TALK":
                # Seteamos el estado a TALK y buscamos el nombre del NPC target
                self.player_state.update_state("TALK")
                if act.targets:
                    target_id = act.targets[0]
                    npc_name = target_id
                    # Buscar el nombre real del NPC si el target es un ID
                    if target_id in self.world_state.npcs:
                        npc_name = self.world_state.npcs[target_id].name
                    elif target_id in self.world_state.npcs_by_name:
                        npc_name = self.world_state.npcs_by_name[target_id].name

                    self.player_state.data.player_target = npc_name
                else:
                    self.player_state.data.player_target = ""

        # Sincronizar cambios de vuelta en WorldState
        self.player_state.save(self.world_state)

        # Re-inicializar el campo de visión / percepción para asegurar total consistencia
        # Conservando el player_target recién establecido en LocalState
        current_target = self.player_state.data.player_target
        self.player_state = LocalState.create_from_world(self.world_state)
        self.player_state.data.player_target = current_target

