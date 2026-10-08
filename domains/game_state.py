"""Modelo de dominio canónico para GameState y sus componentes."""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

from domains.world import Place


class EntityMapItem(BaseModel):
    """Representa un ítem presente en un lugar dentro del entity_map."""

    id: str
    name: str = ""
    visible: bool = True


class EntityMapNPC(BaseModel):
    """Representa un NPC presente en un lugar dentro del entity_map."""

    id: str
    name: str = ""
    status: Literal["visible", "Known"] = "visible"
    affinity: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Afinidad dinámica activa del NPC con el jugador (0.0 a 1.0)",
    )


class EntityMapPlace(BaseModel):
    """Representa un lugar y sus entidades contenidas en el entity_map."""

    id: str
    name: str = ""
    status: Literal["visited", "visible", "hidden"] = "visible"
    items: List[EntityMapItem] = Field(default_factory=list)
    npcs: List[EntityMapNPC] = Field(default_factory=list)


class EntityMapLocation(BaseModel):
    """Representa una localización mayor que agrupa lugares y sus entidades en el mapa."""

    id: str = ""
    name: str = ""
    places: List[EntityMapPlace] = Field(default_factory=list)


class LoreBlockHierarchy(BaseModel):
    """Estructura jerárquica de LoreBlocks organizada en 4 categorías: unknown, active, done, popups."""

    unknown: List[Dict[str, Any]] = Field(default_factory=list)
    active: List[Dict[str, Any]] = Field(default_factory=list)
    done: List[Dict[str, Any]] = Field(default_factory=list)
    popups: List[Dict[str, Any]] = Field(default_factory=list)

    def __getitem__(self, item: str) -> List[Dict[str, Any]]:
        if hasattr(self, item):
            return getattr(self, item)
        raise KeyError(f"Categoría de loreblock no válida: {item}")

    def __setitem__(self, key: str, value: List[Dict[str, Any]]) -> None:
        if key in ("unknown", "active", "done", "popups"):
            setattr(self, key, value)
        else:
            raise KeyError(f"Categoría de loreblock no válida: {key}")

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def items(self):
        return [
            ("unknown", self.unknown),
            ("active", self.active),
            ("done", self.done),
            ("popups", self.popups),
        ]

    def keys(self):
        return ["unknown", "active", "done", "popups"]

    def values(self):
        return [self.unknown, self.active, self.done, self.popups]

    def __contains__(self, key: str) -> bool:
        return key in ("unknown", "active", "done", "popups")


class Inventory(BaseModel):
    """Estructura de inventario que encapsula los ítems en posesión y el oro del jugador."""

    items: List[str] = Field(default_factory=list, description="Lista de IDs de ítems en el inventario")
    gold: int = Field(default=0, ge=0, description="Cantidad de monedas de oro del jugador")

    def __iter__(self):
        return iter(self.items)

    def __len__(self):
        return len(self.items)

    def __contains__(self, item: Any) -> bool:
        return item in self.items

    def __getitem__(self, index: Any) -> Any:
        return self.items[index]

    def append(self, item: str) -> None:
        self.items.append(item)

    def remove(self, item: str) -> None:
        self.items.remove(item)

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, list):
            return self.items == other and self.gold == 0
        if isinstance(other, Inventory):
            return self.items == other.items and self.gold == other.gold
        return super().__eq__(other)


class NotebookEntry(BaseModel):
    """Entrada en el cuaderno de misiones (quest activas y done)."""

    id: str
    name: str = ""
    description: str = ""
    status: Optional[str] = Field(
        default=None,
        description="Estado de la quest: 'active' o 'done'",
    )


class GameState(BaseModel):
    """Estado activo del juego y de la partida según el nuevo formato de dominio estándar."""

    player_name: str = ""
    player_state: Literal["EXPLORE", "TALK", "LOOK"] = Field(
        default="EXPLORE",
        description="Estado del jugador EXPLORE/TALK/LOOK",
    )
    player_target: Optional[str] = Field(
        default=None,
        description="ID de la entidad objetivo (NPC en TALK, entidad en LOOK, None en EXPLORE)",
    )
    current_location: str = Field(
        default="",
        description="Place Id donde se encuentre el jugador",
    )
    current_time: Optional[str] = Field(
        default=None,
        description="Fecha y hora actual de la partida (None si elapsed time desactivado)",
    )
    inventory: Inventory = Field(
        default_factory=Inventory,
        description="Inventario del jugador con lista de ítems y oro",
    )
    place: Optional[Place] = Field(
        default=None,
        description="Entidad place completa para current_location",
    )
    entity_map: List[EntityMapLocation] = Field(
        default_factory=list,
        description="Mapa jerárquico estructurado por Location",
    )
    loreblocks: LoreBlockHierarchy = Field(
        default_factory=LoreBlockHierarchy,
        description="Lista jerárquica en forma de diccionario (unknown, active, done)",
    )
    notebook: List[NotebookEntry] = Field(
        default_factory=list,
        description="Lista de quest Activas y done con loreblock (id, name, description)",
    )
    conversations: Dict[str, List[Dict[str, str]]] = Field(
        default_factory=dict,
        description="Historial secuencial de mensajes por target de conversación",
    )

    @property
    def gold(self) -> int:
        return self.inventory.gold

    @gold.setter
    def gold(self, value: int) -> None:
        self.inventory.gold = max(0, value)

    @field_validator("inventory", mode="before")
    @classmethod
    def _normalize_inventory(cls, val: Any) -> Any:
        if val is None:
            return Inventory()
        if isinstance(val, Inventory):
            return val
        if isinstance(val, dict):
            items_raw = val.get("items", [])
            gold = int(val.get("gold", 0))
            items = []
            for item in items_raw:
                if hasattr(item, "id"):
                    items.append(str(item.id))
                elif isinstance(item, dict) and "id" in item:
                    items.append(str(item["id"]))
                else:
                    items.append(str(item))
            return Inventory(items=items, gold=gold)
        if isinstance(val, list):
            result = []
            for item in val:
                if hasattr(item, "id"):
                    result.append(str(item.id))
                elif isinstance(item, dict) and "id" in item:
                    result.append(str(item["id"]))
                else:
                    result.append(str(item))
            return Inventory(items=result, gold=0)
        return val

    @field_validator("loreblocks", mode="before")
    @classmethod
    def _normalize_loreblocks(cls, val: Any) -> Any:
        if val is None or val == []:
            return LoreBlockHierarchy()
        if isinstance(val, dict):
            return LoreBlockHierarchy(**val)
        return val
