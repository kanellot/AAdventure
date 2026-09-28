"""Modelos de dominio para el sistema de Lore dinámico y Máquina de Estados Jerárquica (HSM)."""

from enum import Enum
from typing import Any, List, Literal, Optional
from pydantic import BaseModel, Field, model_validator


class LoreBlockState(str, Enum):
    """Estados del ciclo de vida de un LoreBlock."""

    UNKNOWN = "unknown"
    ACTIVE = "active"
    DONE = "done"


LoreBlockType = Literal["Chapter", "Quest", "Task", "Event", "popup"]

EntityConditionType = Literal["place", "npc", "item", "loreblock", "gold", "time"]

SubCondition = Literal[
    "current_location",
    "visited",
    "visible",
    "known",
    "talk",
    "affinity",
    "affinity_range",
    "have",
    "active",
    "done",
    "all_children_done",
    "any_child_done",
    "time_range",
]

ActionType = Literal["hook", "push"]


class EntityCondition(BaseModel):
    """Condición lógica basada en una entidad del juego o dimensión del sistema."""

    entity_type: EntityConditionType
    entity_id: str = ""
    sub_condition: SubCondition
    value: Optional[Any] = None
    is_negated: bool = False


class ConditionGroup(BaseModel):
    """Grupo de condiciones evaluadas en conjunción (AND) junto con antenas RAG."""

    rag_enabled: bool = False
    trigger_phrases: List[str] = Field(default_factory=list)
    conditions: List[EntityCondition] = Field(default_factory=list)


class LoreEffects(BaseModel):
    """Efectos o mutaciones aplicadas al estado del juego al activarse el lore."""

    target: Optional[str] = None
    action: ActionType = "hook"
    elapsed_time: str = "00:00"
    directive: str = ""
    bypass_llm: bool = False

    gold_delta: int = 0
    affinity_delta: float = 0.0

    give_items: List[str] = Field(default_factory=list)
    take_items: List[str] = Field(default_factory=list)

    unlock_places: List[str] = Field(default_factory=list)
    unlock_npcs: List[str] = Field(default_factory=list)
    unlock_items: List[str] = Field(default_factory=list)

    block_places: List[str] = Field(default_factory=list)
    unblock_places: List[str] = Field(default_factory=list)


class LoreBlock(BaseModel):
    """Bloque de lore como máquina de estados jerárquica (HSM)."""

    id: str
    name: str
    title: str = ""
    description: Optional[str] = ""
    type: LoreBlockType = "Event"
    parent_id: Optional[str] = None
    state: str = LoreBlockState.UNKNOWN.value

    active_conditions: List[ConditionGroup] = Field(default_factory=list)
    done_conditions: List[ConditionGroup] = Field(default_factory=list)
    effects: List[LoreEffects] = Field(default_factory=list)

    @property
    def is_root(self) -> bool:
        """Indica si el bloque es raíz (no tiene bloque padre contenedor)."""
        return not bool(self.parent_id and str(self.parent_id).strip())

    @model_validator(mode="before")
    @classmethod
    def _sync_name_title(cls, data: Any) -> Any:
        """Sincroniza name y title de forma simétrica."""
        if isinstance(data, dict):
            d = dict(data)
            if not d.get("title") and d.get("name"):
                d["title"] = d["name"]
            elif not d.get("name") and d.get("title"):
                d["name"] = d["title"]
            elif not d.get("name") and not d.get("title") and d.get("id"):
                d["name"] = d.get("id")
                d["title"] = d.get("id")
            return d
        return data


__all__ = [
    "LoreBlockState",
    "LoreBlockType",
    "EntityConditionType",
    "SubCondition",
    "ActionType",
    "EntityCondition",
    "ConditionGroup",
    "LoreEffects",
    "LoreBlock",
]
