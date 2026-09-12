"""Exportación de modelos de dominio para AAdventure."""

from domains.base import Entity
from domains.conversation import ConversationRecord
from domains.lore import LoreBlock, LoreConditions, LoreEffects
from domains.npcs import NPC, NPCInfo, NPCMotivations, Service
from domains.player import Player
from domains.system.system_domains import (
    ActionCommand,
    ContextType,
    ExplainLookNarratorCtx,
    ExplainLookResponse,
    ExplainLookResult,
    GameState,
    MoveNarratorCtx,
    MoveNarratorResponse,
    MoveNarratorResult,
    PlaceProjection,
    ResponseType,
    ResultType,
    RuntimeState,
)
from domains.world import Connection, Location, LocationInfo, Place, PlaceInfo, World

__all__ = [
    "Entity",
    "World",
    "Location",
    "Place",
    "Connection",
    "Player",
    "NPC",
    "Service",
    "NPCMotivations",
    "LoreBlock",
    "LoreConditions",
    "LoreEffects",
    "ConversationRecord",
    "ContextType",
    "ResponseType",
    "ResultType",
    "GameState",
    "RuntimeState",
    "PlaceProjection",
    "ActionCommand",
    "LocationInfo",
    "PlaceInfo",
    "NPCInfo",
    "MoveNarratorCtx",
    "MoveNarratorResponse",
    "MoveNarratorResult",
    "ExplainLookNarratorCtx",
    "ExplainLookResponse",
    "ExplainLookResult",
]
