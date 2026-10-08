"""Aplicación principal de consola interactiva (CLI) para AAdventure."""

import os
from typing import Optional, Tuple

from cli.formatter import CLIFormatter, Colors
from cli.listener import CLIEventListener
from engines import AdventureSession


class CLIApp:
    """Controlador del bucle interactivo de la interfaz de consola basado en eventos."""

    def __init__(self, session: AdventureSession, verbose: bool = False):
        self.session = session
        self.verbose = verbose
        self.is_running = True
        self.listener = CLIEventListener(session=self.session, verbose=self.verbose)
        self.session.add_listener(self.listener)

    def parse_command(self, raw_input: str) -> Tuple[str, str]:
        """Analiza la entrada del jugador identificando comandos con '/' o mensajes libres."""
        clean = (raw_input or "").strip().lstrip("\ufeff\xef\xbb\xbf")
        if not clean:
            return "EMPTY", ""

        # Comandos de salida estándar
        if clean.lower() in ["exit", "quit", "q"]:
            return "EXIT", ""

        # Comandos con prefijo de barra inclinada (simulación de botones de la UI)
        if clean.startswith("/"):
            parts = clean[1:].split(maxsplit=1)
            action_name = parts[0].upper()
            target_arg = parts[1].strip() if len(parts) > 1 else ""

            if action_name in ["MOVE", "LOOK", "TALK"]:
                return action_name, target_arg
            elif action_name in ["EXIT", "QUIT", "Q"]:
                return "EXIT", ""
            elif action_name in ["HELP", "H", "?"]:
                return "HELP", ""
            elif action_name in ["STATUS", "STATE"]:
                return "STATUS", ""
            elif action_name in ["ACTIONS", "OPTS", "MOVES"]:
                return "ACTIONS", ""
            else:
                return "UNKNOWN", action_name

        # Texto libre para conversación o respuesta
        return "MESSAGE", clean

    def handle_input(self, raw_input: str) -> Optional[str]:
        """Procesa una línea de entrada del usuario despachando la acción de forma asíncrona y reactiva."""
        cmd_type, arg = self.parse_command(raw_input)

        if cmd_type == "EMPTY":
            return None

        if cmd_type == "EXIT":
            self.is_running = False
            return None

        if cmd_type == "HELP":
            CLIFormatter.print_help()
            return None

        if cmd_type == "STATUS":
            if self.listener.latest_ui_state:
                CLIFormatter.print_status(self.listener.latest_ui_state)
            return None

        if cmd_type == "ACTIONS":
            self._print_available_actions()
            return None

        if cmd_type == "UNKNOWN":
            print(
                f"{Colors.FAIL}[SYSTEM] > Comando '{arg}' no reconocido. Escribe /HELP para ver los comandos disponibles.{Colors.ENDC}")
            return None

        if cmd_type in ["MOVE", "LOOK", "TALK"]:
            if not arg:
                print(
                    f"{Colors.FAIL}[SYSTEM] > Debes especificar un objetivo para /{cmd_type}. Ejemplo: /{cmd_type} <destino_o_personaje>{Colors.ENDC}")
                return None
            task_id = self.session.post_action(action=cmd_type, target=arg)
            self.session.wait_idle()
            return task_id

        if cmd_type == "MESSAGE":
            task_id = self.session.post_action(action="", target="", player_input=arg)
            self.session.wait_idle()
            return task_id

        return None

    def _print_available_actions(self) -> None:
        """Muestra los movimientos y objetivos accesibles en el turno actual."""
        res = self.listener.latest_turn_result
        curr_loc = self.listener.latest_ui_state.current_location if self.listener.latest_ui_state else None
        curr_place = None
        if res and res.map and curr_loc:
            for loc in res.map.locations:
                for p in loc.places:
                    if p.name == curr_loc or p.id == curr_loc:
                        curr_place = p
                        break

        if curr_place:
            print(f"\n{Colors.OKCYAN}{Colors.BOLD}--- OPCIONES DISPONIBLES EN ESTE TURNO ---{Colors.ENDC}")
            if curr_place.connections:
                print(f"  {Colors.BOLD}Desplazamientos disponibles (/MOVE <destino>):{Colors.ENDC}")
                for d, c in curr_place.connections.items():
                    print(f"    • {d.capitalize()}: {c.target} ({c.distance}m, terreno: {c.terrain_type})")
            else:
                print(f"  {Colors.DIM}No hay salidas visibles inmediatas.{Colors.ENDC}")

            if curr_place.npcs:
                print(f"  {Colors.BOLD}Personajes presentes (/TALK <npc>):{Colors.ENDC}")
                for npc in curr_place.npcs:
                    print(f"    • {npc.name}")

            if curr_place.items:
                print(f"  {Colors.BOLD}Inspeccionar (/LOOK <objetivo>):{Colors.ENDC}")
                for it in curr_place.items:
                    if it.visible:
                        print(f"    • {it.name}")
            print(f"{Colors.OKCYAN}------------------------------------------{Colors.ENDC}\n")
            return

        ui_state = self.listener.latest_ui_state
        if ui_state and ui_state.allowed_actions:
            print(f"\n{Colors.OKCYAN}Acciones disponibles: {', '.join(ui_state.allowed_actions)}{Colors.ENDC}\n")
        else:
            print(f"\n{Colors.OKCYAN}Escribe /MOVE <destino>, /LOOK <objetivo> o /TALK <npc>{Colors.ENDC}\n")

    def run(self) -> None:
        """Ejecuta el bucle de juego interactivo en consola."""
        aad_file = self.session.aad_path or ""
        world_name = os.path.splitext(os.path.basename(aad_file))[0] if aad_file else "Aventura"
        CLIFormatter.print_banner(world_name=world_name, aad_file=aad_file)
        if self.listener.latest_ui_state:
            CLIFormatter.print_status(self.listener.latest_ui_state)

        # Iniciar formalmente la partida (Turno 0)
        self.session.start()
        self.session.wait_idle()

        print(f"{Colors.DIM}Escribe /HELP para ver la lista de comandos o /EXIT para salir.{Colors.ENDC}")

        while self.is_running:
            try:
                ui_state = self.listener.latest_ui_state
                if ui_state:
                    time_str = ui_state.formatted_time
                    player_name = ui_state.player_name
                else:
                    time_str = "00:00"
                    player_name = "Aventurero"

                prompt_str = f"\n{Colors.BOLD}[{time_str}] [{player_name}] > {Colors.ENDC}"
                raw_input = input(prompt_str).strip()

                self.handle_input(raw_input)

            except (KeyboardInterrupt, EOFError):
                print(f"\n\n{Colors.OKBLUE}Interrupción detectada. Guardando y saliendo...{Colors.ENDC}")
                break
            except Exception as e:
                print(f"\n{Colors.FAIL}[ERROR INESPERADO EN CLI]: {e}{Colors.ENDC}")

        self.session.close()
        print(f"\n{Colors.OKBLUE}Partida finalizada. ¡Hasta pronto, aventurero!{Colors.ENDC}\n")


def start_cli(session: AdventureSession, verbose: bool = False) -> None:
    """Punto de entrada para iniciar la interfaz de consola con una AdventureSession."""
    app = CLIApp(session=session, verbose=verbose)
    app.run()
