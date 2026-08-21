from typing import Optional
from domains import NPC, Service, ActionResponse, DialogueResponse, ConversationRecord, TurnSummary
from game_engine.evaluator import EvaluationResult

class GameStateMutator:
    """Clase responsable de mutar de forma segura el GameState y WorldState basados en acciones válidas."""

    @staticmethod
    def mutate_action(world_state, game_state_controller, action: ActionResponse, eval_result: EvaluationResult):
        """Aplica los cambios al estado del juego tras una acción del clasificador."""
        if not eval_result.allowed:
            return

        action_type = action.action.upper()

        if action_type == "MOVE":
            target_place = eval_result.metadata.get("target_place")
            if target_place:
                game_state_controller.update_location(target_place.name, world_state)

        elif action_type == "TALK":
            target_npc = eval_result.metadata.get("target_npc")
            if target_npc:
                game_state_controller.update_state("TALK")
                game_state_controller.data.player_target = target_npc.name
                
                # Buscar la ubicación del NPC en el mundo y mover al jugador allí
                npc_place = None
                for place in world_state.places_by_id.values():
                    if target_npc.id in place.visible_entities:
                        npc_place = place
                        break
                if npc_place:
                    game_state_controller.update_location(npc_place.name, world_state)
            else:
                game_state_controller.data.player_target = ""

    @staticmethod
    def mutate_dialogue_state(game_state_controller, next_state: str):
        """Actualiza el estado de la conversación (ej. volver a NORMAL si terminó)."""
        state_upper = next_state.upper()
        if state_upper == "NORMAL":
            game_state_controller.update_state("NORMAL")
            game_state_controller.data.player_target = ""

    @staticmethod
    def apply_service(game_state_controller, npc: NPC, service: Service):
        """Aplica la compra/adquisición de un servicio (descuenta oro y activa misiones)."""
        # Descontar el coste en oro del jugador
        if service.cost is not None:
            game_state_controller.data.gold -= service.cost

        # Si el servicio es de tipo QUEST (misión), asignarla
        if service.type.upper() == "QUEST":
            game_state_controller.data.active_quest = service.id

    @staticmethod
    def modify_affinity(npc: NPC, delta: float):
        """Modifica la afinidad de un NPC, manteniéndola acotada entre 0.0 y 1.0."""
        npc.affinity = round(max(0.0, min(1.0, npc.affinity + delta)), 4)

    @staticmethod
    def record_conversation(npc: NPC, player_input: str, npc_response: str):
        """Registra el intercambio de diálogos en el historial específico del NPC."""
        if not npc.conversation:
            npc.conversation = ConversationRecord(id=f"c_{npc.id}", msg=[])
        npc.conversation.msg.append({"Player": player_input})
        npc.conversation.msg.append({"Npc": npc_response})

    @staticmethod
    def add_turn_to_history(game_state_controller, player_input: str, response_text: str):
        """Añade el turno al historial de turnos generales (últimos 4 turnos)."""
        game_state_controller.data.prev_turns.append(
            TurnSummary(player_input=player_input, narration=response_text)
        )
        game_state_controller.data.prev_turns = game_state_controller.data.prev_turns[-4:]
