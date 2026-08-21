from domains.base import Entity
from domains.world import World, Location, Place
from domains.player import Player
from domains.npcs import NPC, Service, NPCMotivations, LoreBlock
from domains.conversation import ConversationRecord
from domains.system.system_domains import (
    GameState,
    NPCProjection,
    PlaceProjection,
    TurnSummary,
    ActionResponse,
    ActionCtx,
    NarrativeCtx,
    NarrativeContext,
    NarrativeResponse,
    DialogueCtx,
    DialogueContext,
    DialogueResponse,
    MarkdownContext,
)

Action_ctx = ActionCtx

__all__ = [
    "Entity",
    "World",
    "Location",
    "Place",
    "Player",
    "NPC",
    "Service",
    "NPCMotivations",
    "LoreBlock",
    "ConversationRecord",
    "GameState",
    "NPCProjection",
    "PlaceProjection",
    "TurnSummary",
    "ActionResponse",
    "ActionCtx",
    "Action_ctx",
    "NarrativeCtx",
    "NarrativeContext",
    "NarrativeResponse",
    "DialogueCtx",
    "DialogueContext",
    "DialogueResponse",
    "MarkdownContext",
]
