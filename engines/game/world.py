"""Catálogo canónico e inmutable del mundo cargado desde archivos JSON."""

from __future__ import annotations
import json
import os
from typing import Dict, Optional
from domains import (
    Item,
    Location,
    LoreBlock,
    NPC,
    Place,
    Player,
    StoryConfig,
    World,
)


class WorldState:
    """Administra los catálogos canónicos e inmutables del mundo cargados desde los 6 archivos JSON."""

    def __init__(
        self,
        world_json_path: str,
        npcs_json_path: Optional[str] = None,
        player_json_path: Optional[str] = None,
        items_json_path: Optional[str] = None,
        lore_json_path: Optional[str] = None,
        config_json_path: Optional[str] = None,
    ):
        base_dir = os.path.dirname(world_json_path)
        self.world_json_path = world_json_path
        self.npcs_json_path = npcs_json_path or os.path.join(base_dir, "npcs.json")
        self.player_json_path = player_json_path or os.path.join(base_dir, "player.json")
        self.items_json_path = items_json_path or os.path.join(base_dir, "items.json")
        self.lore_json_path = lore_json_path or os.path.join(base_dir, "loreblocks.json")
        self.config_json_path = config_json_path or os.path.join(base_dir, "story_config.json")

        self.world: Optional[World] = None
        self.npcs: Dict[str, NPC] = {}
        self.npcs_by_name: Dict[str, NPC] = {}
        self.player: Optional[Player] = None
        self.items: Dict[str, Item] = {}
        self.items_by_name: Dict[str, Item] = {}
        self.lore_blocks: Dict[str, LoreBlock] = {}
        self.story_config: StoryConfig = StoryConfig()

        self.places_by_id: Dict[str, Place] = {}
        self.places_by_name: Dict[str, Place] = {}
        self.place_to_location: Dict[str, Location] = {}

        self.load_initial_state()

    def load_initial_state(self) -> None:
        """Carga y valida los 6 archivos JSON canónicos de la aventura."""
        # 1. World & Lugares
        if os.path.exists(self.world_json_path):
            with open(self.world_json_path, "r", encoding="utf-8") as f:
                world_data = json.load(f)
            self.world = World.model_validate(world_data.get("world", world_data))
            for loc in self.world.locations:
                for place in loc.places:
                    self.places_by_id[place.id] = place
                    self.places_by_name[place.name] = place
                    self.place_to_location[place.id] = loc
                    self.place_to_location[place.name] = loc

        # 2. NPCs
        if os.path.exists(self.npcs_json_path):
            with open(self.npcs_json_path, "r", encoding="utf-8") as f:
                npcs_data = json.load(f)
            raw_npcs = (npcs_data.get("npcs") if isinstance(npcs_data, dict) else None) or (
                npcs_data.get("NPCS") if isinstance(npcs_data, dict) else None
            ) or (npcs_data if isinstance(npcs_data, list) else [])
            for npc_data in raw_npcs:
                npc = NPC.model_validate(npc_data)
                self.npcs[npc.id] = npc
                self.npcs_by_name[npc.name] = npc

        # 3. Player
        if os.path.exists(self.player_json_path):
            with open(self.player_json_path, "r", encoding="utf-8") as f:
                player_data = json.load(f)
            self.player = Player.model_validate(player_data.get("player", player_data))

        # 4. Items
        if os.path.exists(self.items_json_path):
            with open(self.items_json_path, "r", encoding="utf-8") as f:
                item_data_raw = json.load(f)
            raw_items = (
                item_data_raw.get("items") if isinstance(item_data_raw, dict) else None
            ) or (item_data_raw if isinstance(item_data_raw, list) else [])
            for i_data in raw_items:
                item = Item.model_validate(i_data)
                self.items[item.id] = item
                self.items_by_name[item.name] = item

        # 5. LoreBlocks
        if os.path.exists(self.lore_json_path):
            with open(self.lore_json_path, "r", encoding="utf-8") as f:
                lore_data = json.load(f)
            raw_lbs = (lore_data.get("lore_blocks") if isinstance(lore_data, dict) else None) or (
                lore_data.get("loreblocks") if isinstance(lore_data, dict) else None
            ) or (lore_data if isinstance(lore_data, list) else [])
            for lb_data in raw_lbs:
                lb = LoreBlock.model_validate(lb_data)
                self.lore_blocks[lb.id] = lb

        # 6. Story Config
        if os.path.exists(self.config_json_path):
            with open(self.config_json_path, "r", encoding="utf-8") as f:
                cfg_data = json.load(f)
            self.story_config = StoryConfig.model_validate(cfg_data)

    def get_place(self, id_or_name: str) -> Optional[Place]:
        """Devuelve el Place buscando en tiempo O(1) por ID o nombre."""
        return self.places_by_id.get(id_or_name) or self.places_by_name.get(id_or_name)

    def get_npc(self, id_or_name: str) -> Optional[NPC]:
        """Devuelve el NPC buscando en tiempo O(1) por ID o nombre."""
        return self.npcs.get(id_or_name) or self.npcs_by_name.get(id_or_name)

    def get_item(self, id_or_name: str) -> Optional[Item]:
        """Devuelve el Item buscando en tiempo O(1) por ID o nombre."""
        return self.items.get(id_or_name) or self.items_by_name.get(id_or_name)

    def get_location_for_place(self, place_id_or_name: str) -> Optional[Location]:
        """Devuelve la región (Location) que contiene a un Place en tiempo O(1)."""
        return self.place_to_location.get(place_id_or_name)


__all__ = ["WorldState"]
