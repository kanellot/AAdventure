"""Modelos de dominio para el sistema de Lore dinámico y Máquina de Estados Jerárquica (HSM)."""

from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, model_validator


class LoreBlockState(str, Enum):
    """Estados del ciclo de vida de un LoreBlock."""

    UNKNOWN = "unknown"
    ACTIVE = "active"
    DONE = "done"


class EntityCondition(BaseModel):
    """Condición lógica basada en una entidad del juego (Place, NPC, Item, LoreBlock, Gold)."""

    entity_type: Literal["place", "npc", "item", "loreblock", "gold"]
    entity_id: str
    sub_condition: Literal[
        "known",
        "current_location",
        "visited",
        "unlocked",
        "affinity",
        "have",
        "active",
        "done",
        "any_child_done",
        "talk",
    ]
    value: Optional[Any] = None
    is_negated: bool = False


class LoreEffects(BaseModel):
    """Efectos o mutaciones aplicadas al estado del juego al activarse o completarse el lore."""

    timing: Literal["active", "done"] = "active"
    target: Optional[str] = None
    directive: str = ""
    force_action: bool = False
    trigger_action_type: Optional[str] = None
    trigger_action_target: Optional[str] = None

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
    block_connections: List[str] = Field(default_factory=list)
    allow_connections: List[str] = Field(default_factory=list)


class LoreBlock(BaseModel):
    """Bloque de lore como máquina de estados jerárquica (HSM)."""

    id: str
    name: str
    description: Optional[str] = None
    state: str = "unknown"
    parent_id: Optional[str] = None
    trigger_mode: str = "proactive"
    rag_enabled: bool = False
    trigger_phrases: List[str] = Field(default_factory=list)
    conditions: List[EntityCondition] = Field(default_factory=list)
    exit_conditions: List[EntityCondition] = Field(default_factory=list)
    exit_rag_enabled: bool = False
    exit_trigger_phrases: List[str] = Field(default_factory=list)
    effects: List[LoreEffects] = Field(default_factory=list)

    @property
    def is_root(self) -> bool:
        """Indica si el bloque es raíz (no tiene bloque padre contenedor)."""
        return not bool(self.parent_id and str(self.parent_id).strip())

    @property
    def title(self) -> str:
        return self.name

    @title.setter
    def title(self, val: str) -> None:
        self.name = val

    @property
    def on_active(self) -> LoreEffects:
        """Devuelve el primer efecto de timing 'active' o añade uno por defecto."""
        for eff in self.effects:
            if eff.timing == "active":
                return eff
        eff = LoreEffects(timing="active")
        self.effects.append(eff)
        return eff

    @property
    def on_done(self) -> LoreEffects:
        """Devuelve el primer efecto de timing 'done' o añade uno por defecto."""
        for eff in self.effects:
            if eff.timing == "done":
                return eff
        eff = LoreEffects(timing="done")
        self.effects.append(eff)
        return eff

    @property
    def directive(self) -> str:
        """Obtiene la directiva general del bloque delegando en sus efectos."""
        return self.get_directive_for_entity() or ""

    @property
    def force_action(self) -> bool:
        return any(eff.force_action for eff in self.effects)

    @model_validator(mode="before")
    @classmethod
    def _normalize_loreblock(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        d = dict(data)

        # Sincronizar title y name
        if "title" in d and "name" not in d:
            d["name"] = d["title"]
        elif "name" in d and "title" not in d:
            d["title"] = d["name"]
        if not d.get("name"):
            d["name"] = d.get("id", "")

        # Normalizar effects si viene como dict único
        raw_effects = d.get("effects")
        if isinstance(raw_effects, dict):
            d["effects"] = [raw_effects]
        elif raw_effects is None:
            d["effects"] = []

        # RAG y trigger_mode
        if d.get("trigger_phrases") and not d.get("rag_enabled"):
            d["rag_enabled"] = True
        if d.get("rag_enabled"):
            d["trigger_mode"] = "reactive"
        elif "trigger_mode" not in d:
            d["trigger_mode"] = "proactive"

        # Parent ID
        if "parent_id" in d and d["parent_id"] is not None:
            p_str = str(d["parent_id"]).strip()
            d["parent_id"] = p_str if p_str else None

        return d

    def get_effects_for_timing(self, timing: str) -> List[LoreEffects]:
        """Devuelve todos los efectos asociados a un momento de activación (active o done)."""
        clean_timing = "active" if timing in ("active", "on_active") else "done"
        return [eff for eff in self.effects if eff.timing == clean_timing]

    def get_effect_for_entity(self, entity_id_or_name: str, timing: Optional[str] = None) -> Optional[LoreEffects]:
        """Devuelve el efecto configurado específicamente para una entidad."""
        t_clean = str(entity_id_or_name).strip().lower()
        clean_timing = (
            "active"
            if timing in ("active", "on_active")
            else ("done" if timing in ("done", "on_done") else None)
        )
        for eff in self.effects:
            if (eff.target or "").strip().lower() == t_clean:
                if clean_timing and eff.timing != clean_timing:
                    continue
                return eff
        return None

    def get_directive_for_entity(
        self,
        entity_id_or_name: Optional[str] = None,
        timing: Optional[str] = None,
    ) -> Optional[str]:
        """Obtiene la directiva adecuada considerando la entidad objetivo y el momento (active/done)."""
        clean_timing = (
            "active"
            if timing in ("active", "on_active")
            else ("done" if timing in ("done", "on_done") else None)
        )
        if entity_id_or_name:
            t_clean = str(entity_id_or_name).strip().lower()
            for eff in self.effects:
                if (eff.target or "").strip().lower() == t_clean:
                    if clean_timing and eff.timing != clean_timing:
                        continue
                    if eff.directive:
                        return eff.directive

        for eff in self.effects:
            if not eff.target and (clean_timing is None or eff.timing == clean_timing) and eff.directive:
                return eff.directive

        for eff in self.effects:
            if eff.directive:
                return eff.directive

        return None
