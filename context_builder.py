from typing import TYPE_CHECKING
from domains import PlayerState, Actions, NarrativeContext, Place, NPC

if TYPE_CHECKING:
    from game_state import WorldState


class ContextBuilder:
    """Clase encargada de construir el contexto estructurado para el generador de narrativa."""

    @staticmethod
    def build_narrative_context(
        prev_state: PlayerState,
        curr_state: PlayerState,
        executed_actions: Actions,
        player_input: str,
        world_state: "WorldState"
    ) -> NarrativeContext:
        """Construye un objeto NarrativeContext a partir de los estados y la información global.

        Args:
            prev_state: Estado del jugador antes de la acción.
            curr_state: Estado del jugador después de la acción.
            executed_actions: Acción o acciones que acaban de ser ejecutadas.
            player_input: Texto de entrada proporcionado por el jugador.
            world_state: Estado completo del mundo (contiene NPCs e índices de lugares).

        Returns:
            NarrativeContext: Objeto de contexto listo para la generación narrativa.
        """
        # 1. Obtener los objetos Place completos (origen y destino)
        prev_place = None
        if prev_state.current_place:
            prev_place = world_state.places_by_name.get(prev_state.current_place.name)

        curr_place = None
        if curr_state.current_place:
            curr_place = world_state.places_by_name.get(curr_state.current_place.name)

        # 2. Recopilar NPCs visibles relevantes de ambos lugares
        relevant_npc_ids = set()
        if prev_place:
            relevant_npc_ids.update(prev_place.visible_entities)
        if curr_place:
            relevant_npc_ids.update(curr_place.visible_entities)

        npcs_context = {}
        for npc_id in relevant_npc_ids:
            if npc_id in world_state.npcs:
                npcs_context[npc_id] = world_state.npcs[npc_id]

        return NarrativeContext(
            previous_player_state=prev_state,
            current_player_state=curr_state,
            previous_place=prev_place,
            current_place=curr_place,
            npcs_context=npcs_context,
            player_input=player_input,
            executed_actions=executed_actions
        )
