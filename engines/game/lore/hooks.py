"""Resolución determinista de directivas hook para inyección contextual en la narrativa."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from engines.game.lore.library import LoreLibrary
from engines.game.state_controller import GameStateController


@dataclass
class ResolvedHook:
    """Resultado de la resolución de un hook pasivo."""

    directive: str
    bypass_llm: bool = False
    bypass_author: Optional[str] = None
    block_id: Optional[str] = None


class HookResolver:
    """Resuelve la directiva de hook ganadora para la interacción actual."""

    @classmethod
    def resolve_hook(
            cls,
            transition_hooks: List[Tuple[str, Dict[str, Any]]],
            armed_hooks: List[Tuple[str, Dict[str, Any]]],
            active_entity_id: Optional[str],
            action_name: str,
            library: LoreLibrary,
            ctrl: GameStateController,
    ) -> Optional[ResolvedHook]:
        """Busca el hook aplicable según target, interacción y prioridad jerárquica.

        Reglas:
        - Solo se dispara si la acción es interactiva ('LOOK' o 'TALK') y hay active_entity_id.
        - Prioridad 1: Hooks de transición única del ciclo actual (ej. RAG antenna hit en done_effects).
        - Prioridad 2: Hooks armados persistentes de bloques activos (active_effects).
        - Desempate: Mayor profundidad jerárquica en LoreLibrary ('el bloque más hijo').
        """
        if not active_entity_id or action_name not in ("LOOK", "TALK"):
            return None

        # 1. Candidatos de transición (máxima prioridad)
        trans_candidates = [
            (bid, eff) for (bid, eff) in transition_hooks
            if (eff.get("action") == "hook" or not eff.get("action"))
            and eff.get("target") == active_entity_id
            and bool(eff.get("directive"))
        ]

        # 2. Candidatos armados
        armed_candidates = [
            (bid, eff) for (bid, eff) in armed_hooks
            if (eff.get("action") == "hook" or not eff.get("action"))
            and eff.get("target") == active_entity_id
            and bool(eff.get("directive"))
        ]

        winner_bid: Optional[str] = None
        winner_eff: Optional[Dict[str, Any]] = None

        if trans_candidates:
            # Ordenar por profundidad descendente
            trans_candidates.sort(key=lambda item: library.get_depth(item[0]), reverse=True)
            winner_bid, winner_eff = trans_candidates[0]
        elif armed_candidates:
            armed_candidates.sort(key=lambda item: library.get_depth(item[0]), reverse=True)
            winner_bid, winner_eff = armed_candidates[0]

        if not winner_eff:
            return None

        directive = str(winner_eff.get("directive", ""))
        bypass_llm = bool(winner_eff.get("bypass_llm", False))

        bypass_author: Optional[str] = None
        tgt = winner_eff.get("target")
        if tgt and tgt in ctrl.npcs_by_id:
            bypass_author = ctrl.npcs_by_id[tgt].name
        else:
            bypass_author = "Dungeon Master"

        return ResolvedHook(
            directive=directive,
            bypass_llm=bypass_llm,
            bypass_author=bypass_author,
            block_id=winner_bid,
        )
