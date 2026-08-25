import sys
from transformer_engine import DungeonMaster, TransformerModel
from pydantic import ValidationError
from game_engine import GameEngine


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
DEBUG_PROMPS = 0
DEBUG_PROMPTS = 0
DEBUG_RESPONSE = 0
DEBUG_STATE = 0

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
    print_banner()

    # =====================================================================
    # INICIALIZACIÓN DEL SISTEMA Y DATOS DE JUEGO
    # =====================================================================
    
    # 1. Construir GameEngine
    print(f"{Colors.OKCYAN}[INFO] Inicializando GameEngine y cargando datos de aventura...{Colors.ENDC}")
    try:
        game_engine = GameEngine(
            world_json_path=WORLD_JSON_PATH,
            npcs_json_path=NPCS_JSON_PATH,
            player_json_path=PLAYER_JSON_PATH
        )
        print(f"{Colors.OKGREEN}[INFO] GameEngine y entidades inicializados correctamente desde los archivos JSON.{Colors.ENDC}")
    except Exception as e:
        print(f"{Colors.FAIL}[ERROR CRÍTICO AL INICIALIZAR EL JUEGO]: {e}{Colors.ENDC}")
        sys.exit(1)

    # 2. Inicializar el modelo LLM y DungeonMaster
    print(f"{Colors.OKCYAN}[INFO] Inicializando modelo LLM...{Colors.ENDC}")
    try:
        adapter = TransformerModel(config_path=LLM_CONFIG_PATH)
        dm = DungeonMaster(llm_adapter=adapter)
        print(f"{Colors.OKGREEN}[INFO] TransformerModel y DungeonMaster inicializados correctamente.{Colors.ENDC}")
    except Exception as e:
        print(f"{Colors.FAIL}[ERROR DE CONFIGURACIÓN DEL LLM]{Colors.ENDC}")
        print(f"No se pudo cargar el clasificador semántico: {e}")
        print("\nPor favor, instala 'llama-cpp-python' y configura el modelo local GGUF.")
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
            player_input = input(f"\n{Colors.BOLD}[{player_name}] > {Colors.ENDC}").strip()
            if not player_input:
                continue

            if player_input.lower() in ["exit", "quit", "q"]:
               print(f"\n{Colors.OKBLUE}Saliendo... ¡Hasta pronto!{Colors.ENDC}")
               break

            # Ejecutar el turno completo
            turn_output = game_engine.execute_turn(player_input, dm)

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
