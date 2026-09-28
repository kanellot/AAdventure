"""Paquete de acciones narrativas del motor de juego."""

from engines.game.actions.base_action import BaseAction
from engines.game.actions.dialogue_action import (
    DialogueAction,
    DialogueNPCInfo,
    DialogueNarratorCtx,
    DialogueNarratorResponse,
)
from engines.game.actions.look_action import LookAction
from engines.game.actions.move_action import MoveAction

__all__ = [
    "BaseAction",
    "MoveAction",
    "DialogueAction",
    "DialogueNPCInfo",
    "DialogueNarratorCtx",
    "DialogueNarratorResponse",
    "LookAction",
]
