"""Acción narrativa de inspección o explicación detallada de una entidad."""

from __future__ import annotations
from typing import Any, Dict, Optional, Tuple, Type
from domains import (
    Entity,
    ExplainLookNarratorCtx,
    ExplainLookResponse,
)
from engines.game.actions.base_action import BaseAction
from engines.game.state_controller import GameStateController
from engines.game.utils import MarkdownFormatter


class LookAction(BaseAction[ExplainLookNarratorCtx, ExplainLookResponse]):
    """Acción de inspección: describe y explica entidades o lugares."""

    def __init__(
        self,
        target: Optional[str] = None,
        failed_reason: Optional[str] = None,
        directive: Optional[str] = None,
    ):
        self.target = target
        self.failed_reason = failed_reason
        self.directive = directive

    @property
    def rules_path(self) -> str:
        return r"Resources/system_data/rules/explain_look.md"

    @property
    def response_model(self) -> Type[ExplainLookResponse]:
        return ExplainLookResponse

    @property
    def profile_name(self) -> str:
        return "explain_look_narrator"

    def get_template_tags(self, ctx: ExplainLookNarratorCtx) -> Dict[str, str]:
        return MarkdownFormatter.explain_look_tags(ctx)

    def to_markdown(self, ctx: ExplainLookNarratorCtx) -> str:
        return MarkdownFormatter.explain_look_markdown(ctx)

    def _resolve_entity(self, controller: GameStateController) -> Optional[Entity]:
        target = self.target
        if not target or target == controller.game_state.current_location:
            return controller.game_state.place

        if target in controller.places_by_id:
            return controller.places_by_id[target]

        if target in controller.npcs_by_id:
            return controller.npcs_by_id[target]

        if target in controller.items_by_id:
            return controller.items_by_id[target]

        return None

    def build_context(
        self,
        controller: GameStateController,
        player_input: str = "",
    ) -> ExplainLookNarratorCtx:
        entity = self._resolve_entity(controller)
        return ExplainLookNarratorCtx(
            entity=entity,
            inspection_history=[],
            player_input=player_input,
            directive=self.directive,
            failed_reason=self.failed_reason,
        )

    def fallback_narrative(self, controller: GameStateController, ctx: ExplainLookNarratorCtx) -> Tuple[str, Any]:
        if self.failed_reason:
            return f"No es posible observar '{self.target}': {self.failed_reason}", None

        p = controller.game_state.place
        target = self.target
        if not target or target == controller.game_state.current_location:
            desc = p.description if p else "Un lugar sin descripción."
            name = p.name if p else target
            return f"Miras a tu alrededor en {name}: {desc}", None

        if target in controller.places_by_id:
            pl = controller.places_by_id[target]
            return f"Observas {pl.name}: {pl.description}", None

        if target in controller.npcs_by_id:
            npc = controller.npcs_by_id[target]
            return f"Observas a {npc.name}: {npc.description}", None

        if target in controller.items_by_id:
            it = controller.items_by_id[target]
            return f"Examinas {it.name}: {it.description}", None

        return f"Observas '{target}', pero no distingues detalles relevantes.", None
