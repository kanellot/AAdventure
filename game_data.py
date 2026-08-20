import json
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from domains import World, Player, NPC, Place, Location, GameState, NPCProjection, ActionResponse, TurnSummary

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
    
    def __init__(self, data: GameState):
        self.data = data

    @classmethod
    def create_from_world(cls, world_state: WorldState, prev_turns: Optional[List[TurnSummary]] = None) -> "GameStateController":
        """Genera una proyección del GameState basada en el estado global del mundo."""
        player = world_state.player
        if not player:
            raise ValueError("No se puede crear GameState sin un jugador cargado en WorldState.")
            
        # Obtener el lugar actual por nombre de localización
        current_place = world_state.places_by_name.get(player.player_location)
            
        # Recuperar NPCs visibles
        visible_npcs = []
        if current_place:
            for entity_id in current_place.visible_entities:
                if entity_id in world_state.npcs:
                    npc_full = world_state.npcs[entity_id]
                    visible_npcs.append(NPCProjection(id=npc_full.id, name=npc_full.name))
                    
        data = GameState(
            player_id=player.id,
            player_name=player.name,
            player_description=player.description,
            player_state=player.state,
            player_target="",
            gold=player.gold,
            active_quest=player.active_quest,
            current_place=current_place,
            visible_npcs=visible_npcs,
            prev_turns=prev_turns if prev_turns is not None else []
        )
        return cls(data)

    def update_location(self, new_location_name_or_id: str, world_state: WorldState):
        """Actualiza la ubicación del jugador si el lugar existe por ID o nombre."""
        current_place_full = None
        if new_location_name_or_id in world_state.places_by_id:
            current_place_full = world_state.places_by_id[new_location_name_or_id]
        elif new_location_name_or_id in world_state.places_by_name:
            current_place_full = world_state.places_by_name[new_location_name_or_id]

        if current_place_full:
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
        """Sincroniza y guarda los cambios de GameState de vuelta en WorldState."""
        if world_state.player:
            world_state.player.state = self.data.player_state
            world_state.player.gold = self.data.gold
            world_state.player.active_quest = self.data.active_quest
            if self.data.current_place:
                world_state.player.player_location = self.data.current_place.name


class GameData:
    """Fachada controladora del estado general del juego."""
    
    def __init__(self, world_json_path: str, npcs_json_path: str, player_json_path: str):
        self.world_state = WorldState(world_json_path, npcs_json_path, player_json_path)
        # Inicializa la proyección del jugador envuelta en GameStateController
        self.game_state_controller = GameStateController.create_from_world(self.world_state)

    def mutate(self, actions_input: ActionResponse | dict):
        """Ejecuta la acción clasificada por el LLM y actualiza el estado del jugador y del mundo.

        Args:
            actions_input: Objeto ActionResponse (Pydantic) o diccionario que contiene la acción.
        """
        # Asegurar que trabajamos con el objeto Pydantic ActionResponse
        if isinstance(actions_input, dict):
            actions_obj = ActionResponse.model_validate(actions_input)
        else:
            actions_obj = actions_input

        if actions_obj.action:
            action_type = actions_obj.action.upper()

            if action_type == "MOVE":
                # Si hay target para moverse, tomamos el primero
                if actions_obj.target:
                    destination = actions_obj.target[0]
                    self.game_state_controller.update_location(destination, self.world_state)

            elif action_type == "TALK":
                # Seteamos el estado a TALK y buscamos el nombre del NPC target
                self.game_state_controller.update_state("TALK")
                if actions_obj.target:
                    target_id = actions_obj.target[0]
                    npc_name = target_id
                    # Buscar el nombre real del NPC si el target es un ID
                    if target_id in self.world_state.npcs:
                        npc_name = self.world_state.npcs[target_id].name
                    elif target_id in self.world_state.npcs_by_name:
                        npc_name = self.world_state.npcs_by_name[target_id].name

                    self.game_state_controller.data.player_target = npc_name
                else:
                    self.game_state_controller.data.player_target = ""

        # Sincronizar cambios de vuelta en WorldState
        self.game_state_controller.save(self.world_state)

        # Re-inicializar el campo de visión / percepción para asegurar total consistencia
        # Conservando el player_target recién establecido en GameStateController
        current_target = self.game_state_controller.data.player_target
        current_prev_turns = self.game_state_controller.data.prev_turns
        self.game_state_controller = GameStateController.create_from_world(self.world_state, prev_turns=current_prev_turns)
        self.game_state_controller.data.player_target = current_target

