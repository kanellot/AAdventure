"""Acción narrativa de desplazamiento."""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple, Type
from domains import MoveNarratorCtx, MoveNarratorResponse, Place
from engines.game.actions.base_action import BaseAction
from engines.game.state_controller import GameStateController
from engines.game.utils import MarkdownFormatter


class MoveAction(BaseAction[MoveNarratorCtx, MoveNarratorResponse]):
    """Acción de desplazamiento: construye contexto y genera narrativa de viaje."""

    def __init__(
        self,
        origin_place: Optional[Place],
        destination_place: Optional[Place],
        path_taken: Optional[List[Place]] = None,
        travel_time: int = 0,
        directive: Optional[str] = None,
        blocked_place: Optional[Place] = None,
    ):
        self.origin_place = origin_place
        self.destination_place = destination_place
        self.path_taken = list(path_taken or [])
        self.travel_time = travel_time
        self.directive = directive
        self.blocked_place = blocked_place

    @property
    def rules_path(self) -> str:
        return r"Resources/system_data/rules/exploration_move.md"

    @property
    def response_model(self) -> Type[MoveNarratorResponse]:
        return MoveNarratorResponse

    @property
    def profile_name(self) -> str:
        return "move_narrator"

    def get_template_tags(self, ctx: MoveNarratorCtx) -> Dict[str, str]:
        return MarkdownFormatter.move_tags(ctx)

    def to_markdown(self, ctx: MoveNarratorCtx) -> str:
        return MarkdownFormatter.move_markdown(ctx)

    def build_context(
        self,
        controller: GameStateController,
        player_input: str = "",
    ) -> MoveNarratorCtx:
        return MoveNarratorCtx(
            origin_place=self.origin_place,
            destination_place=self.destination_place,
            player_input=player_input,
            path_taken=self.path_taken,
            estimated_travel_time=self.travel_time,
            directive=self.directive,
        )

    def fallback_narrative(self, controller: GameStateController, ctx: MoveNarratorCtx) -> Tuple[str, Any]:
        dest_name = self.destination_place.name if self.destination_place else "tu destino"
        desc = self.destination_place.description if self.destination_place else ""

        if self.blocked_place:
            msg = (
                f"Avanzas por el camino hasta llegar a {dest_name}. "
                f"Sin embargo, el paso hacia '{self.blocked_place.name}' se encuentra bloqueado. "
                f"{desc}"
            )
        else:
            msg = f"Llegas a {dest_name}. {desc}"

        return msg.strip(), None
