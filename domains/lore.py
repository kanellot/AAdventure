"""Modelos de dominio para el sistema de Lore dinámico y Máquina de Estados Jerárquica (HSM)."""

from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field, model_validator


class LoreBlockState(str, Enum):
    """Estados del ciclo de vida de un LoreBlock."""

    UNKNOWN = "unknown"
    ACTIVE = "active"
    DONE = "done"


class EntityCondition(BaseModel):
    """Condición lógica basada en una entidad del juego (Place, NPC, Item, LoreBlock)."""

    entity_type: Literal["place", "npc", "item", "loreblock"]
    entity_id: str
    sub_condition: Literal["known", "current_location", "affinity", "have", "active", "done", "any_child_done"]
    value: Optional[Any] = None
    is_negated: bool = False


class EntityConditionsList(list):
    """Lista de EntityCondition que ofrece atributos retrocompatibles con LoreConditions."""

    @property
    def min_affinity(self) -> float:
        for c in self:
            if getattr(c, "entity_type", None) == "npc" and getattr(c, "sub_condition", None) == "affinity":
                return float(c.value or 0.0)
        return 0.0

    @property
    def max_affinity(self) -> float:
        return 1.0

    @property
    def required_quests(self) -> List[str]:
        return [
            c.entity_id
            for c in self
            if getattr(c, "entity_type", None) == "quest"
            or (getattr(c, "entity_type", None) == "loreblock" and getattr(c, "sub_condition", None) == "done")
        ]

    @property
    def required_items(self) -> List[str]:
        return [
            c.entity_id
            for c in self
            if getattr(c, "entity_type", None) == "item" and getattr(c, "sub_condition", None) == "have"
        ]

    @property
    def required_gold(self) -> int:
        for c in self:
            if getattr(c, "entity_type", None) == "gold":
                return int(c.value or 0)
        return 0


class LoreConditions(BaseModel):
    """Modelo legacy mantenido por compatibilidad de tipos y pruebas existentes."""

    min_affinity: float = 0.0
    max_affinity: float = 1.0
    required_quests: List[str] = Field(default_factory=list)
    required_items: List[str] = Field(default_factory=list)
    required_gold: int = 0


class LoreEffects(BaseModel):
    """Efectos o mutaciones aplicadas al estado del juego al activarse o completarse el lore."""

    give_items: List[str] = Field(default_factory=list)
    take_items: List[str] = Field(default_factory=list)
    give_gold: int = 0
    take_gold: int = 0
    gold_delta: int = 0
    affinity_delta: float = 0.0
    npc_affinity_deltas: Dict[str, float] = Field(default_factory=dict)
    unlock_quests: List[str] = Field(default_factory=list)
    unlock_places: List[str] = Field(default_factory=list)
    unlock_npcs: List[str] = Field(default_factory=list)
    unlock_items: List[str] = Field(default_factory=list)
    spawn_npcs: List[Dict[str, str]] = Field(default_factory=list)
    spawn_objects: List[Dict[str, str]] = Field(default_factory=list)
    trigger_action_type: Optional[str] = None
    trigger_action_target: Optional[str] = None


class LoreBlock(BaseModel):
    """Bloque de lore como máquina de estados jerárquica (HSM)."""

    id: str
    name: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    state: str = "unknown"
    rag_enabled: bool = True
    trigger_phrases: List[str] = Field(default_factory=list)
    trigger_mode: str = "reactive"
    conditions: List[EntityCondition] = Field(default_factory=list)
    repeatable: bool = False
    exit_conditions: List[EntityCondition] = Field(default_factory=list)
    exit_rag_enabled: bool = False
    exit_trigger_phrases: List[str] = Field(default_factory=list)
    effect_timing: str = "on_active"
    target_entities: List[str] = Field(default_factory=list)
    parent_id: Optional[str] = None
    directive: str = ""
    effects: LoreEffects = Field(default_factory=LoreEffects)

    @property
    def is_root(self) -> bool:
        """Indica si el bloque es raíz (no tiene bloque padre contenedor)."""
        return not bool(self.parent_id and str(self.parent_id).strip())

    @model_validator(mode="before")
    @classmethod
    def _migrate_legacy_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        # Copiar diccionario para no mutar el original
        d = dict(data)

        # Sincronizar title y name
        if "title" in d and "name" not in d:
            d["name"] = d["title"]
        elif "name" in d and "title" not in d:
            d["title"] = d["name"]

        # Migrar content -> directive
        if "content" in d and "directive" not in d:
            d["directive"] = d.pop("content")

        # Migrar once -> repeatable
        if "once" in d and "repeatable" not in d:
            d["repeatable"] = not bool(d.get("once"))

        # Migrar revealed -> state
        if "revealed" in d and "state" not in d:
            d["state"] = "done" if d.get("revealed") else "unknown"

        # Migrar required_affinity y required_quests a nivel raíz si existían
        root_affinity = d.pop("required_affinity", None)
        root_quests = d.pop("required_quests", None)

        raw_conds = d.get("conditions")
        new_conds = []

        if isinstance(raw_conds, list):
            new_conds.extend(raw_conds)
        elif isinstance(raw_conds, (dict, LoreConditions)):
            cond_dict = raw_conds if isinstance(raw_conds, dict) else raw_conds.model_dump()
            min_aff = cond_dict.get("min_affinity", 0.0)
            if min_aff > 0.0:
                new_conds.append(
                    {"entity_type": "npc", "entity_id": "", "sub_condition": "affinity", "value": min_aff}
                )
            for it in cond_dict.get("required_items", []):
                new_conds.append(
                    {"entity_type": "item", "entity_id": it, "sub_condition": "have"}
                )
            for q in cond_dict.get("required_quests", []):
                new_conds.append(
                    {"entity_type": "loreblock", "entity_id": q, "sub_condition": "done"}
                )
            if cond_dict.get("required_gold", 0) > 0:
                new_conds.append(
                    {"entity_type": "item", "entity_id": "gold", "sub_condition": "have", "value": cond_dict.get("required_gold")}
                )

        if root_affinity is not None and float(root_affinity) > 0.0:
            new_conds.append(
                {"entity_type": "npc", "entity_id": "", "sub_condition": "affinity", "value": float(root_affinity)}
            )
        if root_quests:
            for q in root_quests:
                new_conds.append(
                    {"entity_type": "loreblock", "entity_id": q, "sub_condition": "done"}
                )

        d["conditions"] = new_conds
        if "target_entities" not in d:
            d["target_entities"] = []
        if "parent_id" not in d or d["parent_id"] is None:
            d["parent_id"] = None
        else:
            p_val = str(d["parent_id"]).strip()
            d["parent_id"] = p_val if p_val else None
        return d

    @model_validator(mode="after")
    def _wrap_conditions_list(self) -> "LoreBlock":
        if not isinstance(self.conditions, EntityConditionsList):
            self.conditions = EntityConditionsList(self.conditions)
        if not isinstance(self.exit_conditions, EntityConditionsList):
            self.exit_conditions = EntityConditionsList(self.exit_conditions)
        # Sincronización automática de trigger_mode según rag_enabled
        self.trigger_mode = "reactive" if self.rag_enabled else "proactive"
        return self

    @property
    def once(self) -> bool:
        return not self.repeatable

    @once.setter
    def once(self, val: bool) -> None:
        self.repeatable = not val

    @property
    def revealed(self) -> bool:
        return self.state == "done"

    @revealed.setter
    def revealed(self, val: bool) -> None:
        self.state = "done" if val else "unknown"
