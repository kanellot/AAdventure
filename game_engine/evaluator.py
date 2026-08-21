from typing import Optional, Dict, Any
from domains import NPC, Service, ActionResponse, DialogueResponse, GameState, World

class EvaluationResult:
    """Contiene el resultado de evaluar una acción o transacción del juego."""
    def __init__(self, allowed: bool, reason: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
        self.allowed = allowed
        self.reason = reason
        self.metadata = metadata or {}

    def __repr__(self):
        return f"EvaluationResult(allowed={self.allowed}, reason={self.reason}, metadata={self.metadata})"


class ActionEvaluator:
    """Clase responsable de validar que las acciones propuestas por el LLM o el jugador sean válidas."""

    @staticmethod
    def evaluate_action(world_state, game_state: GameState, action: ActionResponse) -> EvaluationResult:
        """Evalúa si una acción de exploración normal se puede llevar a cabo."""
        if not action.action:
            return EvaluationResult(allowed=False, reason="No se ha especificado ninguna acción.")

        action_type = action.action.upper()
        target = action.target[0] if action.target else None

        if action_type == "MOVE":
            if not target:
                return EvaluationResult(allowed=False, reason="No se ha especificado un destino para moverse.")

            # Buscar el lugar actual del jugador en el mundo
            current_place = game_state.current_place
            if not current_place:
                return EvaluationResult(allowed=False, reason="El jugador no se encuentra en una ubicación válida.")

            # Buscar el destino
            dest_place = None
            if target in world_state.places_by_id:
                dest_place = world_state.places_by_id[target]
            elif target in world_state.places_by_name:
                dest_place = world_state.places_by_name[target]

            if not dest_place:
                return EvaluationResult(allowed=False, reason=f"El destino '{target}' no existe.")

            return EvaluationResult(allowed=True, metadata={"target_place": dest_place})

        elif action_type == "TALK":
            if not target:
                return EvaluationResult(allowed=False, reason="No se ha especificado con quién hablar.")

            # Buscar si el NPC existe
            npc = None
            if target in world_state.npcs:
                npc = world_state.npcs[target]
            elif target in world_state.npcs_by_name:
                npc = world_state.npcs_by_name[target]

            if not npc:
                return EvaluationResult(allowed=False, reason=f"El personaje '{target}' no existe.")

            return EvaluationResult(allowed=True, metadata={"target_npc": npc})

        # EXPLAIN y LOOK siempre están permitidos (son de observación)
        elif action_type in ["EXPLAIN", "LOOK"]:
            return EvaluationResult(allowed=True)

        return EvaluationResult(allowed=False, reason=f"Tipo de acción '{action_type}' desconocido.")

    @staticmethod
    def evaluate_dialogue_service(game_state: GameState, npc: NPC, service_id: str) -> EvaluationResult:
        """Evalúa si el jugador califica para comprar/recibir un servicio de un NPC."""
        # Buscar el servicio en el NPC
        service = next((s for s in npc.services if s.id == service_id), None)
        if not service:
            return EvaluationResult(allowed=False, reason=f"El servicio '{service_id}' no es ofrecido por {npc.name}.")

        # 1. Comprobar rango de afinidad
        current_affinity = npc.affinity
        if current_affinity < service.min_affinity or current_affinity > service.max_affinity:
            return EvaluationResult(
                allowed=False,
                reason=f"Tu afinidad con {npc.name} ({current_affinity:.2f}) no está en el rango requerido ({service.min_affinity} - {service.max_affinity}) para este servicio."
            )

        # 2. Comprobar oro
        if service.cost is not None and game_state.gold < service.cost:
            return EvaluationResult(
                allowed=False,
                reason=f"No tienes suficiente oro para el servicio '{service.description}'. Se requiere {service.cost} oro, pero tienes {game_state.gold}."
            )

        return EvaluationResult(allowed=True, metadata={"service": service})
