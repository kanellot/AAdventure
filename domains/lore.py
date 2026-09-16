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
    sub_condition: Literal["known", "current_location", "affinity", "have", "active", "done", "any_child_done", "talk"]
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

    @model_validator(mode="before")
    @classmethod
    def _migrate_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "target_entity_id" in data and "target" not in data:
                data["target"] = data["target_entity_id"]
            if "player_gold_delta" in data and "gold_delta" not in data:
                data["gold_delta"] = data["player_gold_delta"]
        return data

    @property
    def target_entity_id(self) -> Optional[str]:
        return self.target

    @target_entity_id.setter
    def target_entity_id(self, val: Optional[str]) -> None:
        self.target = val

    @property
    def player_gold_delta(self) -> int:
        return self.gold_delta

    @player_gold_delta.setter
    def player_gold_delta(self, val: int) -> None:
        self.gold_delta = val


class LoreBlock(BaseModel):
    """Bloque de lore como máquina de estados jerárquica (HSM)."""

    id: str
    name: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    state: str = "unknown"
    rag_enabled: bool = False
    trigger_phrases: List[str] = Field(default_factory=list)
    trigger_mode: str = "proactive"
    conditions: List[EntityCondition] = Field(default_factory=list)
    exit_conditions: List[EntityCondition] = Field(default_factory=list)
    exit_rag_enabled: bool = False
    exit_trigger_phrases: List[str] = Field(default_factory=list)
    parent_id: Optional[str] = None

    effects: List[LoreEffects] = Field(default_factory=list)

    @property
    def is_root(self) -> bool:
        """Indica si el bloque es raíz (no tiene bloque padre contenedor)."""
        return not bool(self.parent_id and str(self.parent_id).strip())

    @model_validator(mode="before")
    @classmethod
    def _migrate_legacy_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        d = dict(data)

        # Sincronizar title y name
        if "title" in d and "name" not in d:
            d["name"] = d["title"]
        elif "name" in d and "title" not in d:
            d["title"] = d["name"]

        # Migrar content -> directive
        legacy_dir = d.pop("content", None) or d.get("directive", "")

        # Migrar once / repeatable
        d.pop("once", None)
        d.pop("repeatable", None)

        # Migrar revealed -> state
        if "revealed" in d and "state" not in d:
            d["state"] = "done" if d.get("revealed") else "unknown"

        # Migrar efectos heredados (effects, on_active, on_done)
        raw_effects = d.pop("effects", None)
        raw_active = d.pop("on_active", None)
        raw_done = d.pop("on_done", None)
        timing = d.pop("effect_timing", "on_active")
        clean_timing = "active" if timing in ("active", "on_active") else "done"
        force_act = d.pop("force_action", False)
        target_ents = d.get("target_entities", [])

        effects_list = []

        if isinstance(raw_effects, list):
            for item in raw_effects:
                eff_dict = item if isinstance(item, dict) else (item.model_dump() if hasattr(item, "model_dump") else dict(item))
                if "timing" not in eff_dict:
                    eff_dict["timing"] = "active"
                elif eff_dict["timing"] in ("on_active", "active"):
                    eff_dict["timing"] = "active"
                elif eff_dict["timing"] in ("on_done", "done"):
                    eff_dict["timing"] = "done"
                effects_list.append(eff_dict)
        elif raw_effects is not None:
            eff_dict = raw_effects if isinstance(raw_effects, dict) else (raw_effects.model_dump() if hasattr(raw_effects, "model_dump") else dict(raw_effects))
            eff_dict["timing"] = clean_timing
            if legacy_dir and not eff_dict.get("directive"):
                eff_dict["directive"] = legacy_dir
            if target_ents and not eff_dict.get("target"):
                eff_dict["target"] = target_ents[0]
            if force_act and not eff_dict.get("force_action"):
                eff_dict["force_action"] = True
            effects_list.append(eff_dict)

        def _is_effect_meaningful(e_data: dict) -> bool:
            return bool(
                e_data.get("target")
                or e_data.get("directive")
                or e_data.get("force_action")
                or e_data.get("trigger_action_type")
                or e_data.get("trigger_action_target")
                or e_data.get("give_items")
                or e_data.get("take_items")
                or e_data.get("give_gold")
                or e_data.get("take_gold")
                or e_data.get("gold_delta")
                or e_data.get("affinity_delta")
                or e_data.get("npc_affinity_deltas")
                or e_data.get("unlock_quests")
                or e_data.get("unlock_places")
                or e_data.get("unlock_npcs")
                or e_data.get("unlock_items")
                or e_data.get("spawn_npcs")
                or e_data.get("spawn_objects")
                or e_data.get("block_connections")
                or e_data.get("allow_connections")
            )

        if raw_active is not None:
            act_dict = raw_active if isinstance(raw_active, dict) else (raw_active.model_dump() if hasattr(raw_active, "model_dump") else dict(raw_active))
            act_dict["timing"] = "active"
            if legacy_dir and clean_timing == "active" and not act_dict.get("directive"):
                act_dict["directive"] = legacy_dir
            if target_ents and not act_dict.get("target"):
                act_dict["target"] = target_ents[0]
            if force_act and clean_timing == "active" and not act_dict.get("force_action"):
                act_dict["force_action"] = True
            if _is_effect_meaningful(act_dict) or not effects_list:
                effects_list.append(act_dict)

        if raw_done is not None:
            don_dict = raw_done if isinstance(raw_done, dict) else (raw_done.model_dump() if hasattr(raw_done, "model_dump") else dict(raw_done))
            don_dict["timing"] = "done"
            if legacy_dir and clean_timing == "done" and not don_dict.get("directive"):
                don_dict["directive"] = legacy_dir
            if target_ents and clean_timing == "done" and not don_dict.get("target"):
                don_dict["target"] = target_ents[0]
            if force_act and clean_timing == "done" and not don_dict.get("force_action"):
                don_dict["force_action"] = True
            if _is_effect_meaningful(don_dict):
                effects_list.append(don_dict)

        if not effects_list and (legacy_dir or target_ents or force_act):
            eff = {
                "timing": clean_timing,
                "directive": legacy_dir,
                "target": target_ents[0] if target_ents else None,
                "force_action": bool(force_act),
            }
            effects_list.append(eff)

        d["effects"] = effects_list

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
        if "parent_id" not in d or d["parent_id"] is None:
            d["parent_id"] = None
        else:
            p_val = str(d["parent_id"]).strip()
        if "rag_enabled" not in d:
            if d.get("trigger_phrases") or d.get("trigger_mode") == "reactive":
                d["rag_enabled"] = True

        return d

    @model_validator(mode="after")
    def _wrap_conditions_list(self) -> "LoreBlock":
        if not isinstance(self.conditions, EntityConditionsList):
            self.conditions = EntityConditionsList(self.conditions)
        if not isinstance(self.exit_conditions, EntityConditionsList):
            self.exit_conditions = EntityConditionsList(self.exit_conditions)
        if not self.rag_enabled and self.trigger_phrases:
            self.rag_enabled = True
        self.trigger_mode = "reactive" if self.rag_enabled else "proactive"
        return self

    @property
    def on_active(self) -> LoreEffects:
        """Devuelve el primer efecto de timing 'active' o crea uno por defecto para compatibilidad."""
        for eff in self.effects:
            if eff.timing == "active":
                return eff
        eff = LoreEffects(timing="active")
        self.effects.append(eff)
        return eff

    @on_active.setter
    def on_active(self, val: Union[LoreEffects, dict]) -> None:
        if isinstance(val, dict):
            val = LoreEffects(**val)
        val.timing = "active"
        for idx, eff in enumerate(self.effects):
            if eff.timing == "active":
                self.effects[idx] = val
                return
        self.effects.append(val)

    @property
    def on_done(self) -> LoreEffects:
        """Devuelve el primer efecto de timing 'done' o crea uno por defecto para compatibilidad."""
        for eff in self.effects:
            if eff.timing == "done":
                return eff
        eff = LoreEffects(timing="done")
        self.effects.append(eff)
        return eff

    @on_done.setter
    def on_done(self, val: Union[LoreEffects, dict]) -> None:
        if isinstance(val, dict):
            val = LoreEffects(**val)
        val.timing = "done"
        for idx, eff in enumerate(self.effects):
            if eff.timing == "done":
                self.effects[idx] = val
                return
        self.effects.append(val)

    def get_effects_for_timing(self, timing: str) -> List[LoreEffects]:
        """Devuelve todos los efectos asociados a un momento de activación (active o done)."""
        clean_timing = "active" if timing in ("active", "on_active") else "done"
        return [eff for eff in self.effects if eff.timing == clean_timing]

    def get_effect_for_entity(self, entity_id_or_name: str, timing: Optional[str] = None) -> Optional[LoreEffects]:
        """Devuelve el efecto configurado específicamente para una entidad."""
        t_clean = str(entity_id_or_name).strip().lower()
        clean_timing = "active" if timing in ("active", "on_active") else ("done" if timing in ("done", "on_done") else None)
        for eff in self.effects:
            if (eff.target or "").strip().lower() == t_clean:
                if clean_timing and eff.timing != clean_timing:
                    continue
                return eff
        return None

    def get_directive_for_entity(self, entity_id_or_name: Optional[str] = None, timing: Optional[str] = None) -> Optional[str]:
        """Obtiene la directiva adecuada considerando la entidad objetivo y el momento (active/done)."""
        clean_timing = "active" if timing in ("active", "on_active") else ("done" if timing in ("done", "on_done") else None)
        if entity_id_or_name:
            t_clean = str(entity_id_or_name).strip().lower()
            # 1. Buscar con coincidencia exacta de entidad y timing (si se especificó timing)
            for eff in self.effects:
                if (eff.target or "").strip().lower() == t_clean:
                    if clean_timing and eff.timing != clean_timing:
                        continue
                    if eff.directive:
                        return eff.directive
            # Si se especificó timing y no hubo coincidencia para esa entidad en ese timing,
            # no tomar directivas de otros timings. Buscar si hay efecto global (sin target) para ese timing.
            if clean_timing:
                for eff in self.effects:
                    if not eff.target and eff.timing == clean_timing and eff.directive:
                        return eff.directive
                return None
            else:
                # Sin timing especificado: buscar si hay efecto global (sin target)
                for eff in self.effects:
                    if not eff.target and eff.directive:
                        return eff.directive
                return None

        # Fallback a directiva de efecto general (sin target) respetando timing
        for eff in self.effects:
            if not eff.target and (clean_timing is None or eff.timing == clean_timing) and eff.directive:
                return eff.directive

        # Si no hay efectos o ninguno tiene target específico, fallback a self.directive
        if not self.effects or all(not eff.target for eff in self.effects):
            return self.directive or None

        return None

    @property
    def directive(self) -> str:
        if self.state == "done":
            for eff in self.effects:
                if eff.timing == "done" and eff.directive:
                    return eff.directive
        for eff in self.effects:
            if eff.timing == "active" and eff.directive:
                return eff.directive
        for eff in self.effects:
            if eff.directive:
                return eff.directive
        return ""

    @directive.setter
    def directive(self, val: str) -> None:
        self.on_active.directive = val or ""

    @property
    def target_entities(self) -> List[str]:
        targets = []
        for eff in self.effects:
            if eff.target and eff.target not in targets:
                targets.append(eff.target)
        return targets

    @target_entities.setter
    def target_entities(self, val: List[str]) -> None:
        if val:
            self.on_active.target = val[0]
        else:
            for eff in self.effects:
                eff.target = None

    @property
    def force_action(self) -> bool:
        return any(eff.force_action for eff in self.effects)

    @force_action.setter
    def force_action(self, val: bool) -> None:
        self.on_active.force_action = bool(val)

    @property
    def repeatable(self) -> bool:
        return False

    @repeatable.setter
    def repeatable(self, val: bool) -> None:
        pass

    @property
    def once(self) -> bool:
        return True

    @once.setter
    def once(self, val: bool) -> None:
        pass

    @property
    def revealed(self) -> bool:
        return self.state == "done"

    @revealed.setter
    def revealed(self, val: bool) -> None:
        self.state = "done" if val else "unknown"
