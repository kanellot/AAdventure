"""Cálculo y gestión del tiempo transcurrido en el mundo de juego."""

from typing import Any, Dict, List, Optional
from domains.world import Connection, Place
from engines.game.utils.path_calculator import PathCalculator


class TimeCalculator:
    """Calculador y gestor del tiempo transcurrido en el mundo de juego."""

    DEFAULT_TERRAIN_MODIFIERS: Dict[str, float] = {
        "village": 0.0,
        "road": 0.0,
        "forest": -1.5,
        "mountain": -2.5,
        "swamp": -3.0,
    }

    @classmethod
    def calculate_travel_time(
        cls,
        connections: List[Connection],
        travel_speed: float = 4.5,
        terrain_modifiers: Optional[Dict[str, float]] = None,
    ) -> int:
        """Calcula el tiempo de viaje total en minutos para una secuencia de conexiones."""
        if not connections:
            return 0

        modifiers = terrain_modifiers if terrain_modifiers is not None else cls.DEFAULT_TERRAIN_MODIFIERS
        total_time_minutes = 0.0

        for conn in connections:
            terrain_type = conn.terrain_type.lower()
            terrain_mod = modifiers.get(terrain_type, 0.0)
            true_travel_speed = travel_speed + terrain_mod
            if true_travel_speed < 0.1:
                true_travel_speed = 0.1

            conn_time = (conn.distance / 1000.0) / true_travel_speed * 60.0
            total_time_minutes += conn_time

        return max(1, round(total_time_minutes))

    @classmethod
    def calculate_travel_time_between_places(
        cls,
        places: Dict[str, Place],
        start_name_or_id: str,
        end_name_or_id: str,
        travel_speed: float = 4.5,
        terrain_modifiers: Optional[Dict[str, float]] = None,
    ) -> int:
        """Calcula el tiempo total de viaje en minutos entre dos lugares."""
        connections, _ = PathCalculator.find_shortest_path(places, start_name_or_id, end_name_or_id)
        if not connections:
            return 0
        return cls.calculate_travel_time(
            connections,
            travel_speed=travel_speed,
            terrain_modifiers=terrain_modifiers,
        )

    @staticmethod
    def calculate_dialogue_time(turns: int = 1, minutes_per_turn: int = 1) -> int:
        """Calcula el tiempo consumido por una interacción de diálogo."""
        return max(0, turns * minutes_per_turn)

    @classmethod
    def add_dialogue_time(cls, game_state_controller: Any, minutes: int = 1) -> int:
        """Incrementa el tiempo transcurrido en el GameState por una interacción de diálogo."""
        consumed = cls.calculate_dialogue_time(turns=1, minutes_per_turn=minutes)
        if hasattr(game_state_controller, "data") and hasattr(game_state_controller.data, "state"):
            game_state_controller.data.state.elapsed_time += consumed
            return game_state_controller.data.state.elapsed_time
        return consumed

    @staticmethod
    def format_elapsed_time(elapsed_minutes: int) -> str:
        """Formatea minutos transcurridos en representación de rol: 'Día X, HH:MM'."""
        days = elapsed_minutes // 1440
        hours = (elapsed_minutes // 60) % 24
        minutes = elapsed_minutes % 60
        return f"Día {days}, {hours:02d}:{minutes:02d}"

