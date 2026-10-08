"""Submódulo engines.game: lógica, acciones y estado de juego."""

from domains import ActionCommandProjection, ResultType, TurnResultProjection
from engines.game.engine import GameEngine
from engines.game.prompt_builder import PromptBuilder
from engines.game.state_controller import GameStateController
from engines.game.world import WorldState

__all__ = [
    "GameEngine",
    "TurnResultProjection",
    "WorldState",
    "GameStateController",
    "PromptBuilder",
    "ActionCommandProjection",
    "ResultType",
]
