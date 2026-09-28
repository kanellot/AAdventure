import os
import json
import shutil
from typing import List, Optional, Tuple
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
        self.items: List[Item] = []
        self.lore_blocks: List[LoreBlock] = []
        self.story_config: StoryConfig = StoryConfig()
        self.is_dirty: bool = False

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

        # 3. Catálogo de Ítems vacío
        self.items = []

        # 4. Catálogo centralizado de LoreBlocks vacío
        self.lore_blocks = []

        # 5. Configuración de historia por defecto
        self.story_config = StoryConfig(elapsed_time=True, fog_war=True, affinity=True)

        # 6. Jugador asignado obligatoriamente al lugar inicial
        self.player = Player(
            id="player_01",
            name="Aventurero",
            description="Un intrépido explorador.",
            initial_location="p_inicio",
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

            # 4. Items (items.json o fallback objects.json)
            items_path = os.path.join(temp_dir, "items.json")
            if not os.path.exists(items_path):
                items_path = os.path.join(temp_dir, "objects.json")
            with open(items_path, "r", encoding="utf-8") as f:
                item_data = json.load(f)
            raw_items = item_data.get("items", item_data.get("objects", []))
            self.items = [Item.model_validate(it) for it in raw_items]

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
            self.is_dirty = False
        finally:
            shutil.rmtree(temp_dir)

    def validate_story(self) -> Tuple[bool, Optional[str]]:
        """
        Valida que la aventura cumpla las reglas obligatorias de integridad antes de guardar:
        1. Mínimo requerido: al menos un Mundo, una Localización, un Lugar y un Jugador.
        2. Cada entidad (Player, NPC, Item) debe tener un initial_location definido y válido:
           - Player: initial_location asignado a un lugar existente del mundo.
           - NPC: initial_location asignado a un lugar existente del mundo.
           - Item: initial_location asignado a un lugar existente o estar en el inventario del jugador.
        3. Todos los lugares (Places) deben estar conectados:
           - Si hay más de un lugar, ninguno puede carecer de conexiones.
           - Las conexiones deben apuntar a lugares válidos existentes.
           - Todo el grafo de lugares debe formar una única componente conexa (todos interconectados).
        """
        # 1. Mínimo estructural
        if not self.world:
            return False, "Para poder guardar la historia, se requiere como mínimo un Mundo (World) definido."

        locations = self.get_locations()
        if not locations or len(locations) < 1:
            return False, "Para poder guardar la historia, se requiere como mínimo una Localización (Location) definida en el mundo con al menos un lugar definido."

        all_places = self.get_all_places()
        if not all_places or len(all_places) < 1:
            return False, "Para poder guardar la historia, el mundo debe tener al menos un lugar definido (Place)."

        if not self.player:
            return False, "No se ha definido el jugador en la historia. Se requiere como mínimo un Jugador (Player) definido."

        valid_place_ids = {p.id for p in all_places}
        valid_place_names = {p.name for p in all_places}
        valid_places = valid_place_ids | valid_place_names

        # 2. Localización inicial de entidades
        # Player
        player_loc = (self.player.initial_location or "").strip()
        if not player_loc:
            return False, "El jugador (Player) debe tener una ubicación inicial (initial_location) definida."
        if player_loc not in valid_places:
            return False, f"El lugar de inicio asignado al jugador ('{player_loc}') no existe en el mundo."

        # NPCs
        for npc in self.npcs:
            npc_loc = (npc.initial_location or "").strip()
            if not npc_loc:
                return False, f"El personaje '{npc.name}' ({npc.id}) debe tener una ubicación inicial (initial_location) definida."
            if npc_loc not in valid_places:
                return False, f"La ubicación inicial asignada al personaje '{npc.name}' ('{npc_loc}') no existe en el mundo."

        # Items
        for item in self.items:
            item_loc = (item.initial_location or "").strip()
            in_player_inv = self.player and (
                item.id in (self.player.inventory or []) or item.name in (self.player.inventory or [])
            )
            if not item_loc and not in_player_inv:
                return (
                    False,
                    f"El ítem '{item.name}' ({item.id}) debe tener una ubicación inicial (initial_location) definida o estar en el inventario del jugador.",
                )
            if item_loc and item_loc not in ("inventory", "player") and item_loc not in valid_places:
                return False, f"La ubicación inicial asignada al ítem '{item.name}' ('{item_loc}') no existe en el mundo."

        # 3. Conexiones entre lugares
        if len(all_places) > 1:
            unconnected = [p for p in all_places if not p.connections]
            if unconnected:
                names = ", ".join(f"'{p.name}'" for p in unconnected)
                return False, f"Todos los lugares deben estar conectados. Los siguientes lugares no tienen conexiones: {names}."

            # Mapeo a ID canónico para validación de grafo conexo
            id_by_id_or_name = {p.id: p.id for p in all_places}
            id_by_id_or_name.update({p.name: p.id for p in all_places})

            adj = {p.id: set() for p in all_places}
            for p in all_places:
                for direction, conn in p.connections.items():
                    if conn.target not in valid_places:
                        return (
                            False,
                            f"La conexión '{direction}' en el lugar '{p.name}' apunta a un lugar que no existe ('{conn.target}').",
                        )
                    target_id = id_by_id_or_name.get(conn.target)
                    if target_id and target_id in adj:
                        adj[p.id].add(target_id)
                        adj[target_id].add(p.id)

            # Comprobar conexidad del grafo completo mediante BFS
            start_id = all_places[0].id
            visited = set()
            queue = [start_id]
            visited.add(start_id)

            while queue:
                curr_id = queue.pop(0)
                for neighbor_id in adj.get(curr_id, set()):
                    if neighbor_id not in visited:
                        visited.add(neighbor_id)
                        queue.append(neighbor_id)

            if len(visited) < len(all_places):
                unreachable = [p for p in all_places if p.id not in visited]
                names = ", ".join(f"'{p.name}'" for p in unreachable)
                return (
                    False,
                    f"Todos los lugares deben estar interconectados. Se encontraron lugares aislados del resto del mundo: {names}.",
                )

        return True, None

    def save_story(self, aad_path: str):
        """Valida y empaqueta los 6 archivos JSON en el archivo .aad."""
        valid, err = self.validate_story()
        if not valid:
            raise ValueError(err)

        world_dict = {"world": self.world.model_dump()}
        npcs_dict = {"npcs": [npc.model_dump() for npc in self.npcs]}
        player_dict = {"player": self.player.model_dump()}
        items_dict = {"items": [item.model_dump() for item in self.items]}
        lore_dict = {"lore_blocks": [lb.model_dump() for lb in self.lore_blocks]}
        config_dict = self.story_config.model_dump()

        AdventurePackager.pack(
            aad_path,
            world_dict,
            npcs_dict,
            player_dict,
            items_data=items_dict,
            lore_data=lore_dict,
            config_data=config_dict,
        )
        self.current_file_path = aad_path
        self.is_dirty = False

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

    def get_all_places(self) -> List[Place]:
        places = []
        if self.world:
            for loc in self.world.locations:
                places.extend(loc.places)
        return places

    def get_place(self, id_or_name: str) -> Optional[Place]:
        """Busca un lugar por su identificador único o por su nombre."""
        if not id_or_name:
            return None
        for p in self.get_all_places():
            if p.id == id_or_name or p.name == id_or_name:
                return p
        return None

    def get_place_by_name(self, place_name: str) -> Optional[Place]:
        return self.get_place(place_name)

    def get_place_by_id(self, place_id: str) -> Optional[Place]:
        return self.get_place(place_id)

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

        if self.player and not self.player.initial_location:
            self.player.initial_location = place_id

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

    def add_npc(self, name: str, description: str, initial_location: Optional[str] = None) -> NPC:
        npc_id = f"npc_{len(self.npcs) + 1:02d}_{name.lower().replace(' ', '_')}"
        new_npc = NPC(
            id=npc_id,
            name=name,
            description=description,
            initial_location=initial_location,
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

    # --- GETTERS Y MUTADORES DE ÍTEMS ---

    def get_items(self) -> List[Item]:
        return self.items

    def get_item_by_id(self, item_id: str) -> Optional[Item]:
        for item in self.items:
            if item.id == item_id:
                return item
        return None

    def add_item(self, name: str, description: str, state: str = "default", initial_location: Optional[str] = None) -> Item:
        item_id = f"obj_{len(self.items) + 1:02d}_{name.lower().replace(' ', '_')}"
        new_item = Item(
            id=item_id,
            name=name,
            description=description,
            state=state,
            initial_location=initial_location,
        )
        self.items.append(new_item)
        return new_item

    def remove_item(self, item_id: str) -> bool:
        for it in list(self.items):
            if it.id == item_id:
                self.items.remove(it)
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

    def add_connection(self, place_a_name: str, place_b_name: str, dir_ab: str, dir_ba: str, distance: int, terrain: str):
        place_a = self.get_place(place_a_name)
        place_b = self.get_place(place_b_name)
        if not place_a or not place_b:
            raise ValueError("Lugar origen o destino no encontrado.")

        place_a.connections[dir_ab] = Connection(target=place_b.name, distance=distance, terrain_type=terrain)
        place_b.connections[dir_ba] = Connection(target=place_a.name, distance=distance, terrain_type=terrain)

    def remove_connection(self, place_name: str, direction: str):
        place = self.get_place(place_name)
        if not place or direction not in place.connections:
            return

        conn = place.connections[direction]
        target_place = self.get_place(conn.target)
        del place.connections[direction]

        if target_place:
            reciprocal_dir = None
            for dir_key, c in target_place.connections.items():
                if c.target in [place.name, place.id]:
                    reciprocal_dir = dir_key
                    break
            if reciprocal_dir:
                del target_place.connections[reciprocal_dir]

    # --- RESOLUCIÓN Y REFERENCIAS CRUZADAS ---

    def resolve_entity_info(self, entity_id: str) -> Tuple[str, str, str]:
        """
        Resuelve una entidad por su identificador único o nombre.
        Retorna la tupla: (entity_type, name, emoji)
        Tipos posibles: 'place', 'npc', 'item', 'loreblock', 'player', 'unknown'
        """
        if not entity_id or not str(entity_id).strip():
            return ("unknown", "", "❓")

        eid = str(entity_id).strip()

        # 1. Place
        p = self.get_place(eid)
        if p:
            return ("place", p.name, "📍")

        # 2. NPC
        n = self.get_npc_by_id(eid)
        if n:
            return ("npc", n.name, "👤")

        # 3. Item
        if eid == "gold":
            return ("item", "Monedas de Oro", "💰")
        it = self.get_item_by_id(eid)
        if it:
            return ("item", it.name, "📦")

        # 4. LoreBlock
        b = self.get_lore_block_by_id(eid)
        if b:
            return ("loreblock", b.title or b.name or b.id, "📜")

        # 5. Player
        if self.player and (self.player.id == eid or self.player.name == eid):
            return ("player", self.player.name, "🧑")

        return ("unknown", eid, "🔹")

