from domains.base import Entity
from domains.world import World, Location, Place, LocationInfo, PlaceInfo
from domains.player import Player
from domains.npcs import NPC, Service, NPCMotivations, LoreBlock, NPCInfo
from domains.conversation import ConversationRecord
from domains.system.system_domains import (
    ContextType,
    ResponseType,
    ResultType,
    GameState,
    RuntimeState,
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
    MoveNarratorCtx,
    MoveNarratorResponse,
    MoveNarratorResult,
    ExplainLookNarratorCtx,
    ExplainLookResponse,
    ExplainLookResult,
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
    "ContextType",
    "ResponseType",
    "ResultType",
    "GameState",
    "RuntimeState",

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
