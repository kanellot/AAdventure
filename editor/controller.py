import os
import json
import tempfile
import shutil
from typing import List, Optional, Dict, Tuple
from domains import (
    World,
    Location,
    Place,
    Connection,
    NPC,
    Player,
    NPCMotivations,
    Item,
    LoreBlock,
    StoryConfig,
)
from adventure_packager import AdventurePackager


class EditorController:
    """
    Controlador lógico del editor de historias. Mantiene el estado en memoria
    de los 6 modelos independientes y encapsula la lógica de carga, edición y guardado.
    """

    def __init__(self):
        self.current_file_path: Optional[str] = None
        self.world: Optional[World] = None
        self.npcs: List[NPC] = []
        self.player: Optional[Player] = None
        self.objects: List[Item] = []
        self.lore_blocks: List[LoreBlock] = []
        self.story_config: StoryConfig = StoryConfig()

    def new_story(self):
        """Inicializa un proyecto de historia vacío con entidades separadas."""
        self.current_file_path = os.path.join("Resources", "adventure_data", "Adventure.aad")

        # 1. Mundo inicial con una localización y lugar de muestra
        p_init = Place(
            id="p_inicio",
            name="Entrada Principal",
            description="El punto de partida de la aventura.",
            connections={},
        )
        l_init = Location(
            id="l_01",
            name="Comarca Inicial",
            description="Tierras tranquilas y conocidas.",
            places=[p_init],
        )
        self.world = World(
            id="w_01",
            name="Nuevo Mundo",
            description="Una comarca inexplorada.",
            locations=[l_init],
        )

        # 2. Catálogo de NPCs vacío
        self.npcs = []

        # 3. Catálogo de Objetos vacío
        self.objects = []

        # 4. Catálogo centralizado de LoreBlocks vacío
        self.lore_blocks = []

        # 5. Configuración de historia por defecto
        self.story_config = StoryConfig(elapsed_time=True, fog_war=True)

        # 6. Jugador asignado obligatoriamente al lugar inicial
        self.player = Player(
            id="player_01",
            name="Aventurero",
            description="Un intrépido explorador.",
            initial_place="p_inicio",
            player_location="p_inicio",
            gold=10,
            inventory=[],
            travel_speed=4.5,
            elapsed_time=0,
        )

    def load_story(self, aad_path: str):
        """Desempaqueta un archivo .aad y carga los 6 modelos independientes."""
        temp_dir = AdventurePackager.unpack_to_temp(aad_path)
        try:
            # 1. World
            world_path = os.path.join(temp_dir, "world.json")
            with open(world_path, "r", encoding="utf-8") as f:
                world_data = json.load(f)
            self.world = World.model_validate(world_data.get("world", world_data))

            # 2. NPCs
            npcs_path = os.path.join(temp_dir, "npcs.json")
            with open(npcs_path, "r", encoding="utf-8") as f:
                npcs_data = json.load(f)
            raw_npcs = npcs_data.get("npcs", npcs_data.get("NPCS", []))
            self.npcs = [NPC.model_validate(n) for n in raw_npcs]

            # 3. Player
            player_path = os.path.join(temp_dir, "player.json")
            with open(player_path, "r", encoding="utf-8") as f:
                player_data = json.load(f)
            self.player = Player.model_validate(player_data.get("player", player_data))

            # 4. Objects
            objects_path = os.path.join(temp_dir, "objects.json")
            with open(objects_path, "r", encoding="utf-8") as f:
                obj_data = json.load(f)
            raw_objs = obj_data.get("objects", obj_data.get("items", []))
            self.objects = [Item.model_validate(o) for o in raw_objs]

            # 5. LoreBlocks
            lore_path = os.path.join(temp_dir, "loreblocks.json")
            with open(lore_path, "r", encoding="utf-8") as f:
                lore_data = json.load(f)
            raw_lbs = lore_data.get("lore_blocks", lore_data.get("loreblocks", []))
            self.lore_blocks = [LoreBlock.model_validate(lb) for lb in raw_lbs]

            # 6. Story Config
            config_path = os.path.join(temp_dir, "story_config.json")
            with open(config_path, "r", encoding="utf-8") as f:
                cfg_data = json.load(f)
            self.story_config = StoryConfig.model_validate(cfg_data)

            self.current_file_path = aad_path
        finally:
            shutil.rmtree(temp_dir)

    def validate_story(self) -> Tuple[bool, Optional[str]]:
        """Valida que la aventura cumpla las reglas obligatorias de integridad."""
        if not self.player:
            return False, "No se ha definido el jugador en la historia."

        init_place = self.player.initial_place or self.player.player_location
        if not init_place or not init_place.strip():
            return False, "Es obligatorio que el jugador esté asignado a un lugar de inicio al comenzar la historia."

        all_places = self.get_all_places()
        if not all_places:
            return False, "El mundo debe tener al menos un lugar definido."

        valid_places = {p.id for p in all_places} | {p.name for p in all_places}
        if init_place not in valid_places:
            return False, f"El lugar de inicio asignado al jugador ('{init_place}') no existe en el mundo."

        return True, None

    def save_story(self, aad_path: str):
        """Valida y empaqueta los 6 archivos JSON en el archivo .aad."""
        valid, err = self.validate_story()
        if not valid:
            raise ValueError(err)

        # Sincronizar initial_place con player_location
        if self.player:
            if not self.player.initial_place and self.player.player_location:
                self.player.initial_place = self.player.player_location
            elif self.player.initial_place and not self.player.player_location:
                self.player.player_location = self.player.initial_place

        world_dict = {"world": self.world.model_dump()}
        npcs_dict = {"npcs": [npc.model_dump() for npc in self.npcs]}
        player_dict = {"player": self.player.model_dump()}
        objects_dict = {"objects": [obj.model_dump() for obj in self.objects]}
        lore_dict = {"lore_blocks": [lb.model_dump() for lb in self.lore_blocks]}
        config_dict = self.story_config.model_dump()

        AdventurePackager.pack(
            aad_path,
            world_dict,
            npcs_dict,
            player_dict,
            objects_dict,
            lore_dict,
            config_dict,
        )
        self.current_file_path = aad_path

    # --- GETTERS Y MUTADORES DE MUNDO ---

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

    def add_location(self, name: str, description: str) -> Location:
        loc_id = f"l_{len(self.world.locations) + 1:02d}"
        new_loc = Location(id=loc_id, name=name, description=description, places=[])
        self.world.locations.append(new_loc)
        return new_loc

    def add_place(self, loc_id: str, name: str, description: str) -> Optional[Place]:
        loc = self.get_location_by_id(loc_id)
        if not loc:
            return None
        all_places_count = len(self.get_all_places())
        place_id = f"p_{all_places_count + 1:02d}"
        new_place = Place(id=place_id, name=name, description=description, connections={})
        loc.places.append(new_place)

        if self.player and not self.player.initial_place:
            self.player.initial_place = place_id
            self.player.player_location = name

        return new_place

    def remove_location(self, loc_id: str) -> bool:
        if not self.world:
            return False
        for loc in list(self.world.locations):
            if loc.id == loc_id:
                self.world.locations.remove(loc)
                return True
        return False

    def remove_place(self, place_id: str) -> bool:
        if not self.world:
            return False
        for loc in self.world.locations:
            for p in list(loc.places):
                if p.id == place_id or p.name == place_id:
                    loc.places.remove(p)
                    # Limpiar conexiones hacia este lugar en otros lugares
                    for other_p in self.get_all_places():
                        for d in list(other_p.connections.keys()):
                            if other_p.connections[d].target in [p.name, p.id]:
                                del other_p.connections[d]
                    return True
        return False

    def get_location_by_place_id(self, place_id: str) -> Optional[Location]:
        if not self.world:
            return None
        for loc in self.world.locations:
            for p in loc.places:
                if p.id == place_id or p.name == place_id:
                    return loc
        return None

    # --- GETTERS Y MUTADORES DE NPCS ---

    def get_npcs(self) -> List[NPC]:
        return self.npcs

    def get_npc_by_id(self, npc_id: str) -> Optional[NPC]:
        for npc in self.npcs:
            if npc.id == npc_id:
                return npc
        return None

    def add_npc(self, name: str, description: str, initial_place: Optional[str] = None) -> NPC:
        npc_id = f"npc_{len(self.npcs) + 1:02d}_{name.lower().replace(' ', '_')}"
        new_npc = NPC(
            id=npc_id,
            name=name,
            description=description,
            initial_place=initial_place,
            state="idle",
            affinity=0.5,
            motivations=NPCMotivations(likes=[], dislikes=[]),
        )
        self.npcs.append(new_npc)
        return new_npc

    def remove_npc(self, npc_id: str) -> bool:
        for n in list(self.npcs):
            if n.id == npc_id:
                self.npcs.remove(n)
                return True
        return False

    # --- GETTERS Y MUTADORES DE OBJETOS (ITEMS) ---

    def get_objects(self) -> List[Item]:
        return self.objects

    def get_object_by_id(self, obj_id: str) -> Optional[Item]:
        for obj in self.objects:
            if obj.id == obj_id:
                return obj
        return None

    def add_object(self, name: str, description: str, state: str = "default", initial_place: Optional[str] = None) -> Item:
        obj_id = f"obj_{len(self.objects) + 1:02d}_{name.lower().replace(' ', '_')}"
        new_obj = Item(
            id=obj_id,
            name=name,
            description=description,
            state=state,
            initial_place=initial_place,
        )
        self.objects.append(new_obj)
        return new_obj

    def remove_object(self, obj_id: str) -> bool:
        for o in list(self.objects):
            if o.id == obj_id:
                self.objects.remove(o)
                return True
        return False

    # --- GETTERS Y MUTADORES DE LOREBLOCKS (HSM) ---

    def get_lore_blocks(self) -> List[LoreBlock]:
        return self.lore_blocks

    def get_lore_block_by_id(self, lb_id: str) -> Optional[LoreBlock]:
        for lb in self.lore_blocks:
            if lb.id == lb_id:
                return lb
        return None

    def add_lore_block(self, lore_block: LoreBlock) -> LoreBlock:
        self.lore_blocks.append(lore_block)
        return lore_block

    def remove_lore_block(self, lb_id: str) -> bool:
        for lb in list(self.lore_blocks):
            if lb.id == lb_id:
                self.lore_blocks.remove(lb)
                return True
        return False

    # --- COMPATIBILIDAD Y CONSULTAS GLOBALES ---

    def get_all_items(self) -> List[Tuple[Item, Place]]:
        """Retorna todos los objetos asociados a un lugar (para vistas de lugar)."""
        res = []
        for obj in self.objects:
            if obj.initial_place:
                p = self.get_place_by_id(obj.initial_place) or self.get_place_by_name(obj.initial_place)
                if p:
                    res.append((obj, p))
        return res

    def get_all_lore_blocks(self) -> List[Tuple[LoreBlock, str]]:
        """Retorna todos los bloques de lore con etiqueta descriptiva."""
        return [(lb, f"Lore: {lb.name or lb.title or lb.id}") for lb in self.lore_blocks]

    # --- CONEXIONES ENTRE LUGARES ---

    def add_connection(self, place_a_name: str, place_b_name: str, dir_ab: str, dir_ba: str, distance: int, terrain: str, passable: bool = True):
        place_a = self.get_place_by_name(place_a_name) or self.get_place_by_id(place_a_name)
        place_b = self.get_place_by_name(place_b_name) or self.get_place_by_id(place_b_name)
        if not place_a or not place_b:
            raise ValueError("Lugar origen o destino no encontrado.")

        place_a.connections[dir_ab] = Connection(target=place_b.name, distance=distance, terrain_type=terrain, passable=passable)
        place_b.connections[dir_ba] = Connection(target=place_a.name, distance=distance, terrain_type=terrain, passable=passable)

    def toggle_connection_passable(self, place_name: str, direction: str) -> bool:
        """Alterna el estado passable de una conexión y su recíproca. Retorna el nuevo estado."""
        place = self.get_place_by_name(place_name) or self.get_place_by_id(place_name)
        if not place or direction not in place.connections:
            return True

        conn = place.connections[direction]
        new_state = not getattr(conn, "passable", True)
        conn.passable = new_state

        target_place = self.get_place_by_name(conn.target) or self.get_place_by_id(conn.target)
        if target_place:
            for dir_key, c in target_place.connections.items():
                if c.target in [place.name, place.id]:
                    c.passable = new_state
                    break
        return new_state


    def remove_connection(self, place_name: str, direction: str):
        place = self.get_place_by_name(place_name) or self.get_place_by_id(place_name)
        if not place or direction not in place.connections:
            return

        conn = place.connections[direction]
        target_place = self.get_place_by_name(conn.target) or self.get_place_by_id(conn.target)
        del place.connections[direction]

        if target_place:
            reciprocal_dir = None
            for dir_key, c in target_place.connections.items():
                if c.target in [place.name, place.id]:
                    reciprocal_dir = dir_key
                    break
            if reciprocal_dir:
                del target_place.connections[reciprocal_dir]
