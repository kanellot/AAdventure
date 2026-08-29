import os
import json
import tempfile
import shutil
from typing import List, Optional, Dict
from domains import World, Location, Place, Connection, NPC, Player, NPCMotivations
from adventure_packager import AdventurePackager

class EditorController:
    """
    Controlador lógico del editor de historias. Mantiene el estado en memoria
    de los modelos Pydantic y encapsula la lógica de carga, edición y guardado.
    """

    def __init__(self):
        self.current_file_path: Optional[str] = None
        self.world: Optional[World] = None
        self.npcs: List[NPC] = []
        self.player: Optional[Player] = None

    def new_story(self):
        """
        Inicializa un proyecto de historia vacío con valores por defecto básicos.
        """
        self.current_file_path = None
        
        # 1. Crear Mundo inicial vacío
        self.world = World(
            id="w_01",
            name="Nuevo Mundo",
            description="Una comarca inexplorada.",
            locations=[]
        )
        
        # 2. Crear NPCs vacíos
        self.npcs = []
        
        # 3. Crear Jugador inicial por defecto
        self.player = Player(
            id="player",
            name="Aventurero",
            description="Un intrépido explorador.",
            player_location="",
            state="none",
            gold=10,
            travel_speed=4.5,
            elapsed_time=0
        )

    def load_story(self, aad_path: str):
        """
        Desempaqueta un archivo .aad, carga y valida los modelos de datos en memoria.
        """
        temp_dir = AdventurePackager.unpack_to_temp(aad_path)
        try:
            # 1. Cargar Mundo
            world_path = os.path.join(temp_dir, "world.json")
            with open(world_path, "r", encoding="utf-8") as f:
                world_data = json.load(f)
            self.world = World.model_validate(world_data["world"])

            # 2. Cargar NPCs
            npcs_path = os.path.join(temp_dir, "npcs.json")
            with open(npcs_path, "r", encoding="utf-8") as f:
                npcs_data = json.load(f)
            self.npcs = [NPC.model_validate(n) for n in npcs_data.get("NPCS", [])]

            # 3. Cargar Jugador
            player_path = os.path.join(temp_dir, "player.json")
            with open(player_path, "r", encoding="utf-8") as f:
                player_data = json.load(f)
            self.player = Player.model_validate(player_data["player"])

            self.current_file_path = aad_path
        finally:
            shutil.rmtree(temp_dir)

    def save_story(self, aad_path: str):
        """
        Serializa los modelos actuales de memoria y los empaqueta en el archivo .aad.
        """
        # Salvaguarda: si la ubicación inicial del jugador está vacía y existen lugares, le asignamos el primero
        if self.player and not self.player.player_location:
            all_places = self.get_all_places()
            if all_places:
                self.player.player_location = all_places[0].name

        # Preparar estructuras JSON según el esquema esperado
        world_dict = {"world": self.world.model_dump()}
        npcs_dict = {"NPCS": [npc.model_dump() for npc in self.npcs]}
        player_dict = {"player": self.player.model_dump()}

        # Empaquetar a .aad
        AdventurePackager.pack(aad_path, world_dict, npcs_dict, player_dict)
        self.current_file_path = aad_path

    # --- GETTERS ---

    def get_locations(self) -> List[Location]:
        return self.world.locations if self.world else []

    def get_location_by_id(self, loc_id: str) -> Optional[Location]:
        if not self.world:
            return None
        for loc in self.world.locations:
            if loc.id == loc_id:
                return loc
        return None

    def get_places_in_location(self, loc_id: str) -> List[Place]:
        loc = self.get_location_by_id(loc_id)
        return loc.places if loc else []

    def get_all_places(self) -> List[Place]:
        places = []
        if self.world:
            for loc in self.world.locations:
                places.extend(loc.places)
        return places

    def get_place_by_name(self, place_name: str) -> Optional[Place]:
        for p in self.get_all_places():
            if p.name == place_name:
                return p
        return None

    def get_place_by_id(self, place_id: str) -> Optional[Place]:
        for p in self.get_all_places():
            if p.id == place_id:
                return p
        return None

    def get_npcs(self) -> List[NPC]:
        return self.npcs

    def get_npc_by_id(self, npc_id: str) -> Optional[NPC]:
        for npc in self.npcs:
            if npc.id == npc_id:
                return npc
        return None

    # --- MUTADORES DE ENTIDADES ---

    def add_location(self, name: str, description: str) -> Location:
        loc_id = f"l_{len(self.world.locations) + 1:02d}"
        new_loc = Location(id=loc_id, name=name, description=description, places=[])
        self.world.locations.append(new_loc)
        return new_loc

    def add_place(self, loc_id: str, name: str, description: str) -> Optional[Place]:
        loc = self.get_location_by_id(loc_id)
        if not loc:
            return None
        # Generar un ID único basado en el total de places del mundo
        all_places_count = len(self.get_all_places())
        place_id = f"p_{all_places_count:02d}"
        
        new_place = Place(id=place_id, name=name, description=description, visible_entities=[], connections={})
        loc.places.append(new_place)

        # Si la ubicación del jugador está vacía, le asignamos este primer lugar
        if self.player and not self.player.player_location:
            self.player.player_location = name

        return new_place

    def add_npc(self, name: str, description: str) -> NPC:
        npc_id = f"npc_{name.lower().replace(' ', '_')}"
        new_npc = NPC(
            id=npc_id,
            name=name,
            description=description,
            state="idle",
            affinity=0.5,
            motivations=NPCMotivations(likes=[], dislikes=[]),
            services=[]
        )
        self.npcs.append(new_npc)
        return new_npc

    # --- LOGICA DE CONEXIONES ---

    def add_connection(self, place_a_name: str, place_b_name: str, dir_ab: str, dir_ba: str, distance: int, terrain: str):
        """
        Crea una conexión bidireccional entre Lugar A y Lugar B.
        """
        place_a = self.get_place_by_name(place_a_name)
        place_b = self.get_place_by_name(place_b_name)

        if not place_a or not place_b:
            raise ValueError("Lugar origen o destino no encontrado.")

        # Añadir conexión A -> B
        place_a.connections[dir_ab] = Connection(
            target=place_b.name,
            distance=distance,
            terrain_type=terrain
        )

        # Añadir conexión recíproca B -> A
        place_b.connections[dir_ba] = Connection(
            target=place_a.name,
            distance=distance,
            terrain_type=terrain
        )

    def remove_connection(self, place_name: str, direction: str):
        """
        Elimina la conexión en la dirección especificada de un lugar y,
        al mismo tiempo, busca y elimina la conexión recíproca en el lugar destino.
        """
        place = self.get_place_by_name(place_name)
        if not place or direction not in place.connections:
            return

        conn = place.connections[direction]
        target_name = conn.target
        target_place = self.get_place_by_name(target_name)

        # Borrar conexión de ida A -> B
        del place.connections[direction]

        # Buscar y borrar conexión recíproca B -> A
        if target_place:
            reciprocal_dir = None
            for dir_key, c in target_place.connections.items():
                if c.target == place_name:
                    reciprocal_dir = dir_key
                    break
            if reciprocal_dir:
                del target_place.connections[reciprocal_dir]
