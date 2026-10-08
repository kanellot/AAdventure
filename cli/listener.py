"""Listener de eventos para la interfaz de consola interactiva CLI."""

from __future__ import annotations

import logging
from typing import Any, Optional

from cli.formatter import CLIFormatter, Colors
from domains.projections import TurnResultProjection, UIStateProjection
from engines.events import PopupEvent, ThinkingEvent
from engines.listeners import BaseEngineEventListener

logger = logging.getLogger(__name__)


class CLIEventListener(BaseEngineEventListener):
    """Observador del motor para el cliente de consola.

    Recibe y renderiza eventos en la terminal, desacoplando la interacción de la lógica del motor.
    """

    def __init__(self, session: Any, verbose: bool = False):
        self.session = session
        self.verbose = verbose
        self.latest_ui_state: Optional[UIStateProjection] = None
        self.latest_turn_result: Optional[TurnResultProjection] = None

    def on_thinking_changed(self, event_json: str) -> None:
        event = ThinkingEvent.model_validate_json(event_json)
        if event.is_thinking and event.source == "LORE":
            print(f"\n{Colors.DIM}[*] [Simulación LoreBlock en curso: {event.action} -> {event.target}]...{Colors.ENDC}")

    def on_popup(self, popup_json: str) -> None:
        event = PopupEvent.model_validate_json(popup_json)
        title = event.title or "Aviso del Sistema"
        msg = event.message
        box_width = max(len(title) + 16, len(msg) + 4, 30)
        print(f"\n{Colors.WARNING}{Colors.BOLD}+{'=' * box_width}+{Colors.ENDC}")
        print(f"{Colors.WARNING}{Colors.BOLD}|  {title.upper()}  |{Colors.ENDC}")
        print(f"{Colors.WARNING}   {msg}{Colors.ENDC}")
        print(f"{Colors.WARNING}{Colors.BOLD}+{'=' * box_width}+{Colors.ENDC}\n")

    def on_task_completed(self, task_id: str, result_json: str) -> None:
        result = TurnResultProjection.model_validate_json(result_json)
        self.latest_turn_result = result
        CLIFormatter.print_turn_result(result)

        if self.verbose and getattr(result, "debug", None):
            try:
                CLIFormatter.print_verbose_debug(
                    turn_result=result,
                    game_state=self.session.get_game_state(),
                    lore_graph=self.session.get_lore_graph(),
                )
            except Exception as e:
                logger.debug("Error al imprimir verbose debug: %s", e)

    def on_state_updated(self, ui_state_json: str) -> None:
        self.latest_ui_state = UIStateProjection.model_validate_json(ui_state_json)

    def on_error(self, task_id: str, error_message: str, error_code: str) -> None:
        print(f"\n{Colors.FAIL}[SYSTEM ERROR] {error_code}: {error_message}{Colors.ENDC}")
