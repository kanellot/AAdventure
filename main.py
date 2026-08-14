import sys
import os
import json
from transformer_engine import DungeonMaster, TransformerModel
from pydantic import ValidationError
from domains import Actions, PreActionContext, NarrationResponse
from game_state import GameState
from context_builder import ContextBuilder


# Colores ANSI para la consola
class Colors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"


def print_banner():
    print(f"{Colors.HEADER}{Colors.BOLD}" + "=" * 65)
    print("       AAdventure: Motor Narrativo D&D (Punto de Entrada)")
    print("=" * 65 + f"{Colors.ENDC}")


def main():
    print_banner()

    # Rutas de datos de la aventura
    world_json_path = r"Resources/adventure_data/world_2.json"
    npcs_json_path = r"Resources/adventure_data/npcs_2.json"
    player_json_path = r"Resources/adventure_data/player_2.json"

    # 1. Construir WorldState, PlayerState, GameState a partir de los archivos de aventura
    print(f"{Colors.OKCYAN}[INFO] Inicializando GameState y cargando datos de aventura...{Colors.ENDC}")
    try:
        game_state = GameState(
            world_json_path=world_json_path,
            npcs_json_path=npcs_json_path,
            player_json_path=player_json_path
        )
        print(f"{Colors.OKGREEN}[INFO] GameState y entidades inicializados correctamente desde los archivos JSON.{Colors.ENDC}")
    except Exception as e:
        print(f"{Colors.FAIL}[ERROR CRÍTICO AL INICIALIZAR EL JUEGO]: {e}{Colors.ENDC}")
        sys.exit(1)

    # Rutas de configuración y reglas del sistema
    config_path = r"Resources/system_data/llm_config.json"
    rules_path = r"Resources/system_data/rules/classifier_rules.md"

    # 2. Inicializar el modelo LLM de transformer_engine
    print(f"{Colors.OKCYAN}[INFO] Inicializando modelo LLM...{Colors.ENDC}")
    try:
        adapter = TransformerModel(config_path=config_path)
        dm = DungeonMaster(llm_adapter=adapter)
        print(f"{Colors.OKGREEN}[INFO] TransformerModel y DungeonMaster inicializados correctamente.{Colors.ENDC}")
    except Exception as e:
        print(f"{Colors.FAIL}[ERROR DE CONFIGURACIÓN DEL LLM]{Colors.ENDC}")
        print(f"No se pudo cargar el clasificador semántico: {e}")
        print("\nPor favor, instala 'llama-cpp-python' y configura el modelo local GGUF.")
        sys.exit(1)

    # 3. Imprimir el PRE_ACTION inicial del juego recién cargado
    initial_pre_action_ctx = PreActionContext(
        player_state=game_state.player_state.data,
        player_input=""
    )
    print(f"\n{Colors.OKCYAN}{Colors.BOLD}--- DEBUG: PRE_ACTION INICIAL (Estado Cargado) ---{Colors.ENDC}")
    print(initial_pre_action_ctx.model_dump_json(indent=2))
    print(f"{Colors.OKCYAN}--------------------------------------------------{Colors.ENDC}")

    print(f"\nIntroduce tu acción. Escribe {Colors.BOLD}'exit'{Colors.ENDC} para salir.")

    while True:
        try:
            player_input = input(f"\n{Colors.BOLD}[Jugador] > {Colors.ENDC}").strip()
            if not player_input:
                continue

            if player_input.lower() in ["exit", "quit", "q"]:
               print(f"\n{Colors.OKBLUE}Saliendo... ¡Hasta pronto!{Colors.ENDC}")
               break

            # 3. Construir el objeto de contexto PRE_ACTION usando los datos reales
            pre_action_ctx = PreActionContext(
                player_state=game_state.player_state.data,
                player_input=player_input
            )

            # DEBUG: Imprimir PRE_ACTION
            print(f"\n{Colors.OKCYAN}{Colors.BOLD}--- DEBUG: PRE_ACTION (PreActionContext) ---{Colors.ENDC}")
            print(pre_action_ctx.model_dump_json(indent=2))
            print(f"{Colors.OKCYAN}--------------------------------------------{Colors.ENDC}")

            # 4. Clasificar acción usando DungeonMaster
            action_result = dm.execute(
                rules_path=rules_path,
                gamecontext=pre_action_ctx,
                player_input=player_input,
                response_model=Actions
            )

            # 5. Capturar el estado del jugador antes de la mutación
            prev_player_state = game_state.player_state.data.model_copy(deep=True)

            # 6. Mutar el estado del juego basándonos en la acción clasificada
            game_state.mutate(action_result)

            # DEBUG: Imprimir ACTION
            print(f"\n{Colors.OKGREEN}{Colors.BOLD}--- DEBUG: ACTION (Clasificación de Acciones) ---{Colors.ENDC}")
            print(json.dumps(action_result, indent=2, ensure_ascii=False))
            print(f"{Colors.OKGREEN}-------------------------------------------------{Colors.ENDC}")

            # 7. Construir el contexto para la narración
            narrative_ctx = ContextBuilder.build_narrative_context(
                prev_state=prev_player_state,
                curr_state=game_state.player_state.data,
                executed_actions=Actions.model_validate(action_result),
                player_input=player_input,
                world_state=game_state.world_state
            )

            # DEBUG: Imprimir NARRATIVE_CONTEXT
            print(f"\n{Colors.OKCYAN}{Colors.BOLD}--- DEBUG: NARRATIVE_CONTEXT (NarrativeContext) ---{Colors.ENDC}")
            print(narrative_ctx.model_dump_json(indent=2))
            print(f"{Colors.OKCYAN}--------------------------------------------------{Colors.ENDC}")

            # 8. Generar narración usando el DungeonMaster
            narrator_rules_path = r"Resources/system_data/rules/narrator.md"
            narration_result = dm.execute(
                rules_path=narrator_rules_path,
                gamecontext=narrative_ctx,
                player_input=player_input,
                response_model=NarrationResponse
            )
            narration_text = narration_result["narration"]

            # Imprimir la narración del Dungeon Master
            print(f"\n{Colors.OKGREEN}{Colors.BOLD}[Dungeon Master] > {Colors.ENDC}{narration_text}")

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
