import json
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from domains import World, Player, NPC, Place, Location

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


class PlayerState(BaseModel):
    """Representa la proyección del estado y percepción del jugador (Scope reducido).
    Este objeto es idóneo para convertirse a JSON y enviarse al LLM.
    """
    player_id: str
    player_name: str
    player_description: str
    player_state: str
    
    # Entidades dentro del alcance visual del jugador
    current_place: Optional[Place] = None
    visible_npcs: List[NPC] = Field(default_factory=list)

    @classmethod
    def create_from_world(cls, world_state: WorldState) -> "PlayerState":
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
                    visible_npcs.append(world_state.npcs[entity_id])
                    
        return cls(
            player_id=player.id,
            player_name=player.name,
            player_description=player.description,
            player_state=player.state,
            current_place=current_place,
            visible_npcs=visible_npcs
        )

    def update_location(self, new_location_name: str, world_state: WorldState):
        """Actualiza la ubicación del jugador si el lugar existe."""
        if new_location_name in world_state.places_by_name:
            self.current_place = world_state.places_by_name[new_location_name]
            
            # Actualizar NPCs visibles correspondientes a la nueva localización
            self.visible_npcs = []
            for entity_id in self.current_place.visible_entities:
                if entity_id in world_state.npcs:
                    self.visible_npcs.append(world_state.npcs[entity_id])

    def update_state(self, new_state: str):
        """Actualiza el estado dinámico del jugador."""
        self.player_state = new_state

    def save(self, world_state: WorldState):
        """Sincroniza y guarda los cambios de PlayerState de vuelta en WorldState."""
        if world_state.player:
            world_state.player.state = self.player_state
            if self.current_place:
                world_state.player.player_location = self.current_place.name


class GameState:
    """Fachada controladora del estado general del juego."""
    
    def __init__(self, world_json_path: str, npcs_json_path: str, player_json_path: str):
        self.world_state = WorldState(world_json_path, npcs_json_path, player_json_path)
        # Inicializa la proyección del jugador
        self.player_state = PlayerState.create_from_world(self.world_state)

    def mutate(self, action_type: str, **kwargs):
        """Ejecuta una acción que altera el estado del jugador y lo sincroniza con el mundo.
        
        Ejemplos de llamadas:
          game_state.mutate("MOVE", destination="Taberna")
          game_state.mutate("UPDATE_STATE", state="talking")
        """
        action_type = action_type.upper()
        
        if action_type == "MOVE":
            destination = kwargs.get("destination")
            if destination:
                self.player_state.update_location(destination, self.world_state)
                
        elif action_type == "UPDATE_STATE":
            state = kwargs.get("state")
            if state:
                self.player_state.update_state(state)
                
        # Sincronizar cambios de vuelta en WorldState
        self.player_state.save(self.world_state)
        
        # Re-inicializar el campo de visión / percepción para asegurar total consistencia
        self.player_state = PlayerState.create_from_world(self.world_state)
