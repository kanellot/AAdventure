import sys
import os
from engines.transformer import TransformerEngine, create_llm_adapter
from pydantic import ValidationError
from engines.game import GameEngine


# =====================================================================
# CONFIGURACIÓN DE CONSTANTES Y RUTAS DE ARCHIVOS (FÁCIL DE MODIFICAR)
# =====================================================================

# Colores ANSI para la consola
class Colors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"

# Configuración de depuración en consola (0 = Desactivado, 1 = Activado)
DEBUG_PROMPS = 1
DEBUG_PROMPTS = 1
DEBUG_RESPONSE = 1
DEBUG_STATE = 1

# Rutas de los archivos JSON de datos de aventura
WORLD_JSON_PATH = r"Resources/adventure_data/world_2.json"
NPCS_JSON_PATH = r"Resources/adventure_data/npcs_2.json"
PLAYER_JSON_PATH = r"Resources/adventure_data/player_2.json"

# Ruta del archivo de configuración del LLM
LLM_CONFIG_PATH = r"Resources/system_data/llm_config.json"


def print_banner():
    print(f"{Colors.HEADER}{Colors.BOLD}" + "=" * 65)
    print("       AAdventure: Motor Narrativo D&D con GameEngine")
    print("=" * 65 + f"{Colors.ENDC}")


def main():
    import argparse
    from adventure_selector import (
        get_default_adventure_path,
        set_default_adventure_path,
        open_adventure_selector,
    )

    parser = argparse.ArgumentParser(description="AAdventure - Motor Narrativo D&D con GameEngine")
    parser.add_argument("--editor", "-e", action="store_true", help="Lanza el editor gráfico de historias")
    parser.add_argument("--play-debug", "-d", action="store_true", help="Jugar con la UI de depuración gráfica")
    parser.add_argument("--select-adventure", "-s", action="store_true", help="Abre el selector gráfico de aventuras")
    parser.add_argument("aad_file", nargs="?", default=None, help="Ruta al archivo de aventura .aad")
    args = parser.parse_args()

    if args.editor:
        print(f"{Colors.OKCYAN}[INFO] Lanzando el Editor de Historias de AAdventure...{Colors.ENDC}")
        try:
            from editor.main import start_editor
            start_editor()
            sys.exit(0)
        except ImportError as ie:
            print(f"{Colors.FAIL}[ERROR] No se pudo iniciar el editor gráfico.{Colors.ENDC}")
            print(f"Asegúrate de instalar PySide6: pip install PySide6")
            print(f"Error detallado: {ie}")
            sys.exit(1)

    # Si se solicita el selector explícito
    if args.select_adventure:
        chosen = open_adventure_selector()
        if not chosen:
            print(f"{Colors.OKCYAN}[INFO] Operación cancelada.{Colors.ENDC}")
            sys.exit(0)
        args.aad_file = chosen

    print_banner()

    # =====================================================================
    # INICIALIZACIÓN DEL SISTEMA Y DATOS DE JUEGO
    # =====================================================================
    
    # 1. Construir GameEngine
    # Si se especificó un aad_file, usarlo y guardarlo como el nuevo por defecto.
    # Si no, consultar la aventura guardada por defecto.
    DEFAULT_AAD = os.path.join("Resources", "adventure_data", "Adventure.aad")
    if args.aad_file:
        aad_to_load = args.aad_file
        if os.path.exists(aad_to_load) and aad_to_load.lower().endswith(".aad"):
            set_default_adventure_path(aad_to_load)
    else:
        aad_to_load = get_default_adventure_path() or DEFAULT_AAD

    if os.path.exists(aad_to_load) and aad_to_load.lower().endswith(".aad"):
        print(f"{Colors.OKCYAN}[INFO] Inicializando GameEngine y cargando aventura desde: {aad_to_load}...{Colors.ENDC}")
        world_path = aad_to_load
        npcs_path = None
        player_path = None
    else:
        # Fallback a los JSON individuales por si acaso no existiera aún el .aad por defecto
        if not args.aad_file:
            print(f"{Colors.OKCYAN}[INFO] Advertencia: No se encontró {DEFAULT_AAD}. Cargando JSONs por defecto...{Colors.ENDC}")
        else:
            print(f"{Colors.OKCYAN}[INFO] Cargando aventura desde archivos JSON...{Colors.ENDC}")
        world_path = WORLD_JSON_PATH
        npcs_path = NPCS_JSON_PATH
        player_path = PLAYER_JSON_PATH

    try:
        game_engine = GameEngine(
            world_json_path=world_path,
            npcs_json_path=npcs_path,
            player_json_path=player_path
        )
        print(f"{Colors.OKGREEN}[INFO] GameEngine y entidades inicializados correctamente.{Colors.ENDC}")
    except Exception as e:
        print(f"{Colors.FAIL}[ERROR CRÍTICO AL INICIALIZAR EL JUEGO]: {e}{Colors.ENDC}")
        sys.exit(1)

    # 2. Inicializar el modelo LLM y TransformerEngine
    print(f"{Colors.OKCYAN}[INFO] Inicializando modelo LLM...{Colors.ENDC}")
    try:
        adapter = create_llm_adapter(config_or_path=LLM_CONFIG_PATH)
        dm = TransformerEngine(llm_adapter=adapter)
        adapter_name = adapter.__class__.__name__
        print(f"{Colors.OKGREEN}[INFO] Adaptador '{adapter_name}' y TransformerEngine inicializados correctamente.{Colors.ENDC}")
    except Exception as e:
        print(f"{Colors.FAIL}[ERROR DE CONFIGURACIÓN DEL LLM]{Colors.ENDC}")
        print(f"No se pudo inicializar el modelo o TransformerEngine: {e}")
        sys.exit(1)

    if args.play_debug:
        print(f"{Colors.OKCYAN}[INFO] Lanzando el Depurador Gráfico de AAdventure...{Colors.ENDC}")
        try:
            from game_debugger.main import start_debugger
            start_debugger(game_engine, dm, aad_path=aad_to_load)
            sys.exit(0)
        except ImportError as ie:
            print(f"{Colors.FAIL}[ERROR] No se pudo iniciar el depurador gráfico.{Colors.ENDC}")
            print(f"Asegúrate de instalar PySide6: pip install PySide6")
            print(f"Error detallado: {ie}")
            sys.exit(1)

    # 3. Imprimir el GameState inicial del juego recién cargado si está activado el debug de estado
    if DEBUG_STATE:
        print(f"\n{Colors.OKCYAN}{Colors.BOLD}--- DEBUG: GameState INICIAL (Estado Cargado) ---{Colors.ENDC}")
        print(game_engine.game_state_controller.data.model_dump_json(indent=2))
        print(f"{Colors.OKCYAN}--------------------------------------------------{Colors.ENDC}")

    print(f"\nIntroduce tu acción. Escribe {Colors.BOLD}'exit'{Colors.ENDC} para salir.")

    # =====================================================================
    # BUCLE PRINCIPAL DE JUEGO (GAME LOOP)
    # =====================================================================
    while True:
        try:
            player_name = game_engine.get_player_name()
            time_str = game_engine.get_formatted_time()
            player_input = input(f"\n{Colors.BOLD}[{time_str}] [{player_name}] > {Colors.ENDC}").strip()
            if not player_input:
                continue

            if player_input.lower() in ["exit", "quit", "q"]:
               print(f"\n{Colors.OKBLUE}Saliendo... ¡Hasta pronto!{Colors.ENDC}")
               break

            # Ejecutar el turno completo
            turn_output = game_engine.execute_turn(action=player_input, dm=dm)

            # Imprimir los resultados narrativos en la consola
            if turn_output.author == "SYSTEM":
                print(f"\n{Colors.FAIL}{Colors.BOLD}[SYSTEM] > {Colors.ENDC}{turn_output.msg}")
            else:
                print(f"\n{Colors.OKGREEN}{Colors.BOLD}[{turn_output.author}] > {Colors.ENDC}{turn_output.msg}")

            # Mostrar mensaje si finalizó el diálogo
            if turn_output.info_msg:
                print(f"\n{Colors.OKBLUE}{turn_output.info_msg}{Colors.ENDC}")

            # DEBUG: Imprimir GameState actualizado si está activado
            if DEBUG_STATE:
                print(f"\n{Colors.OKCYAN}{Colors.BOLD}--- DEBUG: GameState ---{Colors.ENDC}")
                print(game_engine.game_state_controller.data.model_dump_json(indent=2))
                print(f"{Colors.OKCYAN}------------------------{Colors.ENDC}")

        except ValidationError as ve:
            print(f"\n{Colors.FAIL}[ERROR DE VALIDACIÓN DE ESQUEMA (Pydantic)]:{Colors.ENDC}")
            print(f"{Colors.FAIL}{ve}{Colors.ENDC}")
        except KeyboardInterrupt:
            print(f"\n\n{Colors.OKBLUE}Saliendo...{Colors.ENDC}")
            break
        except Exception as e:
            print(f"\n{Colors.FAIL}[ERROR INESPERADO]: {e}{Colors.ENDC}")


if __name__ == "__main__":
    main()
