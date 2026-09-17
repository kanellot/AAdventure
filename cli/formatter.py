"""Utilidades de presentación y formateo visual para la consola CLI de AAdventure."""

from typing import Optional
from domains.projections import (
    GameStateProjection,
    LoreGraphProjection,
    RagEvaluationProjection,
    TurnResultProjection,
    UIStateProjection,
)


class Colors:
    """Códigos de escape ANSI para colores en terminal."""

    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"


class CLIFormatter:
    """Formateador de salidas normales y bloques de depuración verbose en la consola."""

    @staticmethod
    def print_banner(world_name: str = "AAdventure", aad_file: str = "") -> None:
        """Muestra el banner de inicio de la partida en consola."""
        print(f"{Colors.HEADER}{Colors.BOLD}" + "=" * 70)
        print("      AAdventure CLI - Motor Narrativo D&D con AdventureSession")
        if aad_file:
            print(f"      Mundo: {world_name} | Archivo: {aad_file}")
        print("=" * 70 + f"{Colors.ENDC}\n")

    @staticmethod
    def print_help() -> None:
        """Muestra la guía de comandos disponibles en la consola."""
        print(f"\n{Colors.OKCYAN}{Colors.BOLD}--- COMANDOS DISPONIBLES EN CONSOLA ---{Colors.ENDC}")
        print(f"  {Colors.BOLD}/MOVE <destino>{Colors.ENDC}    : Desplazarse a un lugar conectado (simula boton MOVE de la UI)")
        print(f"  {Colors.BOLD}/LOOK <objetivo>{Colors.ENDC}   : Inspeccionar lugar, personaje u objeto (simula boton LOOK)")
        print(f"  {Colors.BOLD}/TALK <npc>{Colors.ENDC}        : Iniciar dialogo con un NPC (simula boton TALK)")
        print(f"  {Colors.BOLD}<texto libre>{Colors.ENDC}      : Hablar con el NPC en conversacion activa o responder")
        print(f"  {Colors.BOLD}/STATUS{Colors.ENDC}            : Ver estado consolidado del jugador (HUD)")
        print(f"  {Colors.BOLD}/ACTIONS{Colors.ENDC}           : Listar acciones y movimientos validos en este turno")
        print(f"  {Colors.BOLD}/HELP{Colors.ENDC}              : Mostrar esta lista de comandos")
        print(f"  {Colors.BOLD}/EXIT{Colors.ENDC} o {Colors.BOLD}exit{Colors.ENDC}     : Guardar y salir del juego")
        print(f"{Colors.OKCYAN}---------------------------------------{Colors.ENDC}\n")

    @staticmethod
    def print_status(ui_state: UIStateProjection) -> None:
        """Muestra el HUD consolidado del jugador."""
        mode_str = ui_state.game_state
        if ui_state.game_state == "TALK" and ui_state.player_target:
            if ui_state.active_npc_affinity is not None:
                mode_str = f"TALK ({ui_state.player_target} | Afinidad: {ui_state.active_npc_affinity:.2f})"
            else:
                mode_str = f"TALK ({ui_state.player_target})"

        print(f"\n{Colors.OKCYAN}{Colors.BOLD}[HUD] Jugador: {ui_state.player_name} | Lugar: {ui_state.current_location} | Oro: {ui_state.gold} | Tiempo: {ui_state.formatted_time} | Modo: {mode_str}{Colors.ENDC}")

    @staticmethod
    def print_turn_result(turn_result: TurnResultProjection) -> None:
        """Muestra el resultado narrativo del turno."""
        if turn_result.author == "SYSTEM":
            print(f"\n{Colors.FAIL}{Colors.BOLD}[SYSTEM] > {Colors.ENDC}{turn_result.msg}")
        elif turn_result.author == "Dungeon Master":
            print(f"\n{Colors.OKBLUE}{Colors.BOLD}[Dungeon Master] > {Colors.ENDC}{turn_result.msg}")
        else:
            print(f"\n{Colors.OKGREEN}{Colors.BOLD}[{turn_result.author}] > {Colors.ENDC}{turn_result.msg}")

        if turn_result.info_msg:
            print(f"{Colors.WARNING}{Colors.BOLD}[INFO] {turn_result.info_msg}{Colors.ENDC}")

    @staticmethod
    def print_verbose_debug(
        turn_result: TurnResultProjection,
        game_state: Optional[GameStateProjection] = None,
        lore_graph: Optional[LoreGraphProjection] = None,
    ) -> None:
        """Muestra la información exhaustiva de depuración cuando el modo verbose (-v) está activo."""
        print(f"\n{Colors.DIM}" + "-" * 70)
        print(" [DEBUG MODE -v]: Inspeccion Detallada del Turno")
        print("-" * 70 + f"{Colors.ENDC}")

        # 1. Prompt enviado al LLM
        if turn_result.debug_prompt:
            print(f"{Colors.OKCYAN}{Colors.BOLD}[PROMPT ENVIADO AL LLM]:{Colors.ENDC}")
            print(f"{Colors.DIM}{turn_result.debug_prompt.strip()}{Colors.ENDC}\n")

        # 2. Evaluación RAG y Antenas
        rag = turn_result.rag_evaluation
        if rag:
            print(f"{Colors.OKCYAN}{Colors.BOLD}[EVALUACION SEMANTICA RAG]:{Colors.ENDC}")
            print(f"  * Input Evaluado   : \"{rag.player_input}\"")
            print(f"  * Umbral Minimo    : {rag.threshold}")
            if rag.matched_lore_id:
                print(f"  * Lore Coincidente : {Colors.OKGREEN}{rag.matched_lore_id} (Antena: \"{rag.matched_antenna}\"){Colors.ENDC}")
                if rag.injected_directive:
                    print(f"  * Directiva Iny.   : \"{rag.injected_directive}\"")
            else:
                print(f"  * Lore Coincidente : {Colors.DIM}Ninguno supero el umbral.{Colors.ENDC}")

            if rag.antennas:
                print("  * Antenas Evaluadas:")
                for ant in rag.antennas:
                    matched_flag = f"{Colors.OKGREEN}[MATCH]{Colors.ENDC}" if ant.is_matched else f"{Colors.DIM}[--]{Colors.ENDC}"
                    cond_flag = "Cond: OK" if ant.conditions_met else "Cond: NO"
                    print(f"    - [{ant.score:.4f}] \"{ant.antenna}\" (Lore: {ant.lore_id}) [{cond_flag}] {matched_flag}")
            print()

        # 3. LoreBlocks HSM (Activos / Completados)
        if lore_graph:
            print(f"{Colors.OKCYAN}{Colors.BOLD}[ESTADO HSM LOREBLOCKS]:{Colors.ENDC}")
            print(f"  * Total: {lore_graph.total_count} | Activos: {lore_graph.active_count} | Done: {lore_graph.done_count} | Unknown: {lore_graph.unknown_count}")
            active_names = [b.title or b.id for b in lore_graph.blocks if b.state == "active"]
            done_names = [b.title or b.id for b in lore_graph.blocks if b.state == "done"]
            if active_names:
                print(f"  * Activos : {', '.join(active_names)}")
            if done_names:
                print(f"  * Done    : {', '.join(done_names)}")
            print()

        # 4. Respuesta Estructurada o Raw del LLM
        if turn_result.debug_structured_response or turn_result.debug_raw_response:
            print(f"{Colors.OKCYAN}{Colors.BOLD}[RESPUESTA DEL MODELO (LLM)]:{Colors.ENDC}")
            resp_str = turn_result.debug_structured_response or turn_result.debug_raw_response or ""
            print(f"{Colors.DIM}{resp_str.strip()}{Colors.ENDC}\n")

        # 5. GameState
        if game_state:
            print(f"{Colors.OKCYAN}{Colors.BOLD}[GAME STATE SNAPSHOT]:{Colors.ENDC}")
            print(f"  * Ubicacion: {game_state.current_place} (Previo: {game_state.prev_place})")
            print(f"  * Jugador  : Estado={game_state.player_state}, Target='{game_state.player_target}', Afinidad={game_state.active_npc_affinity}")
            print(f"  * Tiempo   : {game_state.formatted_time} ({game_state.elapsed_time} min)")
            print(f"  * Visitados: {len(game_state.discovered_places)} lugares | NPCs Visibles: {game_state.visible_npcs}")

        print(f"{Colors.DIM}" + "-" * 70 + f"{Colors.ENDC}\n")
