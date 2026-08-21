from typing import Optional, List
from game_engine.state import WorldState, GameStateController
from game_engine.evaluator import ActionEvaluator, EvaluationResult
from game_engine.mutator import GameStateMutator
from game_engine.context_builder import ContextBuilder
from domains import NPC, Service, ActionResponse, DialogueResponse, TurnSummary

class GameEngine:
    """Clase orquestadora principal (Fachada) que coordina las reglas, mutaciones y contextos del juego."""

    def __init__(self, world_json_path: str, npcs_json_path: str, player_json_path: str):
        # 1. Cargar el estado inicial del mundo
        self.world_state = WorldState(world_json_path, npcs_json_path, player_json_path)
        
        # 2. Inicializar la proyección del GameState
        self.game_state_controller = GameStateController.create_from_world(self.world_state)
        
        # 3. Guardar instancias de las clases de soporte
        self.evaluator = ActionEvaluator()
        self.mutator = GameStateMutator()
        self.context_builder = ContextBuilder()

    def get_npc_by_name_or_id(self, target: str) -> Optional[NPC]:
        """Busca un NPC por su ID o su nombre en el estado del mundo."""
        if target in self.world_state.npcs:
            return self.world_state.npcs[target]
        elif target in self.world_state.npcs_by_name:
            return self.world_state.npcs_by_name[target]
        return None

    # =====================================================================
    # INTERFAZ DE PROCESAMIENTO Y MUTACIÓN
    # =====================================================================

    def process_action(self, action: ActionResponse, player_input: str) -> EvaluationResult:
        """Evalúa y ejecuta una acción clasificada en modo normal (MOVE, TALK, LOOK, EXPLAIN)."""
        # 1. Evaluar viabilidad
        eval_result = self.evaluator.evaluate_action(
            world_state=self.world_state,
            game_state=self.game_state_controller.data,
            action=action
        )

        # 2. Mutar el estado si es permitido
        if eval_result.allowed:
            self.mutator.mutate_action(
                world_state=self.world_state,
                game_state_controller=self.game_state_controller,
                action=action,
                eval_result=eval_result
            )
            # Guardamos para sincronizar con world_state
            self.save()
            # Re-inicializar el campo de visión / percepción para asegurar total consistencia
            current_target = self.game_state_controller.data.player_target
            current_prev_turns = self.game_state_controller.data.prev_turns
            self.game_state_controller = GameStateController.create_from_world(self.world_state, prev_turns=current_prev_turns)
            self.game_state_controller.data.player_target = current_target

        return eval_result

    def process_dialogue(self, dialogue: DialogueResponse, player_input: str) -> EvaluationResult:
        """Procesa y aplica las consecuencias de un turno de diálogo (mensajes, servicios, afinidad)."""
        target_npc_name = self.game_state_controller.data.player_target
        npc = self.get_npc_by_name_or_id(target_npc_name)
        
        if not npc:
            return EvaluationResult(allowed=False, reason=f"No hay una conversación activa con ningún NPC válido (actual: '{target_npc_name}').")

        # 1. Procesar servicio si el LLM indicó que se está brindando uno
        service_eval = None
        if dialogue.service:
            service_eval = self.evaluator.evaluate_dialogue_service(
                game_state=self.game_state_controller.data,
                npc=npc,
                service_id=dialogue.service
            )
            if service_eval.allowed:
                service = service_eval.metadata.get("service")
                if service:
                    self.mutator.apply_service(self.game_state_controller, npc, service)

        # 2. Registrar el mensaje en el historial del NPC
        self.mutator.record_conversation(npc, player_input, dialogue.msg)

        # 3. Registrar el turno en el historial del jugador
        self.mutator.add_turn_to_history(self.game_state_controller, player_input, dialogue.msg)

        # 4. Actualizar el estado de diálogo (ej. volver a exploración NORMAL si cerró)
        if dialogue.state:
            self.mutator.mutate_dialogue_state(self.game_state_controller, dialogue.state)

        # Retornar el resultado de la transacción del servicio (si hubo una) o éxito general
        return service_eval if service_eval is not None else EvaluationResult(allowed=True)

    def change_npc_affinity(self, npc_name_or_id: str, delta: float):
        """Modifica externamente la afinidad de un NPC."""
        npc = self.get_npc_by_name_or_id(npc_name_or_id)
        if npc:
            self.mutator.modify_affinity(npc, delta)

    def save(self):
        """Sincroniza y persiste los cambios del controlador de vuelta al WorldState."""
        self.game_state_controller.save(self.world_state)

    # =====================================================================
    # GENERACIÓN DE CONTEXTO EN MARKDOWN
    # =====================================================================

    def get_classifier_context_markdown(self, player_input: str) -> str:
        """Devuelve el Markdown para el Clasificador semántico."""
        return self.context_builder.build_classifier_context(
            world_state=self.world_state,
            game_state=self.game_state_controller.data,
            player_input=player_input
        )

    def get_narrative_context_markdown(self, player_input: str) -> str:
        """Devuelve el Markdown detallado del lugar y NPCs para el Narrador."""
        return self.context_builder.build_narrative_context(
            world_state=self.world_state,
            game_state=self.game_state_controller.data,
            player_input=player_input
        )

    def get_dialogue_context_markdown(self, player_input: str) -> str:
        """Devuelve el Markdown de diálogo del NPC activo con sus servicios/lore desbloqueados."""
        target_npc_name = self.game_state_controller.data.player_target
        npc = self.get_npc_by_name_or_id(target_npc_name)
        if not npc:
            return "## ERROR\nNo hay una conversación activa."
            
        return self.context_builder.build_dialogue_context(
            world_state=self.world_state,
            game_state=self.game_state_controller.data,
            npc=npc,
            player_input=player_input
        )
