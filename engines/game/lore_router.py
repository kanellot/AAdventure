"""Enrutador semántico y evaluador de condiciones de Lore Dinámico."""

import logging
from typing import Optional, Tuple
from domains import Entity, LoreBlock, LoreConditions, NPC, Player
from engines.embedding import BaseEmbeddingBackend, EmbeddingFactory
from engines.game.state_controller import GameStateController

logger = logging.getLogger(__name__)


class LoreRouter:
    """Coordina la lógica determinista del Game Engine con la detección semántica por embeddings."""

    _instance: Optional["LoreRouter"] = None

    @classmethod
    def get_instance(cls) -> "LoreRouter":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self, embedding_backend: Optional[BaseEmbeddingBackend] = None):
        self.embedder = embedding_backend or EmbeddingFactory.get_backend()

    def check_conditions(
        self,
        conditions: LoreConditions,
        game_state: GameStateController,
        npc: Optional[NPC] = None,
    ) -> bool:
        """Verifica si se cumplen las condiciones lógicas y de estado del juego."""
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

    def find_proactive_lore(
        self,
        entity: Entity,
        game_state: GameStateController,
        npc: Optional[NPC] = None,
    ) -> Optional[LoreBlock]:
        """Busca un bloque de lore con iniciativa proactiva que cumpla condiciones."""
        if not hasattr(entity, "dynamic_lore") or not entity.dynamic_lore:
            return None

        for block in entity.dynamic_lore:
            if block.trigger_mode == "proactive":
                if block.once and block.revealed:
                    continue
                if self.check_conditions(block.conditions, game_state, npc):
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
        """Evalúa si la entrada del jugador activa un bloque reactivo por similitud."""
        if not hasattr(entity, "dynamic_lore") or not entity.dynamic_lore:
            return None

        clean_input = player_input.strip()
        if not clean_input:
            return None

        def _get_specificity(b: LoreBlock) -> int:
            c = b.conditions
            return (
                len(c.required_items) * 100
                + len(c.required_quests) * 50
                + (20 if c.required_gold > 0 else 0)
                + int(c.min_affinity * 10)
            )

        best_block: Optional[LoreBlock] = None
        best_score: float = 0.0
        best_raw_score: float = 0.0

        for block in entity.dynamic_lore:
            if block.trigger_mode != "reactive":
                continue
            if block.once and block.revealed:
                continue
            if not block.trigger_phrases:
                continue

            if not self.check_conditions(block.conditions, game_state, npc):
                continue

            score, _ = self.embedder.compute_max_similarity(clean_input, block.trigger_phrases)
            if score >= threshold:
                weighted_score = score + (_get_specificity(block) * 0.002)
                if weighted_score > best_score:
                    best_score = weighted_score
                    best_raw_score = score
                    best_block = block

        if best_block is not None:
            return best_block, best_raw_score

        return None

    def apply_effects(
        self,
        block: LoreBlock,
        game_state: GameStateController,
        npc: Optional[NPC] = None,
    ) -> dict:
        """Aplica las mutaciones del bloque activado al estado de juego."""
        mutations = {}
        player = game_state.data.player

        if block.once:
            block.revealed = True
            mutations["revealed"] = True

        effects = block.effects

        if effects.give_gold > 0 and player:
            player.gold += effects.give_gold
            mutations["gold_gained"] = effects.give_gold

        if effects.take_gold > 0 and player:
            taken = min(player.gold, effects.take_gold)
            player.gold -= taken
            mutations["gold_spent"] = taken

        if player:
            if not hasattr(player, "inventory") or player.inventory is None:
                player.inventory = []

            for item in effects.give_items:
                if item not in player.inventory:
                    player.inventory.append(item)
                    mutations.setdefault("items_received", []).append(item)

            for item in effects.take_items:
                if item in player.inventory:
                    player.inventory.remove(item)
                    mutations.setdefault("items_removed", []).append(item)

        if npc is not None and effects.affinity_delta != 0.0:
            npc.affinity = round(max(0.0, min(1.0, npc.affinity + effects.affinity_delta)), 4)
            mutations["affinity_delta"] = effects.affinity_delta
            mutations["new_affinity"] = npc.affinity

        if effects.unlock_quests and player:
            for q in effects.unlock_quests:
                if q not in player.completed_quests and player.active_quest != q:
                    player.active_quest = q
                    mutations.setdefault("quests_unlocked", []).append(q)

        if effects.unlock_places:
            for p in effects.unlock_places:
                if hasattr(player, "unlocked_places"):
                    if p not in player.unlocked_places:
                        player.unlocked_places.append(p)
                mutations.setdefault("places_unlocked", []).append(p)

        return mutations

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
        """Enruta la búsqueda de lore en inspección reactiva."""
        reactive = self.find_reactive_lore(player_input, entity, game_state, npc=None)
        if reactive:
            return reactive[0]
        return None
