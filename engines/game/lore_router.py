"""Enrutador semántico y evaluador de condiciones de Lore Dinámico y Máquina de Estados (HSM)."""

import logging
from typing import Any, List, Optional, Tuple, Union
from domains import (
    Entity,
    EntityCondition,
    LoreBlock,
    LoreConditions,
    NPC,
    Place,
    Player,
    RagAntennaScoreProjection,
    RagEvaluationProjection,
)
from engines.embedding import BaseEmbeddingBackend, EmbeddingFactory
from engines.game.state_controller import GameStateController

logger = logging.getLogger(__name__)


class LoreRouter:
    """Coordina la lógica determinista del Game Engine con la detección semántica por embeddings y HSM."""

    _instance: Optional["LoreRouter"] = None

    @classmethod
    def get_instance(cls) -> "LoreRouter":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self, embedding_backend: Optional[BaseEmbeddingBackend] = None):
        self.embedder = embedding_backend or EmbeddingFactory.get_backend()
        self.last_evaluation: Optional[RagEvaluationProjection] = None

    def reset_evaluation(self, player_input: str = "", threshold: float = 0.65) -> None:
        """Reinicia el registro de evaluación RAG para un nuevo turno."""
        self.last_evaluation = RagEvaluationProjection(
            player_input=player_input,
            threshold=threshold,
        )

    def get_last_evaluation(self) -> Optional[RagEvaluationProjection]:
        """Devuelve la última evaluación semántica RAG efectuada."""
        return self.last_evaluation

    def find_lore_block_state(self, lore_id: str, game_state: GameStateController) -> Optional[str]:
        """Busca el estado de un LoreBlock por su ID en la máquina de estados y entidades."""
        # 1. Consulta directa en listas HSM de GameState
        done_list = getattr(game_state, "done_lore_blocks", None)
        if done_list is not None and lore_id in done_list:
            return "done"
        active_list = getattr(game_state, "active_lore_blocks", None)
        if active_list is not None and lore_id in active_list:
            return "active"

        # 2. Catálogo centralizado en world_state
        if hasattr(game_state, "world_state") and hasattr(game_state.world_state, "lore_blocks"):
            if lore_id in game_state.world_state.lore_blocks:
                return getattr(game_state.world_state.lore_blocks[lore_id], "state", "unknown")

        # 3. En lugares y sus objetos (compatibilidad retroactiva)
        if hasattr(game_state, "world_state") and game_state.world_state and game_state.world_state.world:
            for loc in game_state.world_state.world.locations:
                for place in loc.places:
                    for b in getattr(place, "dynamic_lore", []):
                        if b.id == lore_id:
                            return getattr(b, "state", "unknown")
                    for item in getattr(place, "items", []):
                        for b in getattr(item, "dynamic_lore", []):
                            if b.id == lore_id:
                                return getattr(b, "state", "unknown")

        # 4. En NPCs del mundo
        if hasattr(game_state, "world_state") and game_state.world_state:
            for n in game_state.world_state.npcs.values():
                for b in getattr(n, "dynamic_lore", []):
                    if b.id == lore_id:
                        return getattr(b, "state", "unknown")

        # 5. En NPCs locales de sesión
        for n in getattr(game_state.data, "npcs", {}).values():
            for b in getattr(n, "dynamic_lore", []):
                if b.id == lore_id:
                    return getattr(b, "state", "unknown")

        # 6. En lugar actual de sesión
        curr_p = getattr(game_state, "place", None) or getattr(game_state.data, "place", None)
        if curr_p:
            for b in getattr(curr_p, "dynamic_lore", []):
                if b.id == lore_id:
                    return getattr(b, "state", "unknown")
            for item in getattr(curr_p, "items", []):
                for b in getattr(item, "dynamic_lore", []):
                    if b.id == lore_id:
                        return getattr(b, "state", "unknown")

        return None

    def _get_all_blocks(self, game_state: Optional[GameStateController] = None) -> List[LoreBlock]:
        """Obtiene la lista completa de todos los LoreBlocks conocidos en el juego."""
        blocks: List[LoreBlock] = []
        seen_ids = set()

        if game_state:
            # 1. world_state.lore_blocks
            if hasattr(game_state, "world_state") and game_state.world_state and hasattr(game_state.world_state, "lore_blocks"):
                for b in game_state.world_state.lore_blocks.values():
                    if b.id not in seen_ids:
                        blocks.append(b)
                        seen_ids.add(b.id)

            # 2. game_state.lore_blocks
            if hasattr(game_state, "lore_blocks"):
                lbs = game_state.lore_blocks.values() if isinstance(game_state.lore_blocks, dict) else game_state.lore_blocks
                for b in lbs:
                    if getattr(b, "id", None) and b.id not in seen_ids:
                        blocks.append(b)
                        seen_ids.add(b.id)

            # 3. game_state.data (session)
            if hasattr(game_state, "data") and game_state.data:
                # NPCs
                for n in getattr(game_state.data, "npcs", {}).values():
                    for b in getattr(n, "dynamic_lore", []):
                        if getattr(b, "id", None) and b.id not in seen_ids:
                            blocks.append(b)
                            seen_ids.add(b.id)
                # Current place
                curr_p = getattr(game_state.data, "place", None)
                if curr_p:
                    for b in getattr(curr_p, "dynamic_lore", []):
                        if getattr(b, "id", None) and b.id not in seen_ids:
                            blocks.append(b)
                            seen_ids.add(b.id)
                    for item in getattr(curr_p, "items", []):
                        for b in getattr(item, "dynamic_lore", []):
                            if getattr(b, "id", None) and b.id not in seen_ids:
                                blocks.append(b)
                                seen_ids.add(b.id)
        return blocks

    def has_child_blocks(self, block: LoreBlock, game_state: Optional[GameStateController] = None) -> bool:
        """Determina si un bloque alberga sub-bloques hijos (actúa como carpeta contenedora)."""
        all_blocks = self._get_all_blocks(game_state)
        return any(getattr(b, "parent_id", None) == block.id for b in all_blocks)

    def is_block_accessible(
        self,
        block: LoreBlock,
        game_state: Optional[GameStateController] = None,
        visited_ids: Optional[set] = None,
    ) -> bool:
        """Verifica si un bloque es accesible según la jerarquía de carpetas/padres HSM.

        Un bloque raíz (parent_id is None) siempre es accesible.
        Un bloque hijo solo es accesible si su padre directo y todos sus ancestros están en estado 'active'.
        """
        p_id = getattr(block, "parent_id", None)
        if not p_id or not str(p_id).strip():
            return True

        if not game_state:
            return True

        p_id = str(p_id).strip()

        # Detección de ciclos recursivos
        if visited_ids is None:
            visited_ids = set()
        if block.id in visited_ids:
            return False
        visited_ids.add(block.id)

        all_blocks = self._get_all_blocks(game_state)
        parent_block = next((b for b in all_blocks if b.id == p_id), None)

        if not parent_block:
            st = self.find_lore_block_state(p_id, game_state)
            if st != "active":
                return False
            return True

        if parent_block.state != "active":
            return False

        return self.is_block_accessible(parent_block, game_state, visited_ids)

    def evaluate_single_condition(
        self,
        cond: EntityCondition,
        game_state: GameStateController,
        npc: Optional[NPC] = None,
        evaluating_block: Optional[LoreBlock] = None,
    ) -> bool:
        """Evalúa una condición individual sobre una entidad (Place, NPC, Item, LoreBlock)."""
        player = getattr(game_state.data, "player", None)
        result = False

        if cond.entity_type == "place":
            target_id_or_name = cond.entity_id.strip()
            if cond.sub_condition == "known":
                known_places = list(getattr(game_state, "known_places", []))
                if hasattr(game_state, "fog_war") and game_state.fog_war:
                    known_places.extend(game_state.fog_war.get_all_discovered_places())
                if player:
                    known_places.extend(getattr(player, "visited_places", []) or [])
                    known_places.extend(getattr(player, "unlocked_places", []) or [])

                all_known_ids = set()
                if hasattr(game_state, "world_state") and game_state.world_state:
                    for p_name in known_places:
                        p = game_state.world_state.places_by_name.get(p_name) or game_state.world_state.places_by_id.get(p_name)
                        if p:
                            all_known_ids.add(p.id)
                            all_known_ids.add(p.name)

                result = target_id_or_name in known_places or target_id_or_name in all_known_ids

            elif cond.sub_condition == "current_location":
                curr_loc = getattr(game_state, "current_location", "")
                curr_place = getattr(game_state, "place", None) or getattr(game_state.data, "place", None)
                names_and_ids = {curr_loc.lower()}
                if curr_place:
                    names_and_ids.add(curr_place.name.lower())
                    names_and_ids.add(curr_place.id.lower())
                if player and getattr(player, "player_location", None):
                    names_and_ids.add(player.player_location.lower())
                result = target_id_or_name.lower() in names_and_ids

        elif cond.entity_type == "npc":
            target_npc = npc
            if cond.entity_id:
                if cond.entity_id in getattr(game_state.data, "npcs", {}):
                    target_npc = game_state.data.npcs[cond.entity_id]
                elif hasattr(game_state, "world_state") and game_state.world_state:
                    if cond.entity_id in game_state.world_state.npcs:
                        target_npc = game_state.world_state.npcs[cond.entity_id]
                    elif cond.entity_id in game_state.world_state.npcs_by_name:
                        target_npc = game_state.world_state.npcs_by_name[cond.entity_id]

            if cond.sub_condition == "known":
                known_npcs = set(getattr(game_state, "known_npcs", []) or [])
                visible_npcs = set(getattr(game_state, "visible_npcs", []) or [])
                if player:
                    known_npcs.update(getattr(player, "known_npcs", []) or [])
                if hasattr(game_state, "fog_war") and game_state.fog_war:
                    visible_npcs.update(game_state.fog_war.get_visible_npcs())
                all_known = known_npcs | visible_npcs
                if target_npc:
                    result = target_npc.name in all_known or target_npc.id in all_known
                else:
                    result = cond.entity_id in all_known

            elif cond.sub_condition == "affinity":
                min_val = float(cond.value or 0.0)
                if target_npc is not None:
                    result = target_npc.affinity >= min_val

        elif cond.entity_type == "item":
            target_item_id = cond.entity_id.strip()
            if cond.sub_condition == "known":
                known_objs = set(getattr(game_state, "known_objs", []) or [])
                known_objs.update(getattr(game_state, "visible_objs", []) or [])
                if player:
                    known_objs.update(getattr(player, "known_items", []) or [])
                result = target_item_id in known_objs
            elif cond.sub_condition == "have":
                if target_item_id.lower() == "gold":
                    req_gold = int(cond.value or 0)
                    gold_val = getattr(game_state, "gold", getattr(player, "gold", 0) if player else 0)
                    result = bool(gold_val >= req_gold)
                else:
                    inventory = getattr(game_state, "inventory", getattr(player, "inventory", []) if player else []) or []
                    result = target_item_id in inventory

        elif cond.entity_type == "loreblock":
            if cond.sub_condition == "any_child_done":
                target_id = cond.entity_id.strip()
                p_id = target_id or (evaluating_block.id if evaluating_block else "")
                all_blocks = self._get_all_blocks(game_state)
                result = any(
                    getattr(b, "parent_id", None) == p_id and getattr(b, "state", "") == "done"
                    for b in all_blocks
                )
            else:
                target_lore_id = cond.entity_id.strip()
                found_state = self.find_lore_block_state(target_lore_id, game_state)
                if found_state is None and player:
                    if target_lore_id in player.completed_quests:
                        found_state = "done"
                    elif player.active_quest == target_lore_id:
                        found_state = "active"

                if cond.sub_condition == "active":
                    result = (found_state == "active")
                elif cond.sub_condition == "done":
                    result = (found_state == "done")

        if cond.is_negated:
            result = not result

        return result

    def check_conditions(
        self,
        conditions: Union[LoreConditions, List[EntityCondition]],
        game_state: GameStateController,
        npc: Optional[NPC] = None,
        evaluating_block: Optional[LoreBlock] = None,
    ) -> bool:
        """Verifica si se cumplen las condiciones lógicas (1 a N) del bloque."""
        if isinstance(conditions, LoreConditions):
            player: Player = game_state.data.player
            if npc is not None:
                if not (conditions.min_affinity <= npc.affinity <= conditions.max_affinity):
                    return False
            if conditions.required_gold > 0:
                if not player or player.gold < conditions.required_gold:
                    return False
            if conditions.required_quests:
                if not player:
                    return False
                for q in conditions.required_quests:
                    if q not in player.completed_quests:
                        return False
            if conditions.required_items:
                if not player:
                    return False
                player_inv = getattr(player, "inventory", [])
                for item in conditions.required_items:
                    if item not in player_inv:
                        return False
            return True

        if not conditions:
            return True

        for cond in conditions:
            if not self.evaluate_single_condition(cond, game_state, npc, evaluating_block=evaluating_block):
                return False

        return True

    def get_blocks_for_entity(
        self,
        entity: Any,
        game_state: Optional[GameStateController] = None,
    ) -> List[LoreBlock]:
        """Obtiene todos los LoreBlocks del catálogo global que afectan a la entidad dada."""
        e_id = getattr(entity, "id", None)
        e_name = getattr(entity, "name", None)
        if e_id is None and isinstance(entity, str):
            e_id = entity

        matched_blocks = []
        seen_ids = set()

        # 1. Catálogo centralizado en world_state.lore_blocks
        if game_state and hasattr(game_state, "world_state") and game_state.world_state:
            for b in game_state.world_state.lore_blocks.values():
                if b.id not in seen_ids:
                    targets = getattr(b, "target_entities", []) or []
                    if (e_id and e_id in targets) or (e_name and e_name in targets):
                        matched_blocks.append(b)
                        seen_ids.add(b.id)

        # 2. Bloques embebidos en entity.dynamic_lore si existieran
        if hasattr(entity, "dynamic_lore") and entity.dynamic_lore:
            for b in entity.dynamic_lore:
                if b.id not in seen_ids:
                    matched_blocks.append(b)
                    seen_ids.add(b.id)

        return matched_blocks

    def find_proactive_lore(
        self,
        entity: Entity,
        game_state: GameStateController,
        npc: Optional[NPC] = None,
    ) -> Optional[LoreBlock]:
        """Busca un bloque de lore con iniciativa proactiva o determinista que cumpla condiciones."""
        candidate_blocks = [
            b for b in self.get_blocks_for_entity(entity, game_state)
            if self.is_block_accessible(b, game_state)
        ]
        if not candidate_blocks:
            return None

        for block in candidate_blocks:
            # 1. Si ya está completado, no se ejecuta
            if block.state == "done" or (block.once and block.revealed):
                continue

            # 2. Si está en active y es repetible o contenedor, verificar si debe salir a done
            if block.state == "active":
                if not block.repeatable and not block.exit_conditions:
                    continue
                if block.exit_conditions and self.check_conditions(block.exit_conditions, game_state, npc, evaluating_block=block):
                    block.state = "done"
                    if block.effect_timing == "on_done":
                        self.apply_effects(block, game_state, npc)
                    continue
                if not block.repeatable:
                    continue

            # 3. Solo evalúa bloques proactivos o bloques sin RAG (activación pura por estado)
            if block.trigger_mode == "proactive" or not block.rag_enabled:
                if self.check_conditions(block.conditions, game_state, npc, evaluating_block=block):
                    return block

        return None

    def find_reactive_lore(
        self,
        player_input: str,
        entity: Entity,
        game_state: GameStateController,
        npc: Optional[NPC] = None,
        threshold: float = 0.65,
    ) -> Optional[Tuple[LoreBlock, float]]:
        """Evalúa si la entrada del jugador activa un bloque reactivo por similitud semántica o estado."""
        candidate_blocks = [
            b for b in self.get_blocks_for_entity(entity, game_state)
            if self.is_block_accessible(b, game_state)
        ]
        if not candidate_blocks:
            return None

        clean_input = player_input.strip()
        if not clean_input:
            return None

        if self.last_evaluation is None or self.last_evaluation.player_input != clean_input:
            self.last_evaluation = RagEvaluationProjection(
                player_input=clean_input,
                threshold=threshold,
            )

        def _get_specificity(b: LoreBlock) -> int:
            return len(b.conditions) * 20

        best_block: Optional[LoreBlock] = None
        best_score: float = 0.0
        best_raw_score: float = 0.0
        best_antenna: Optional[str] = None

        query_vec = None

        for block in candidate_blocks:
            if block.state == "done" or (block.once and block.revealed):
                continue

            if block.state == "active":
                if not block.repeatable:
                    continue
                exit_conds_met = (
                    self.check_conditions(block.exit_conditions, game_state, npc, evaluating_block=block)
                    if block.exit_conditions else True
                )
                if exit_conds_met:
                    if getattr(block, "exit_rag_enabled", False) and getattr(block, "exit_trigger_phrases", None):
                        if query_vec is None:
                            query_vec = self.embedder.embed_text(clean_input)
                        matched_exit = False
                        for phrase in block.exit_trigger_phrases:
                            p_vec = self.embedder.embed_text(phrase)
                            p_score = round(float(self.embedder.compute_similarity(query_vec, p_vec)), 4)
                            if p_score >= threshold:
                                matched_exit = True
                                break
                        if not matched_exit:
                            continue

                    block.state = "done"
                    if block.effect_timing == "on_done":
                        self.apply_effects(block, game_state, npc)
                    continue

            cond_met = self.check_conditions(block.conditions, game_state, npc, evaluating_block=block)
            if not cond_met:
                continue

            # Si el bloque NO tiene RAG habilitado, se activa directamente si cumple condiciones
            if not block.rag_enabled:
                best_block = block
                best_raw_score = 1.0
                best_antenna = block.title or block.id
                break

            # Si tiene RAG activado, evaluar trigger_phrases
            if not block.trigger_phrases:
                continue

            if query_vec is None:
                query_vec = self.embedder.embed_text(clean_input)

            block_max_score = 0.0
            block_best_phrase = None

            for phrase in block.trigger_phrases:
                phrase_vec = self.embedder.embed_text(phrase)
                phrase_score = round(float(self.embedder.compute_similarity(query_vec, phrase_vec)), 4)

                self.last_evaluation.antennas.append(
                    RagAntennaScoreProjection(
                        antenna=phrase,
                        lore_id=block.id,
                        lore_title=getattr(block, "title", block.id) or block.id,
                        score=phrase_score,
                        threshold=threshold,
                        conditions_met=cond_met,
                        is_matched=False,
                        is_injected=False,
                    )
                )

                if phrase_score > block_max_score:
                    block_max_score = phrase_score
                    block_best_phrase = phrase

            if block_max_score >= threshold:
                weighted_score = block_max_score + (_get_specificity(block) * 0.002)
                if weighted_score > best_score:
                    best_score = weighted_score
                    best_raw_score = block_max_score
                    best_block = block
                    best_antenna = block_best_phrase

        if best_block is not None:
            self.last_evaluation.matched_lore_id = best_block.id
            self.last_evaluation.matched_antenna = best_antenna
            self.last_evaluation.injected_directive = best_block.directive

            for ant in self.last_evaluation.antennas:
                if ant.lore_id == best_block.id and ant.antenna == best_antenna:
                    ant.is_matched = True
                    ant.is_injected = True
                    break

            return best_block, best_raw_score

        return None

    def apply_effects(
        self,
        block: LoreBlock,
        game_state: GameStateController,
        npc: Optional[NPC] = None,
    ) -> dict:
        """Aplica las mutaciones del bloque al estado de juego según su ciclo de vida HSM."""
        mutations = {}
        player = game_state.data.player

        # Determinar transición de estado
        entering_active = (block.state == "unknown")
        transitioning_to_done = False

        is_container = bool(block.repeatable or block.exit_conditions or self.has_child_blocks(block, game_state))

        if not is_container:
            block.state = "done"
            transitioning_to_done = True
            mutations["state"] = "done"
            if hasattr(game_state, "active_lore_blocks") and block.id in game_state.active_lore_blocks:
                game_state.active_lore_blocks.remove(block.id)
            if hasattr(game_state, "done_lore_blocks") and block.id not in game_state.done_lore_blocks:
                game_state.done_lore_blocks.append(block.id)
        else:
            block.state = "active"
            mutations["state"] = "active"
            if hasattr(game_state, "active_lore_blocks") and block.id not in game_state.active_lore_blocks:
                game_state.active_lore_blocks.append(block.id)
            if block.exit_conditions and self.check_conditions(block.exit_conditions, game_state, npc, evaluating_block=block):
                block.state = "done"
                transitioning_to_done = True
                mutations["state"] = "done"
                if hasattr(game_state, "active_lore_blocks") and block.id in game_state.active_lore_blocks:
                    game_state.active_lore_blocks.remove(block.id)
                if hasattr(game_state, "done_lore_blocks") and block.id not in game_state.done_lore_blocks:
                    game_state.done_lore_blocks.append(block.id)

        # Verificar si deben aplicarse los efectos según timing
        should_apply = False
        if block.effect_timing == "on_active" and (entering_active or block.repeatable):
            should_apply = True
        elif block.effect_timing == "on_done" and transitioning_to_done:
            should_apply = True
        elif block.effect_timing not in ["on_active", "on_done"]:
            should_apply = True

        if not should_apply:
            return mutations

        effects = block.effects

        # 1. Oro
        if effects.gold_delta != 0:
            if hasattr(game_state, "gold"):
                game_state.gold = max(0, game_state.gold + effects.gold_delta)
            if player and hasattr(player, "gold"):
                player.gold = max(0, player.gold + effects.gold_delta)
            mutations["gold_delta"] = effects.gold_delta
        elif effects.give_gold > 0:
            if hasattr(game_state, "gold"):
                game_state.gold += effects.give_gold
            if player and hasattr(player, "gold"):
                player.gold += effects.give_gold
            mutations["gold_gained"] = effects.give_gold

        if effects.take_gold > 0:
            curr_gold = getattr(game_state, "gold", player.gold if player else 0)
            taken = min(curr_gold, effects.take_gold)
            if hasattr(game_state, "gold"):
                game_state.gold -= taken
            if player and hasattr(player, "gold"):
                player.gold -= taken
            mutations["gold_spent"] = taken

        # 2. Objetos
        inv = getattr(game_state, "inventory", getattr(player, "inventory", []) if player else [])
        known_o = getattr(game_state, "known_objs", getattr(player, "known_items", []) if player else [])

        for item in effects.give_items:
            if hasattr(game_state, "give_item_to_player"):
                game_state.give_item_to_player(item)
            else:
                if item not in inv:
                    inv.append(item)
            if player and hasattr(player, "inventory") and item not in player.inventory:
                player.inventory.append(item)
            mutations.setdefault("items_received", []).append(item)
            if item not in known_o:
                known_o.append(item)

        for item in effects.take_items:
            if hasattr(game_state, "remove_item_from_player"):
                game_state.remove_item_from_player(item)
            else:
                if item in inv:
                    inv.remove(item)
            if player and hasattr(player, "inventory") and item in player.inventory:
                player.inventory.remove(item)
            mutations.setdefault("items_removed", []).append(item)

        # 3. Afinidad
        if npc is not None and effects.affinity_delta != 0.0:
            npc.affinity = round(max(0.0, min(1.0, npc.affinity + effects.affinity_delta)), 4)
            mutations["affinity_delta"] = effects.affinity_delta
            mutations["new_affinity"] = npc.affinity

        if effects.npc_affinity_deltas:
            for n_id, delta in effects.npc_affinity_deltas.items():
                target_npc = None
                if n_id in getattr(game_state.data, "npcs", {}):
                    target_npc = game_state.data.npcs[n_id]
                elif hasattr(game_state, "world_state") and game_state.world_state:
                    target_npc = game_state.world_state.npcs.get(n_id) or game_state.world_state.npcs_by_name.get(n_id)
                if target_npc:
                    target_npc.affinity = round(max(0.0, min(1.0, target_npc.affinity + delta)), 4)
                    mutations.setdefault("npc_affinity_changes", {})[n_id] = target_npc.affinity

        # 4. Misiones
        if effects.unlock_quests and player:
            for q in effects.unlock_quests:
                if q not in player.completed_quests and player.active_quest != q:
                    player.active_quest = q
                    mutations.setdefault("quests_unlocked", []).append(q)

        # 5. Lugares
        if effects.unlock_places:
            for p in effects.unlock_places:
                if hasattr(player, "unlocked_places"):
                    if p not in player.unlocked_places:
                        player.unlocked_places.append(p)
                if hasattr(game_state, "fog_war") and game_state.fog_war:
                    game_state.fog_war.visit(p)
                mutations.setdefault("places_unlocked", []).append(p)

        # 6. NPCs conocidos
        known_n = getattr(game_state, "known_npcs", getattr(player, "known_npcs", []) if player else [])
        if effects.unlock_npcs:
            for n in effects.unlock_npcs:
                if n not in known_n:
                    known_n.append(n)
                mutations.setdefault("npcs_unlocked", []).append(n)

        # 7. Aparición dinámica de NPCs (spawn_npcs)
        for spawn_info in getattr(effects, "spawn_npcs", []):
            n_id = spawn_info.get("npc_id")
            p_id = spawn_info.get("place_id") or getattr(game_state, "current_location", "")
            if hasattr(game_state, "spawn_npc"):
                game_state.spawn_npc(n_id, p_id)
            mutations.setdefault("npcs_spawned", []).append({"npc_id": n_id, "place_id": p_id})

        # 8. Aparición dinámica de Objetos (spawn_objects)
        for spawn_info in getattr(effects, "spawn_objects", []):
            o_id = spawn_info.get("object_id")
            p_id = spawn_info.get("place_id") or getattr(game_state, "current_location", "")
            if hasattr(game_state, "spawn_object"):
                game_state.spawn_object(o_id, p_id)
            mutations.setdefault("objects_spawned", []).append({"object_id": o_id, "place_id": p_id})

        # 9. Acción forzada o sugerida
        if effects.trigger_action_type and effects.trigger_action_target:
            mutations["trigger_action"] = {
                "action": effects.trigger_action_type,
                "target": effects.trigger_action_target,
            }

        # 10. Evaluar condiciones de salida en bloques padre si este bloque cambió de estado
        self.check_and_update_parent_exit_conditions(game_state, npc)

        return mutations

    def check_and_update_parent_exit_conditions(
        self,
        game_state: GameStateController,
        npc: Optional[NPC] = None,
    ) -> List[str]:
        """Evalúa si algún bloque padre en estado 'active' cumple sus condiciones de salida gracias a sus hijos."""
        all_blocks = self._get_all_blocks(game_state)
        done_parents: List[str] = []

        active_parents = [b for b in all_blocks if b.state == "active" and b.exit_conditions]

        for parent in active_parents:
            if self.check_conditions(parent.exit_conditions, game_state, npc, evaluating_block=parent):
                parent.state = "done"
                done_parents.append(parent.id)
                if hasattr(game_state, "active_lore_blocks") and parent.id in game_state.active_lore_blocks:
                    game_state.active_lore_blocks.remove(parent.id)
                if hasattr(game_state, "done_lore_blocks") and parent.id not in game_state.done_lore_blocks:
                    game_state.done_lore_blocks.append(parent.id)
                if parent.effect_timing == "on_done":
                    self.apply_effects(parent, game_state, npc)

        # Propagar recursivamente si algún padre transicionó a done
        if done_parents:
            self.check_and_update_parent_exit_conditions(game_state, npc)

        return done_parents

    def route_dialogue_lore(
        self,
        npc: NPC,
        game_state: GameStateController,
        player_input: str,
    ) -> Optional[LoreBlock]:
        """Enruta la búsqueda de lore en diálogo (reactivo primero, luego proactivo)."""
        reactive = self.find_reactive_lore(player_input, npc, game_state, npc=npc)
        if reactive:
            return reactive[0]
        return self.find_proactive_lore(npc, game_state, npc=npc)

    def route_look_lore(
        self,
        entity: Entity,
        game_state: GameStateController,
        player_input: str,
    ) -> Optional[LoreBlock]:
        """Enruta la búsqueda de lore en inspección (reactivo primero, luego proactivo)."""
        reactive = self.find_reactive_lore(player_input, entity, game_state, npc=None)
        if reactive:
            return reactive[0]
        return self.find_proactive_lore(entity, game_state, npc=None)

    def check_conditions_for_move(
        self,
        conditions: Union[LoreConditions, List[EntityCondition]],
        game_state: GameStateController,
        hypothetical_place: Place,
    ) -> bool:
        """Verifica si se cumplen las condiciones simulando la llegada a hypothetical_place."""
        for cond in conditions:
            if cond.entity_type == "place" and cond.sub_condition == "current_location":
                target_p = cond.entity_id.strip()
                matches = (not target_p or target_p == hypothetical_place.id or target_p == hypothetical_place.name)
                if cond.is_negated:
                    matches = not matches
                if not matches:
                    return False
            else:
                if not self.evaluate_single_condition(cond, game_state):
                    return False
        return True

    def route_move_lore(
        self,
        destination_place: Place,
        game_state: GameStateController,
        player_input: str,
        path_taken: Optional[List[Place]] = None,
    ) -> Optional[LoreBlock]:
        """Enruta la búsqueda de lore aplicable a una acción MOVE que conduce a destination_place.
        Busca bloques que afecten a destination_place y tengan la subcondición current_location.
        """
        places_to_check = [destination_place]
        if path_taken:
            for p in path_taken:
                if p.id != destination_place.id and p not in places_to_check:
                    places_to_check.append(p)

        for pl in places_to_check:
            candidate_blocks = [
                b for b in self.get_blocks_for_entity(pl, game_state)
                if self.is_block_accessible(b, game_state)
            ]
            for block in candidate_blocks:
                if block.state == "done" or (block.once and block.revealed):
                    continue

                if block.state == "active" and not block.repeatable:
                    continue

                # El bloque debe contener la condición current_location sobre este lugar
                has_curr_loc = any(
                    cond.entity_type == "place"
                    and cond.sub_condition == "current_location"
                    and (not cond.entity_id or cond.entity_id in [pl.id, pl.name])
                    for cond in block.conditions
                )
                if not has_curr_loc:
                    continue

                cond_met = self.check_conditions_for_move(block.conditions, game_state, hypothetical_place=pl)
                if not cond_met:
                    continue

                if not block.rag_enabled or block.trigger_mode == "proactive":
                    return block

                clean_input = (player_input or "").strip()
                if clean_input and block.trigger_phrases:
                    query_vec = self.embedder.embed_text(clean_input)
                    for phrase in block.trigger_phrases:
                        p_vec = self.embedder.embed_text(phrase)
                        score = float(self.embedder.compute_similarity(query_vec, p_vec))
                        if score >= 0.65:
                            return block
                elif not block.trigger_phrases:
                    return block

        return None
