from typing import TYPE_CHECKING
from domains import (
    GameState,
    Place,
    NPC,
    ActionCtx,
    PlaceProjection,
    NPCProjection,
    NarrativeCtx,
    NarrativeContext,
    DialogueCtx,
    DialogueContext,
)

if TYPE_CHECKING:
    from game_data import WorldState


class ContextBuilder:
    """Clase encargada de construir los contextos estructurados para el clasificador, narrador y diálogo."""

    @staticmethod
    def build_action_ctx(
        world_state: "WorldState",
        player_input: str
    ) -> ActionCtx:
        """Construye un objeto ActionCtx con la lista de todos los lugares y NPCs del mundo."""
        places_proj = [
            PlaceProjection(id=p.id, name=p.name)
            for p in world_state.places_by_id.values()
        ]
        npc_proj = [
            NPCProjection(id=n.id, name=n.name)
            for n in world_state.npcs.values()
        ]
        return ActionCtx(
            places=places_proj,
            npc=npc_proj,
            player_input=player_input
        )

    @staticmethod
    def build_narrative_ctx(
        world_state: "WorldState",
        current_place_name: str,
        player_input: str
    ) -> NarrativeContext:
        """Construye un NarrativeContext conteniendo NarrativeCtx y la entrada del jugador."""
        curr_place = world_state.places_by_name.get(current_place_name)
        
        visible_npcs = []
        if curr_place:
            for entity_id in curr_place.visible_entities:
                if entity_id in world_state.npcs:
                    visible_npcs.append(world_state.npcs[entity_id])

        narrative_ctx = NarrativeCtx(
            current_place=curr_place,
            visible_npcs=visible_npcs
        )
        return NarrativeContext(
            narrative_ctx=narrative_ctx,
            player_input=player_input
        )

    @staticmethod
    def build_dialogue_ctx(
        npc: NPC,
        player_input: str
    ) -> DialogueContext:
        """Construye un DialogueContext conteniendo DialogueCtx y la entrada del jugador."""
        dialogue_ctx = DialogueCtx(
            npc=npc,
            conversation=npc.conversation
        )
        return DialogueContext(
            dialogue_ctx=dialogue_ctx,
            player_input=player_input
        )
