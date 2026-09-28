"""Controlador del estado activo de juego (GameState) y persistencia canónica."""

from __future__ import annotations
import os
from typing import Any, Dict, List, Literal, Optional
from domains.game_state import (
    EntityMapItem,
    EntityMapLocation,
    EntityMapNPC,
    EntityMapPlace,
    GameState,
    Inventory,
    LoreBlockHierarchy,
    NotebookEntry,
)
from domains.items import Item
from domains.npcs import NPC
from domains.player import Player
from domains.world import Place, World


class GameStateController:
    """Gestiona el estado activo de la partida (GameState), mutaciones y persistencia."""

    def __init__(
        self,
        game_state: GameState,
        world: Optional[World] = None,
        npcs: Optional[List[NPC]] = None,
        items: Optional[List[Item]] = None,
        adventure_path: Optional[str] = None,
        fog_war_enabled: bool = True,
    ):
        self.game_state = game_state
        self.world = world
        self.adventure_path = adventure_path
        self.fog_war_enabled = fog_war_enabled

        # Catálogos de consulta O(1)
        self.npcs_by_id: Dict[str, NPC] = {n.id: n for n in (npcs or [])}
        self.items_by_id: Dict[str, Item] = {i.id: i for i in (items or [])}
        self.places_by_id: Dict[str, Place] = {}
        self.places_by_name: Dict[str, Place] = {}
        if world:
            for loc in world.locations:
                for p in loc.places:
                    self.places_by_id[p.id] = p
                    self.places_by_name[p.name] = p

        # Asegurar que el objeto place esté sincronizado con current_location
        if self.world and not self.game_state.place and self.game_state.current_location:
            self.game_state.place = self.places_by_id.get(self.game_state.current_location)

    @classmethod
    def create_initial(
        cls,
        world: World,
        player: Player,
        npcs: Optional[List[NPC]] = None,
        items: Optional[List[Item]] = None,
        loreblocks_hierarchy: Optional[LoreBlockHierarchy] = None,
        adventure_path: Optional[str] = None,
        elapsed_time_enabled: bool = True,
        fog_war_enabled: bool = True,
    ) -> GameStateController:
        """Inicializa GameStateController a partir de las entidades de la historia."""
        all_npcs = npcs or []
        all_items = items or []
        start_location = player.initial_location or ""

        # Construir mapa jerárquico por Location
        places_by_id: Dict[str, Place] = {}
        for loc in world.locations:
            for p in loc.places:
                places_by_id[p.id] = p

        places_by_name = {p.name: p for p in places_by_id.values()}
        if start_location in places_by_name:
            start_location = places_by_name[start_location].id

        for npc in all_npcs:
            loc_val = getattr(npc, "initial_location", None)
            if loc_val in places_by_name:
                npc.initial_location = places_by_name[loc_val].id

        for it in all_items:
            loc_val = getattr(it, "initial_location", None)
            if loc_val in places_by_name:
                it.initial_location = places_by_name[loc_val].id

        initial_place = places_by_id.get(start_location)
        connected_ids = set()
        if initial_place:
            for k, conn in initial_place.connections.items():
                target = getattr(conn, "target", k) if hasattr(conn, "target") else (conn.get("target", k) if isinstance(conn, dict) else k)
                if target in places_by_name:
                    connected_ids.add(places_by_name[target].id)
                else:
                    connected_ids.add(target)
                connected_ids.add(k)

        entity_map: List[EntityMapLocation] = []
        for loc in world.locations:
            places_dto: List[EntityMapPlace] = []
            for p in loc.places:
                # Niebla de guerra inicial
                if p.id == start_location:
                    status = "visited"
                elif not fog_war_enabled or p.id in connected_ids:
                    status = "visible"
                else:
                    status = "hidden"

                # Entidades presentes en este lugar
                place_items: List[EntityMapItem] = []
                for it in all_items:
                    if getattr(it, "initial_location", None) == p.id:
                        place_items.append(
                            EntityMapItem(
                                id=it.id,
                                name=it.name,
                                visible=(status == "visited"),
                            )
                        )

                place_npcs: List[EntityMapNPC] = []
                for npc in all_npcs:
                    if getattr(npc, "initial_location", None) == p.id:
                        place_npcs.append(
                            EntityMapNPC(
                                id=npc.id,
                                name=npc.name,
                                status="visible" if status == "visited" else "visible",
                                affinity=getattr(npc, "affinity", 0.5),
                            )
                        )

                places_dto.append(
                    EntityMapPlace(
                        id=p.id,
                        name=p.name,
                        status=status,
                        items=place_items,
                        npcs=place_npcs,
                    )
                )

            entity_map.append(
                EntityMapLocation(
                    id=loc.id,
                    name=loc.name,
                    places=places_dto,
                )
            )

        # Cuaderno de misiones iniciales
        notebook: List[NotebookEntry] = []
        hierarchy = loreblocks_hierarchy or LoreBlockHierarchy()
        for cat in ("active", "done"):
            for blk in hierarchy.get(cat, []):
                if blk.get("type") == "Quest":
                    notebook.append(
                        NotebookEntry(
                            id=blk.get("id", ""),
                            name=blk.get("name", ""),
                            description=blk.get("description", ""),
                            status=cat,
                        )
                    )

        initial_time = "Día 1, 08:00" if elapsed_time_enabled else None
        inventory = Inventory(items=list(player.inventory), gold=player.gold)

        state = GameState(
            player_name=player.name,
            player_state="EXPLORE",
            player_target=None,
            current_location=start_location,
            current_time=initial_time,
            inventory=inventory,
            place=initial_place,
            entity_map=entity_map,
            loreblocks=hierarchy,
            notebook=notebook,
            conversations={},
        )

        return cls(
            game_state=state,
            world=world,
            npcs=all_npcs,
            items=all_items,
            adventure_path=adventure_path,
            fog_war_enabled=fog_war_enabled,
        )

    @classmethod
    def from_aad(cls, aad_path: str) -> GameStateController:
        """Carga e inicializa el controlador a partir de un paquete .aad o directorio."""
        import json
        import shutil
        from adventure_packager import AdventurePackager
        from domains.story_config import StoryConfig

        if not os.path.exists(aad_path):
            raise FileNotFoundError(f"No se encontró el archivo de aventura: {aad_path}")

        temp_dir = None
        if os.path.isfile(aad_path):
            work_dir = AdventurePackager.unpack_to_temp(aad_path)
            temp_dir = work_dir
        else:
            work_dir = aad_path

        try:
            with open(os.path.join(work_dir, "world.json"), "r", encoding="utf-8") as f:
                raw_world = json.load(f)
            world_data = raw_world.get("world", raw_world)
            world = World.model_validate(world_data)

            with open(os.path.join(work_dir, "player.json"), "r", encoding="utf-8") as f:
                raw_player = json.load(f)
            player_data = raw_player.get("player", raw_player)
            player = Player.model_validate(player_data)

            npcs = []
            npcs_file = os.path.join(work_dir, "npcs.json")
            if os.path.exists(npcs_file):
                with open(npcs_file, "r", encoding="utf-8") as f:
                    raw_npcs = json.load(f)
                npcs = [NPC.model_validate(n) for n in raw_npcs.get("npcs", [])]

            items = []
            items_file = os.path.join(work_dir, "items.json")
            if os.path.exists(items_file):
                with open(items_file, "r", encoding="utf-8") as f:
                    raw_items = json.load(f)
                items = [Item.model_validate(i) for i in raw_items.get("items", [])]

            hierarchy = LoreBlockHierarchy()
            lore_file = os.path.join(work_dir, "loreblocks.json")
            if os.path.exists(lore_file):
                with open(lore_file, "r", encoding="utf-8") as f:
                    raw_lore = json.load(f)
                blocks = raw_lore.get("lore_blocks", [])
                active_ids = {b.get("id") for b in blocks if b.get("state") == "active"}
                changed = True
                while changed:
                    changed = False
                    for b in blocks:
                        bid = b.get("id")
                        if bid in active_ids or b.get("type") == "popup":
                            continue
                        has_active_conds = any(
                            bool(grp.get("conditions") or (grp.get("rag_enabled") and grp.get("trigger_phrases")))
                            for grp in b.get("active_conditions", [])
                            if isinstance(grp, dict)
                        )
                        if not has_active_conds:
                            pid = b.get("parent_id")
                            if not pid or pid in active_ids:
                                active_ids.add(bid)
                                changed = True

                active_list = []
                unknown_list = []
                for b in blocks:
                    if b.get("id") in active_ids:
                        b["state"] = "active"
                        active_list.append(b)
                    else:
                        b["state"] = "unknown"
                        unknown_list.append(b)

                hierarchy = LoreBlockHierarchy(active=active_list, done=[], unknown=unknown_list)

            elapsed_time_enabled = True
            fog_war_enabled = True
            config_file = os.path.join(work_dir, "story_config.json")
            if os.path.exists(config_file):
                with open(config_file, "r", encoding="utf-8") as f:
                    cfg_data = json.load(f)
                elapsed_time_enabled = cfg_data.get("elapsed_time", True)
                fog_war_enabled = cfg_data.get("fog_war", True)

            return cls.create_initial(
                world=world,
                player=player,
                npcs=npcs,
                items=items,
                loreblocks_hierarchy=hierarchy,
                adventure_path=aad_path,
                elapsed_time_enabled=elapsed_time_enabled,
                fog_war_enabled=fog_war_enabled,
            )
        finally:
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)

    # =========================================================================
    # Métodos de Mutación Atómica de Estado
    # =========================================================================

    def set_player_state(self, state: Literal["EXPLORE", "TALK", "LOOK"]) -> None:
        """Actualiza el modo o estado del jugador."""
        self.game_state.player_state = state

    def set_player_target(self, target_id: Optional[str]) -> None:
        """Actualiza el objetivo activo del jugador."""
        self.game_state.player_target = target_id

    def set_current_location(self, place_id: str) -> None:
        """Actualiza la posición espacial del jugador y sincroniza lugar y niebla de guerra."""
        self.game_state.current_location = place_id
        target_place = self.places_by_id.get(place_id)
        if target_place:
            self.game_state.place = target_place
        self.reveal_place_and_neighbors(place_id)

    def reveal_place_and_neighbors(self, visited_place_id: str) -> None:
        """Aplica las reglas de niebla de guerra para el lugar visitado y colindantes."""
        target_place = self.places_by_id.get(visited_place_id)
        connected_ids = set()
        if target_place:
            for k, conn in target_place.connections.items():
                target = getattr(conn, "target", k) if hasattr(conn, "target") else (conn.get("target", k) if isinstance(conn, dict) else k)
                if target in self.places_by_name:
                    connected_ids.add(self.places_by_name[target].id)
                else:
                    connected_ids.add(target)
                connected_ids.add(k)

        for loc in self.game_state.entity_map:
            for p in loc.places:
                if p.id == visited_place_id:
                    p.status = "visited"
                    for item in p.items:
                        item.visible = True
                    for npc in p.npcs:
                        npc.status = "visible"
                elif (not self.fog_war_enabled or p.id in connected_ids) and p.status == "hidden":
                    p.status = "visible"

    def add_to_inventory(self, item_id: str) -> None:
        """Añade un ítem al inventario y lo retira del mapa si estuviera en un lugar."""
        self.game_state.inventory.append(item_id)
        for loc in self.game_state.entity_map:
            for p in loc.places:
                p.items = [it for it in p.items if it.id != item_id]

    def remove_from_inventory(self, item_id: str) -> None:
        """Elimina un ítem del inventario."""
        self.game_state.inventory.remove(item_id)

    def add_gold(self, amount: int) -> None:
        """Incrementa el oro del jugador."""
        self.game_state.inventory.gold += max(0, amount)

    def remove_gold(self, amount: int) -> None:
        """Reduce el oro del jugador sin permitir valores negativos."""
        self.game_state.inventory.gold = max(0, self.game_state.inventory.gold - amount)

    def block_place(self, place_id: str) -> None:
        """Bloquea el acceso a un lugar."""
        p = self.places_by_id.get(place_id)
        if p:
            p.blocked_place = True
        if self.game_state.place and self.game_state.place.id == place_id:
            self.game_state.place.blocked_place = True

    def unblock_place(self, place_id: str) -> None:
        """Desbloquea el acceso a un lugar."""
        p = self.places_by_id.get(place_id)
        if p:
            p.blocked_place = False
        if self.game_state.place and self.game_state.place.id == place_id:
            self.game_state.place.blocked_place = False

    def is_place_blocked(self, place_id: str) -> bool:
        """Indica si un lugar se encuentra físicamente bloqueado."""
        p = self.places_by_id.get(place_id)
        return p.blocked_place if p else False

    def update_npc_affinity(self, npc_id: str, new_affinity: float) -> None:
        """Actualiza la afinidad viva de un NPC en el mapa."""
        clamped = max(0.0, min(1.0, new_affinity))
        for loc in self.game_state.entity_map:
            for p in loc.places:
                for npc in p.npcs:
                    if npc.id == npc_id:
                        npc.affinity = clamped
                        return

    def get_npc_affinity(self, npc_id: str) -> float:
        """Obtiene la afinidad actual de un NPC."""
        for loc in self.game_state.entity_map:
            for p in loc.places:
                for npc in p.npcs:
                    if npc.id == npc_id:
                        return npc.affinity
        return 0.5

    def get_conversation(self, target_id: str) -> List[Dict[str, str]]:
        """Recupera el historial de mensajes para un target de conversación."""
        return self.game_state.conversations.get(target_id, [])

    def append_dialogue_exchange(
        self,
        target_id: str,
        player_msg: str,
        npc_name: str,
        npc_msg: str,
        max_messages: int = 16,
    ) -> None:
        """Registra un par de diálogo en el historial y mantiene la ventana deslizante."""
        if target_id not in self.game_state.conversations:
            self.game_state.conversations[target_id] = []

        history = self.game_state.conversations[target_id]
        if player_msg:
            history.append({"player": player_msg})
        if npc_msg:
            history.append({npc_name: npc_msg})

        if len(history) > max_messages:
            self.game_state.conversations[target_id] = history[-max_messages:]

    def add_elapsed_minutes(self, minutes: int) -> None:
        """Avanza los minutos transcurridos de juego y actualiza current_time."""
        if not self.game_state.current_time or minutes <= 0:
            return
        total = self._parse_elapsed_minutes(self.game_state.current_time) + minutes
        self.game_state.current_time = self._format_elapsed_time(total)

    def sync_notebook(self) -> None:
        """Sincroniza las misiones del cuaderno a partir de los LoreBlocks activos y completados."""
        quests: List[NotebookEntry] = []
        for cat in ("active", "done"):
            for blk in self.game_state.loreblocks.get(cat, []):
                if blk.get("type") == "Quest":
                    quests.append(
                        NotebookEntry(
                            id=blk.get("id", ""),
                            name=blk.get("name", ""),
                            description=blk.get("description", ""),
                            status=cat,
                        )
                    )
        self.game_state.notebook = quests

    # =========================================================================
    # Persistencia Canónica Pura (JSON)
    # =========================================================================

    @property
    def saves_directory(self) -> str:
        """Directorio base de partidas guardadas."""
        if not self.adventure_path:
            return "saves"
        base = os.path.dirname(self.adventure_path) if os.path.isfile(self.adventure_path) else self.adventure_path
        return os.path.join(base, "saves")

    def save(self, filepath: Optional[str] = None) -> str:
        """Serializa el GameState canónico a disco en formato JSON."""
        if not filepath:
            target_path = os.path.join(self.saves_directory, "savegame.json")
        elif not os.path.dirname(filepath):
            slot_name = filepath if filepath.endswith(".json") else f"{filepath}.json"
            target_path = os.path.join(self.saves_directory, slot_name)
        else:
            target_path = filepath

        dir_name = os.path.dirname(target_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(self.game_state.model_dump_json(indent=2))

        return target_path

    def load(self, filepath: str) -> GameState:
        """Carga y valida un GameState previamente guardado."""
        target_path = filepath
        if not os.path.exists(target_path):
            alt_path = os.path.join(self.saves_directory, filepath if filepath.endswith(".json") else f"{filepath}.json")
            if os.path.exists(alt_path):
                target_path = alt_path
            else:
                raise FileNotFoundError(f"Archivo de partida guardada no encontrado: {filepath}")

        with open(target_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.game_state = GameState.model_validate_json(content)
        if self.world and self.game_state.current_location:
            self.game_state.place = self.places_by_id.get(self.game_state.current_location)

        return self.game_state

    # =========================================================================
    # Utilidades de Conversión de Tiempo
    # =========================================================================

    @staticmethod
    def _parse_elapsed_minutes(formatted: str) -> int:
        try:
            parts = formatted.split(",")
            day = int(parts[0].replace("Día", "").strip())
            h, m = map(int, parts[1].strip().split(":"))
            return (day - 1) * 1440 + h * 60 + m
        except Exception:
            return 0

    @staticmethod
    def _format_elapsed_time(total_minutes: int) -> str:
        days = (total_minutes // 1440) + 1
        hours = (total_minutes // 60) % 24
        mins = total_minutes % 60
        return f"Día {days}, {hours:02d}:{mins:02d}"
