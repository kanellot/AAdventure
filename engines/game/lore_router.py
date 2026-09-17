"""Enrutador semántico y evaluador de condiciones de Lore Dinámico y Máquina de Estados (HSM)."""

import logging
from typing import Any, List, Optional, Tuple, Union
from domains import (
    Entity,
    EntityCondition,
    LoreBlock,
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
        self._embedder: Optional[BaseEmbeddingBackend] = embedding_backend
        self.last_evaluation: Optional[RagEvaluationProjection] = None

    @property
    def embedder(self) -> BaseEmbeddingBackend:
        if self._embedder is None:
            self._embedder = EmbeddingFactory.get_backend()
        return self._embedder

    @embedder.setter
    def embedder(self, backend: BaseEmbeddingBackend) -> None:
        self._embedder = backend

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
        player = (
            getattr(game_state, "player", None)
            or (game_state.world_state.player if hasattr(game_state, "world_state") and game_state.world_state else None)
            or getattr(getattr(game_state, "data", None), "player", None)
        )
        result = False

        if isinstance(cond, dict):
            cond = EntityCondition(**cond)

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
                ctrl_npcs = getattr(game_state, "npcs", None)
                if isinstance(ctrl_npcs, dict) and cond.entity_id in ctrl_npcs:
                    target_npc = ctrl_npcs[cond.entity_id]
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

            elif cond.sub_condition == "talk":
                # Condición cumplida si el jugador interactúa con el NPC en diálogo (y no es acción forzada)
                is_forced = getattr(game_state, "_is_executing_forced_action", False)
                if is_forced:
                    result = False
                else:
                    curr_state = ""
                    player_target = ""
                    if hasattr(game_state, "data") and hasattr(game_state.data, "state") and game_state.data.state:
                        curr_state = getattr(game_state.data.state, "player_state", "") or ""
                        player_target = getattr(game_state.data.state, "player_target", "") or ""
                    elif hasattr(game_state, "game_state") and game_state.game_state:
                        curr_state = getattr(game_state.game_state, "player_state", "") or ""
                        player_target = getattr(game_state.game_state, "player_target", "") or ""

                    is_talk_action = (curr_state.upper() == "TALK")
                    target_id_or_name = cond.entity_id.strip() if cond.entity_id else ""
                    npc_matches = False
                    if target_npc:
                        npc_matches = (
                            not target_id_or_name
                            or target_id_or_name.lower() in [target_npc.id.lower(), target_npc.name.lower()]
                        )
                    elif player_target:
                        npc_matches = (
                            not target_id_or_name
                            or target_id_or_name.lower() == player_target.lower()
                        )
                    result = is_talk_action and npc_matches

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
        conditions: List[EntityCondition],
        game_state: GameStateController,
        npc: Optional[NPC] = None,
        evaluating_block: Optional[LoreBlock] = None,
    ) -> bool:
        """Verifica si se cumplen las condiciones lógicas (1 a N) del bloque."""
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

        entity_identifiers = set()
        if e_id:
            entity_identifiers.add(str(e_id).strip().lower())
        if e_name:
            entity_identifiers.add(str(e_name).strip().lower())

        # Si entity es un Place, incluir también identificadores de NPCs ubicados en dicho lugar
        if hasattr(entity, "connections") and game_state and hasattr(game_state, "world_state") and game_state.world_state:
            for n_obj in getattr(game_state.world_state, "npcs", {}).values():
                n_loc = getattr(n_obj, "current_location", None) or getattr(n_obj, "initial_place", None) or getattr(n_obj, "place", None)
                if n_loc and str(n_loc).strip().lower() in entity_identifiers:
                    if getattr(n_obj, "id", None):
                        entity_identifiers.add(str(n_obj.id).strip().lower())
                    if getattr(n_obj, "name", None):
                        entity_identifiers.add(str(n_obj.name).strip().lower())

        matched_blocks = []
        seen_ids = set()

        all_blocks = self._get_all_blocks(game_state)
        for b in all_blocks:
            if b.id in seen_ids:
                continue

            # 1. Comprobar target en los efectos del bloque
            eff_targets = [str(eff.target).strip().lower() for eff in getattr(b, "effects", []) if getattr(eff, "target", None)]
            if any(t in entity_identifiers for t in eff_targets):
                matched_blocks.append(b)
                seen_ids.add(b.id)
                continue

            # 2. Comprobar condiciones que hagan referencia a esta entidad
            has_matching_cond = False
            for cond in (getattr(b, "conditions", []) or []):
                cid = (cond.entity_id or "").strip().lower()
                if cid and cid in entity_identifiers:
                    has_matching_cond = True
                    break
            if has_matching_cond:
                matched_blocks.append(b)
                seen_ids.add(b.id)
                continue

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
            if block.state == "done":
                continue

            # 2. Si está en active, verificar si cumple condiciones de salida para pasar a done
            if block.state == "active":
                if not getattr(block, "exit_rag_enabled", False):
                    if block.exit_conditions and self.check_conditions(block.exit_conditions, game_state, npc, evaluating_block=block):
                        self.apply_effects(block, game_state, npc, to_state="done")
                        continue
                    return block
                else:
                    # Si tiene exit_rag_enabled, la salida requiere interacción semántica (RAG).
                    # Si no tiene directiva propia de on_active ni force_action, no debe ser seleccionado proactivamente.
                    has_act_dir = any(getattr(eff, "directive", "") for eff in block.get_effects_for_timing("active")) if hasattr(block, "get_effects_for_timing") else bool(getattr(block.on_active, "directive", ""))
                    has_act_force = any(getattr(eff, "force_action", False) for eff in block.get_effects_for_timing("active")) if hasattr(block, "get_effects_for_timing") else bool(getattr(block.on_active, "force_action", False))
                    if not has_act_dir and not has_act_force and not getattr(block.on_active, "directive", "") and not getattr(block.on_active, "force_action", False):
                        continue
                    return block

            # 3. Bloque unknown: comprobar condiciones de activación
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
        is_exit_match: bool = False

        query_vec = None

        for block in candidate_blocks:
            if block.state == "done":
                continue

            # CASO 1: Bloque en ACTIVE con RAG de Salida (exit_rag_enabled)
            if block.state == "active" and getattr(block, "exit_rag_enabled", False):
                exit_cond_met = True
                if block.exit_conditions:
                    exit_cond_met = self.check_conditions(block.exit_conditions, game_state, npc, evaluating_block=block)

                if not block.exit_trigger_phrases:
                    continue

                if query_vec is None:
                    query_vec = self.embedder.embed_text(clean_input)

                block_max_score = 0.0
                block_best_phrase = None

                for phrase in block.exit_trigger_phrases:
                    phrase_vec = self.embedder.embed_text(phrase)
                    phrase_score = round(float(self.embedder.compute_similarity(query_vec, phrase_vec)), 4)

                    self.last_evaluation.antennas.append(
                        RagAntennaScoreProjection(
                            antenna=phrase,
                            lore_id=block.id,
                            lore_title=getattr(block, "title", block.id) or block.id,
                            score=phrase_score,
                            threshold=threshold,
                            conditions_met=exit_cond_met,
                            is_matched=False,
                            is_injected=False,
                        )
                    )

                    if phrase_score > block_max_score:
                        block_max_score = phrase_score
                        block_best_phrase = phrase

                if exit_cond_met and block_max_score >= threshold:
                    weighted_score = block_max_score + (_get_specificity(block) * 0.002)
                    if weighted_score > best_score:
                        best_score = weighted_score
                        best_raw_score = block_max_score
                        best_block = block
                        best_antenna = block_best_phrase
                        is_exit_match = True

                continue

            # CASO 2: Bloque en ACTIVE sin RAG de Salida
            if block.state == "active":
                # Si cumple exit_conditions lógicas, transiciona inmediatamente a done y no coincide
                if block.exit_conditions and self.check_conditions(block.exit_conditions, game_state, npc, evaluating_block=block):
                    self.apply_effects(block, game_state, npc, to_state="done")
                    continue
                # Si no las cumple, continúa para evaluar trigger_phrases de activación repetible

            # CASO 3: Evaluación de frases normales (trigger_phrases)
            cond_met = self.check_conditions(block.conditions, game_state, npc, evaluating_block=block)
            if not cond_met:
                continue

            # Si el bloque NO tiene RAG habilitado, se activa reactivamente solo si trigger_mode es reactive
            if not block.rag_enabled:
                if getattr(block, "trigger_mode", "proactive") == "reactive":
                    best_block = block
                    best_raw_score = 1.0
                    best_antenna = block.title or block.id
                    is_exit_match = False
                    break
                continue

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
                    is_exit_match = False

        if best_block is not None:
            self.last_evaluation.matched_lore_id = best_block.id
            self.last_evaluation.matched_antenna = best_antenna

            for ant in self.last_evaluation.antennas:
                if ant.lore_id == best_block.id and ant.antenna == best_antenna:
                    ant.is_matched = True
                    ant.is_injected = True
                    break

            timing = "done" if is_exit_match else "active"
            if is_exit_match:
                # Transicionar a DONE y aplicar mutaciones de on_done
                self.apply_effects(best_block, game_state, npc, to_state="done")

            tgt_id = getattr(entity, "id", None) or getattr(entity, "name", None) if entity else None
            if hasattr(best_block, "get_directive_for_entity"):
                injected_dir = best_block.get_directive_for_entity(tgt_id, timing=timing)
            elif is_exit_match:
                injected_dir = getattr(best_block.on_done, "directive", "") or best_block.directive
            else:
                injected_dir = getattr(best_block.on_active, "directive", "") or best_block.directive

            self.last_evaluation.injected_directive = injected_dir
            return best_block, best_raw_score

        return None

    def apply_lore_effects(
        self,
        effects: Any,
        game_state: GameStateController,
        npc: Optional[NPC] = None,
        block: Optional[LoreBlock] = None,
    ) -> dict:
        """Aplica las mutaciones de un objeto LoreEffects al estado de juego."""
        if not effects:
            return {}

        mutations = {}
        player = getattr(game_state, "player", None) or (game_state.world_state.player if hasattr(game_state, "world_state") and game_state.world_state else None)

        # 1. Oro
        gold_delta = getattr(effects, "gold_delta", 0)
        give_gold = getattr(effects, "give_gold", 0)
        take_gold = getattr(effects, "take_gold", 0)

        if gold_delta != 0:
            if hasattr(game_state, "gold"):
                game_state.gold = max(0, game_state.gold + gold_delta)
            elif player and hasattr(player, "gold"):
                player.gold = max(0, player.gold + gold_delta)
            mutations["gold_delta"] = gold_delta
        elif give_gold > 0:
            if hasattr(game_state, "gold"):
                game_state.gold += give_gold
            elif player and hasattr(player, "gold"):
                player.gold += give_gold
            mutations["gold_gained"] = give_gold

        if take_gold > 0:
            curr_gold = getattr(game_state, "gold", player.gold if player else 0)
            taken = min(curr_gold, take_gold)
            if hasattr(game_state, "gold"):
                game_state.gold -= taken
            elif player and hasattr(player, "gold"):
                player.gold -= taken
            mutations["gold_spent"] = taken

        # 2. Objetos
        inv = getattr(game_state, "inventory", getattr(player, "inventory", []) if player else [])
        known_o = getattr(game_state, "known_objs", getattr(player, "known_items", []) if player else [])

        for item in getattr(effects, "give_items", []):
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

        for item in getattr(effects, "take_items", []):
            if hasattr(game_state, "remove_item_from_player"):
                game_state.remove_item_from_player(item)
            else:
                if item in inv:
                    inv.remove(item)
            if player and hasattr(player, "inventory") and item in player.inventory:
                player.inventory.remove(item)
            mutations.setdefault("items_removed", []).append(item)

        # 3. Afinidad
        aff_delta = getattr(effects, "affinity_delta", 0.0)
        target_npc_for_aff = npc
        eff_target = getattr(effects, "target", None)
        if target_npc_for_aff is None and eff_target:
            if hasattr(game_state, "data") and hasattr(game_state.data, "npcs") and eff_target in game_state.data.npcs:
                target_npc_for_aff = game_state.data.npcs[eff_target]
            elif hasattr(game_state, "world_state") and game_state.world_state:
                target_npc_for_aff = game_state.world_state.npcs.get(eff_target) or game_state.world_state.npcs_by_name.get(eff_target)

        if target_npc_for_aff is not None and aff_delta != 0.0:
            target_npc_for_aff.affinity = round(max(0.0, min(1.0, target_npc_for_aff.affinity + aff_delta)), 4)
            mutations["affinity_delta"] = aff_delta
            mutations["new_affinity"] = target_npc_for_aff.affinity
            if hasattr(game_state, "sync_active_npc_affinity"):
                game_state.sync_active_npc_affinity()

        npc_aff_deltas = getattr(effects, "npc_affinity_deltas", {})
        if npc_aff_deltas:
            for n_id, delta in npc_aff_deltas.items():
                t_npc = None
                if hasattr(game_state, "data") and hasattr(game_state.data, "npcs") and n_id in game_state.data.npcs:
                    t_npc = game_state.data.npcs[n_id]
                elif hasattr(game_state, "world_state") and game_state.world_state:
                    t_npc = game_state.world_state.npcs.get(n_id) or game_state.world_state.npcs_by_name.get(n_id)
                if t_npc:
                    t_npc.affinity = round(max(0.0, min(1.0, t_npc.affinity + delta)), 4)
                    mutations.setdefault("npc_affinity_changes", {})[n_id] = t_npc.affinity
            if hasattr(game_state, "sync_active_npc_affinity"):
                game_state.sync_active_npc_affinity()

        # 4. Misiones
        for q in getattr(effects, "unlock_quests", []):
            if player and q not in player.completed_quests and player.active_quest != q:
                player.active_quest = q
                mutations.setdefault("quests_unlocked", []).append(q)

        # 5. Lugares
        for p in getattr(effects, "unlock_places", []):
            if player and hasattr(player, "unlocked_places"):
                if p not in player.unlocked_places:
                    player.unlocked_places.append(p)
            if hasattr(game_state, "fog_war") and game_state.fog_war:
                game_state.fog_war.visit(p)
            mutations.setdefault("places_unlocked", []).append(p)

        # 6. NPCs conocidos
        known_n = getattr(game_state, "known_npcs", getattr(player, "known_npcs", []) if player else [])
        for n in getattr(effects, "unlock_npcs", []):
            if n not in known_n:
                known_n.append(n)
            mutations.setdefault("npcs_unlocked", []).append(n)

        # 7. Aparición dinámica de NPCs
        for spawn_info in getattr(effects, "spawn_npcs", []):
            n_id = spawn_info.get("npc_id")
            p_id = spawn_info.get("place_id") or getattr(game_state, "current_location", "")
            if hasattr(game_state, "spawn_npc"):
                game_state.spawn_npc(n_id, p_id)
            mutations.setdefault("npcs_spawned", []).append({"npc_id": n_id, "place_id": p_id})

        # 8. Aparición dinámica de Objetos
        for spawn_info in getattr(effects, "spawn_objects", []):
            o_id = spawn_info.get("object_id")
            p_id = spawn_info.get("place_id") or getattr(game_state, "current_location", "")
            if hasattr(game_state, "spawn_object"):
                game_state.spawn_object(o_id, p_id)
            mutations.setdefault("objects_spawned", []).append({"object_id": o_id, "place_id": p_id})

        # 9. Acción forzada
        force_action = getattr(effects, "force_action", False)
        act_type = getattr(effects, "trigger_action_type", None)
        act_tgt = getattr(effects, "trigger_action_target", None) or getattr(effects, "target", None)

        if force_action or (act_type and act_tgt):
            if force_action and (not act_type or not act_tgt):
                if act_tgt:
                    is_npc = False
                    if hasattr(game_state, "world_state") and game_state.world_state:
                        is_npc = (act_tgt in game_state.world_state.npcs or act_tgt in getattr(game_state.world_state, "npcs_by_name", {}))
                    act_type = "TALK" if is_npc else "EXPLAIN"
            if act_type and act_tgt:
                mutations["trigger_action"] = {
                    "action": act_type.upper(),
                    "target": act_tgt,
                    "force_action": force_action,
                }

        # 10. Conexiones bloqueadas / permitidas (bidireccional)
        block_targets = getattr(effects, "block_connections", [])
        allow_targets = getattr(effects, "allow_connections", [])

        if block_targets or allow_targets:
            origin_place_obj = None
            if hasattr(game_state, "world_state") and game_state.world_state:
                p_by_name = getattr(game_state.world_state, "places_by_name", {})
                p_by_id = getattr(game_state.world_state, "places_by_id", {})

                def _resolve_place_from_entity_id(ent_id: Optional[str]) -> Optional[Any]:
                    if not ent_id:
                        return None
                    tid = str(ent_id).strip()
                    # 1. Lugar directo
                    p = p_by_id.get(tid) or p_by_name.get(tid)
                    if p:
                        return p
                    # 2. NPC -> ubicación del NPC en el mundo
                    npc_obj = None
                    if hasattr(game_state, "world_state") and game_state.world_state:
                        npc_obj = game_state.world_state.npcs.get(tid) or getattr(game_state.world_state, "npcs_by_name", {}).get(tid)
                    if not npc_obj and hasattr(game_state, "data") and hasattr(game_state.data, "npcs"):
                        npc_obj = game_state.data.npcs.get(tid)
                    if npc_obj:
                        n_loc = getattr(npc_obj, "current_location", None) or getattr(npc_obj, "initial_place", None) or getattr(npc_obj, "place", None)
                        if n_loc:
                            return p_by_id.get(n_loc) or p_by_name.get(n_loc)
                    return None

                # 1. De effects.target (Place o NPC)
                origin_place_obj = _resolve_place_from_entity_id(getattr(effects, "target", None))

                # 2. De condiciones del bloque
                if not origin_place_obj and block:
                    for cond in getattr(block, "conditions", []) or []:
                        origin_place_obj = _resolve_place_from_entity_id(getattr(cond, "entity_id", None))
                        if origin_place_obj:
                            break

                # 4. De la posición actual del jugador
                if not origin_place_obj:
                    curr_p = getattr(game_state, "place", None) or getattr(getattr(game_state, "data", None), "place", None)
                    if hasattr(curr_p, "name"):
                        origin_place_obj = curr_p
                    elif isinstance(curr_p, str):
                        origin_place_obj = p_by_name.get(curr_p) or p_by_id.get(curr_p)

                def _update_connection_passable(orig_p, target_id_or_name: str, is_passable: bool):
                    if not orig_p or not hasattr(game_state, "world_state") or not game_state.world_state:
                        return
                    target_p = p_by_id.get(target_id_or_name) or p_by_name.get(target_id_or_name)

                    # 1. Actualizar conexión de salida desde orig_p
                    target_identifiers = {target_id_or_name}
                    if target_p:
                        target_identifiers.add(target_p.id)
                        target_identifiers.add(target_p.name)

                    for dir_key, conn in orig_p.connections.items():
                        if conn.target in target_identifiers:
                            conn.passable = is_passable

                    # 2. Actualizar conexión de retorno desde target_p (bidireccional)
                    if target_p:
                        orig_identifiers = {orig_p.id, orig_p.name}
                        for dir_key, conn in target_p.connections.items():
                            if conn.target in orig_identifiers:
                                conn.passable = is_passable

                def _apply_connection_update(target_str: str, is_passable: bool):
                    target_p = p_by_id.get(target_str) or p_by_name.get(target_str)
                    target_ids = {target_str}
                    if target_p:
                        target_ids.add(target_p.id)
                        target_ids.add(target_p.name)

                    effective_orig = origin_place_obj
                    if not effective_orig or not any(conn.target in target_ids for conn in effective_orig.connections.values()):
                        # Buscar si algún lugar del mundo conecta hacia el target
                        for cand_p in p_by_id.values():
                            if any(conn.target in target_ids for conn in cand_p.connections.values()):
                                effective_orig = cand_p
                                break

                    if effective_orig:
                        _update_connection_passable(effective_orig, target_str, is_passable)

                for tgt in block_targets:
                    _apply_connection_update(tgt, False)
                    mutations.setdefault("connections_blocked", []).append(tgt)

                for tgt in allow_targets:
                    _apply_connection_update(tgt, True)
                    mutations.setdefault("connections_allowed", []).append(tgt)

        return mutations

    def apply_effects(
        self,
        block: LoreBlock,
        game_state: GameStateController,
        npc: Optional[NPC] = None,
        to_state: Optional[str] = None,
    ) -> dict:
        """Aplica la transición de estado HSM y ejecuta las mutaciones de on_active u on_done."""
        mutations = {}

        if to_state == "done":
            block.state = "done"
            mutations["state"] = "done"
            if hasattr(game_state, "active_lore_blocks") and block.id in game_state.active_lore_blocks:
                game_state.active_lore_blocks.remove(block.id)
            if hasattr(game_state, "done_lore_blocks") and block.id not in game_state.done_lore_blocks:
                game_state.done_lore_blocks.append(block.id)

            done_effects = block.get_effects_for_timing("done") if hasattr(block, "get_effects_for_timing") else []
            if not done_effects and getattr(block, "on_done", None):
                done_effects = [block.on_done]
            for eff in done_effects:
                mutations.update(self.apply_lore_effects(eff, game_state, npc, block=block))
            self.check_and_update_parent_exit_conditions(game_state, npc)

        elif to_state == "active" or (to_state is None and block.state == "unknown"):
            block.state = "active"
            mutations["state"] = "active"
            if hasattr(game_state, "active_lore_blocks") and block.id not in game_state.active_lore_blocks:
                game_state.active_lore_blocks.append(block.id)
            if hasattr(game_state, "done_lore_blocks") and block.id in game_state.done_lore_blocks:
                game_state.done_lore_blocks.remove(block.id)

            active_effects = block.get_effects_for_timing("active") if hasattr(block, "get_effects_for_timing") else []
            if not active_effects and getattr(block, "on_active", None):
                active_effects = [block.on_active]
            for eff in active_effects:
                mutations.update(self.apply_lore_effects(eff, game_state, npc, block=block))

            # Regla: Si no tiene ninguna condición para done (exit_conditions vacías),
            # y no tiene RAG de salida habilitado, pasa inmediatamente a done en este mismo ciclo.
            if not block.exit_conditions and not getattr(block, "exit_rag_enabled", False):
                block.state = "done"
                mutations["state"] = "done"
                if hasattr(game_state, "active_lore_blocks") and block.id in game_state.active_lore_blocks:
                    game_state.active_lore_blocks.remove(block.id)
                if hasattr(game_state, "done_lore_blocks") and block.id not in game_state.done_lore_blocks:
                    game_state.done_lore_blocks.append(block.id)

                done_effects = block.get_effects_for_timing("done") if hasattr(block, "get_effects_for_timing") else []
                if not done_effects and getattr(block, "on_done", None):
                    done_effects = [block.on_done]
                for eff in done_effects:
                    mutations.update(self.apply_lore_effects(eff, game_state, npc, block=block))
                self.check_and_update_parent_exit_conditions(game_state, npc)

        elif to_state is None and block.state == "active":
            # Si el bloque ya está en 'active' y se le llama apply_effects sin to_state:
            # Solo puede pasar a 'done' si NO tiene exit_rag_enabled (que requiere match semántico con el jugador)
            # y sus exit_conditions se cumplen.
            if not getattr(block, "exit_rag_enabled", False):
                if not block.exit_conditions or self.check_conditions(block.exit_conditions, game_state, npc, evaluating_block=block):
                    return self.apply_effects(block, game_state, npc, to_state="done")

        return mutations

    def check_and_update_parent_exit_conditions(
        self,
        game_state: GameStateController,
        npc: Optional[NPC] = None,
    ) -> List[str]:
        """Evalúa si algún bloque padre en estado 'active' cumple sus condiciones de salida gracias a sus hijos."""
        all_blocks = self._get_all_blocks(game_state)
        done_parents: List[str] = []

        active_parents = [
            b for b in all_blocks
            if b.state == "active" and b.exit_conditions and not getattr(b, "exit_rag_enabled", False)
        ]

        for parent in active_parents:
            if self.check_conditions(parent.exit_conditions, game_state, npc, evaluating_block=parent):
                parent.state = "done"
                done_parents.append(parent.id)
                if hasattr(game_state, "active_lore_blocks") and parent.id in game_state.active_lore_blocks:
                    game_state.active_lore_blocks.remove(parent.id)
                if hasattr(game_state, "done_lore_blocks") and parent.id not in game_state.done_lore_blocks:
                    game_state.done_lore_blocks.append(parent.id)
                self.apply_effects(parent, game_state, npc, to_state="done")

        # Propagar recursivamente si algún padre transicionó a done
        if done_parents:
            self.check_and_update_parent_exit_conditions(game_state, npc)

        return done_parents

    def update_lore_state_machine(
        self,
        game_state: GameStateController,
        npc: Optional[NPC] = None,
    ) -> List[str]:
        """Actualiza en cascada el ciclo de vida de los LoreBlocks según sus condiciones.

        Reglas del usuario:
        - Si no tiene condición para active, pasa a active (si todos sus ancestros están activos).
        - Si no tiene condición para done, pasa a done (a menos que tenga antenas RAG de salida exit_rag_enabled).
        - Los bloques hijos solo se evalúan cuando cumplen su condición Y todos sus padres están activos.
        """
        all_blocks = self._get_all_blocks(game_state)
        transitions = []

        for _ in range(15):
            changed = False

            # 1. Evaluar bloques en active para ver si deben transicionar a done
            for block in all_blocks:
                if block.state != "active":
                    continue
                # Si tiene antenas RAG de salida, SOLO transiciona a done si el RAG se ejecuta y hace match
                if getattr(block, "exit_rag_enabled", False):
                    continue
                if not block.exit_conditions:
                    self.apply_effects(block, game_state, npc, to_state="done")
                    transitions.append(f"{block.id} -> done")
                    changed = True
                elif self.check_conditions(block.exit_conditions, game_state, npc, evaluating_block=block):
                    self.apply_effects(block, game_state, npc, to_state="done")
                    transitions.append(f"{block.id} -> done")
                    changed = True

            # 2. Evaluar bloques unknown cuyos padres estén activos
            for block in all_blocks:
                if block.state != "unknown":
                    continue
                if not self.is_block_accessible(block, game_state):
                    continue

                # Bloques reactivos (RAG con frases de activación) solo se disparan por interacción semántica (find_reactive_lore)
                if block.trigger_mode == "reactive" and block.rag_enabled:
                    continue

                # Si no tiene condiciones de activación, pasa directamente a active
                if not block.conditions:
                    self.apply_effects(block, game_state, npc, to_state="active")
                    transitions.append(f"{block.id} -> active")
                    changed = True
                else:
                    # Si tiene condiciones, comprobar si se cumplen en el estado actual
                    if self.check_conditions(block.conditions, game_state, npc, evaluating_block=block):
                        self.apply_effects(block, game_state, npc, to_state="active")
                        transitions.append(f"{block.id} -> active")
                        changed = True

            if not changed:
                break

        return transitions

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
        conditions: List[EntityCondition],
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
    ) -> Optional[Tuple[LoreBlock, Place]]:
        """Enruta la búsqueda de lore aplicable a una acción MOVE que conduce a destination_place.
        Verifica primero los lugares intermedios atravesados en path_taken, y luego destination_place.
        Devuelve (lore_block, place_triggered) si se dispara alguno.
        """
        # 1. Verificar lugares intermedios atravesados en la trayectoria
        if path_taken:
            for pl in path_taken:
                if pl.id == destination_place.id or pl.name == destination_place.name:
                    continue
                candidate_blocks = [
                    b for b in self.get_blocks_for_entity(pl, game_state)
                    if self.is_block_accessible(b, game_state)
                ]
                for block in candidate_blocks:
                    if block.state == "done":
                        continue

                    # Comprobar si requiere current_location en este lugar intermedio
                    has_curr_loc = any(
                        cond.entity_type == "place"
                        and cond.sub_condition == "current_location"
                        and (not cond.entity_id or cond.entity_id.lower() in [pl.id.lower(), pl.name.lower()])
                        for cond in block.conditions
                    )
                    if not has_curr_loc:
                        continue

                    if not self.check_conditions_for_move(block.conditions, game_state, hypothetical_place=pl):
                        continue

                    if not block.rag_enabled or block.trigger_mode == "proactive":
                        return block, pl

                    clean_input = (player_input or "").strip()
                    if clean_input and block.trigger_phrases:
                        query_vec = self.embedder.embed_text(clean_input)
                        for phrase in block.trigger_phrases:
                            p_vec = self.embedder.embed_text(phrase)
                            score = float(self.embedder.compute_similarity(query_vec, p_vec))
                            if score >= 0.65:
                                return block, pl
                    elif not block.trigger_phrases:
                        return block, pl

        # 2. Verificar el lugar de destino final
        candidate_blocks = [
            b for b in self.get_blocks_for_entity(destination_place, game_state)
            if self.is_block_accessible(b, game_state)
        ]
        for block in candidate_blocks:
            if block.state == "done":
                continue

            has_curr_loc = any(
                cond.entity_type == "place"
                and cond.sub_condition == "current_location"
                and (not cond.entity_id or cond.entity_id.lower() in [destination_place.id.lower(), destination_place.name.lower()])
                for cond in block.conditions
            )
            if has_curr_loc:
                if not self.check_conditions_for_move(block.conditions, game_state, hypothetical_place=destination_place):
                    continue
            else:
                if not self.check_conditions(block.conditions, game_state, evaluating_block=block):
                    continue

            if not block.rag_enabled or block.trigger_mode == "proactive":
                return block, destination_place

            clean_input = (player_input or "").strip()
            if clean_input and block.trigger_phrases:
                query_vec = self.embedder.embed_text(clean_input)
                for phrase in block.trigger_phrases:
                    p_vec = self.embedder.embed_text(phrase)
                    score = float(self.embedder.compute_similarity(query_vec, p_vec))
                    if score >= 0.65:
                        return block, destination_place
            elif not block.trigger_phrases:
                return block, destination_place

        return None
