import sys
import os
import json
from transformer_engine import DungeonMaster, TransformerModel
from pydantic import ValidationError
from domains import (
    ActionResponse,
    DialogueResponse,
    NarrativeResponse,
    MarkdownContext,
)
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

# Rutas de los archivos JSON de datos de aventura
WORLD_JSON_PATH = r"Resources/adventure_data/world_2.json"
NPCS_JSON_PATH = r"Resources/adventure_data/npcs_2.json"
PLAYER_JSON_PATH = r"Resources/adventure_data/player_2.json"

# Rutas de los archivos de configuración y reglas del LLM
LLM_CONFIG_PATH = r"Resources/system_data/llm_config.json"
CLASSIFIER_RULES_PATH = r"Resources/system_data/rules/classifier.md"
DIALOGUE_RULES_PATH = r"Resources/system_data/rules/dialogue.md"
NARRATOR_RULES_PATH = r"Resources/system_data/rules/narrator.md"


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

    # 3. Imprimir el GameState inicial del juego recién cargado
    print(f"\n{Colors.OKCYAN}{Colors.BOLD}--- DEBUG: GameState INICIAL (Estado Cargado) ---{Colors.ENDC}")
    print(game_engine.game_state_controller.data.model_dump_json(indent=2))
    print(f"{Colors.OKCYAN}--------------------------------------------------{Colors.ENDC}")

    print(f"\nIntroduce tu acción. Escribe {Colors.BOLD}'exit'{Colors.ENDC} para salir.")

    # =====================================================================
    # BUCLE PRINCIPAL DE JUEGO (GAME LOOP)
    # =====================================================================
    while True:
        try:
            player_input = input(f"\n{Colors.BOLD}[Jugador] > {Colors.ENDC}").strip()
            if not player_input:
                continue

            if player_input.lower() in ["exit", "quit", "q"]:
               print(f"\n{Colors.OKBLUE}Saliendo... ¡Hasta pronto!{Colors.ENDC}")
               break

            # Determinar el estado de la máquina de estados actual
            current_state = game_engine.game_state_controller.data.player_state.upper()

            if current_state == "TALK":
                # --- ESTADO TALK (Conversación Activa) ---
                # 1. Buscar el NPC con el que se habla
                target_npc_name = game_engine.game_state_controller.data.player_target
                npc = game_engine.get_npc_by_name_or_id(target_npc_name)

                if not npc:
                    print(f"\n{Colors.FAIL}[ERROR] No se pudo encontrar al NPC '{target_npc_name}' en el mundo.{Colors.ENDC}")
                    game_engine.game_state_controller.update_state("NORMAL")
                    continue

                # 2. Construir contexto para el diálogo en Markdown
                md_dialogue = game_engine.get_dialogue_context_markdown(player_input)
                dialogue_context = MarkdownContext(markdown_content=md_dialogue)

                # DEBUG: Imprimir DialogueContext
                print(f"\n{Colors.OKCYAN}{Colors.BOLD}--- DEBUG: DialogueContext ---{Colors.ENDC}")
                print(md_dialogue)
                print(f"{Colors.OKCYAN}-------------------------------{Colors.ENDC}")

                # 3. Generar diálogo usando las reglas
                dialogue_result = dm.execute(
                    rules_path=DIALOGUE_RULES_PATH,
                    gamecontext=dialogue_context,
                    player_input=player_input,
                    response_model=DialogueResponse,
                    profile_name="dialogue"
                )
                npc_response = dialogue_result["msg"]
                dialogue_obj = DialogueResponse.model_validate(dialogue_result)

                # DEBUG: Imprimir DialogueResponse
                print(f"\n{Colors.OKGREEN}{Colors.BOLD}--- DEBUG: DialogueResponse ---{Colors.ENDC}")
                print(json.dumps(dialogue_result, indent=2, ensure_ascii=False))
                print(f"{Colors.OKGREEN}--------------------------------{Colors.ENDC}")

                # Imprimir la respuesta del NPC
                print(f"\n{Colors.OKGREEN}{Colors.BOLD}[{npc.name}] > {Colors.ENDC}{npc_response}")

                # 4. Procesar el resultado del diálogo en el GameEngine
                eval_result = game_engine.process_dialogue(dialogue_obj, player_input)
                if dialogue_obj.service and not eval_result.allowed:
                    print(f"\n{Colors.FAIL}[ADVERTENCIA ENGINE] Transacción del servicio rechazada: {eval_result.reason}{Colors.ENDC}")

                # 5. Si el diálogo ha finalizado, imprimirlo
                if game_engine.game_state_controller.data.player_state.upper() == "NORMAL":
                    print(f"\n{Colors.OKBLUE}[INFO] Conversación finalizada con {npc.name}. Volviendo a exploración.{Colors.ENDC}")
                
                game_engine.save()

                # DEBUG: Imprimir GameState actualizado
                print(f"\n{Colors.OKCYAN}{Colors.BOLD}--- DEBUG: GameState ---{Colors.ENDC}")
                print(game_engine.game_state_controller.data.model_dump_json(indent=2))
                print(f"{Colors.OKCYAN}------------------------{Colors.ENDC}")

            else:
                # --- ESTADO NORMAL (Exploración) ---
                # 1. Construir el contexto del clasificador en Markdown
                md_classifier = game_engine.get_classifier_context_markdown(player_input)
                action_ctx = MarkdownContext(markdown_content=md_classifier)

                # 2. Clasificar acción usando DungeonMaster
                action_result = dm.execute(
                    rules_path=CLASSIFIER_RULES_PATH,
                    gamecontext=action_ctx,
                    player_input=player_input,
                    response_model=ActionResponse,
                    profile_name="classifier"
                )
                action_obj = ActionResponse.model_validate(action_result)

                # DEBUG: Imprimir ActionResponse
                print(f"\n{Colors.OKGREEN}{Colors.BOLD}--- DEBUG: ActionResponse ---{Colors.ENDC}")
                print(json.dumps(action_result, indent=2, ensure_ascii=False))
                print(f"{Colors.OKGREEN}------------------------------{Colors.ENDC}")

                # 3. Procesar la acción en el GameEngine (validación y mutación integrada)
                eval_result = game_engine.process_action(action_obj, player_input)
                if not eval_result.allowed:
                    print(f"\n{Colors.FAIL}[ADVERTENCIA ENGINE] Acción rechazada: {eval_result.reason}{Colors.ENDC}")

                # 4. Comprobar si la mutación nos ha llevado al estado TALK
                if game_engine.game_state_controller.data.player_state.upper() == "TALK":
                    target_npc_name = game_engine.game_state_controller.data.player_target
                    npc = game_engine.get_npc_by_name_or_id(target_npc_name)
                    if not npc:
                        print(f"\n{Colors.FAIL}[ERROR] No se pudo encontrar al NPC '{target_npc_name}' en el mundo.{Colors.ENDC}")
                        game_engine.game_state_controller.update_state("NORMAL")
                        continue

                    # Construir contexto para el diálogo inicial
                    md_dialogue = game_engine.get_dialogue_context_markdown(player_input)
                    dialogue_context = MarkdownContext(markdown_content=md_dialogue)

                    # DEBUG: Imprimir DialogueContext
                    print(f"\n{Colors.OKCYAN}{Colors.BOLD}--- DEBUG: DialogueContext ---{Colors.ENDC}")
                    print(md_dialogue)
                    print(f"{Colors.OKCYAN}-------------------------------{Colors.ENDC}")

                    # Generar primera réplica del NPC
                    dialogue_result = dm.execute(
                        rules_path=DIALOGUE_RULES_PATH,
                        gamecontext=dialogue_context,
                        player_input=player_input,
                        response_model=DialogueResponse,
                        profile_name="dialogue"
                    )
                    npc_response = dialogue_result["msg"]
                    dialogue_obj = DialogueResponse.model_validate(dialogue_result)

                    # DEBUG: Imprimir DialogueResponse
                    print(f"\n{Colors.OKGREEN}{Colors.BOLD}--- DEBUG: DialogueResponse ---{Colors.ENDC}")
                    print(json.dumps(dialogue_result, indent=2, ensure_ascii=False))
                    print(f"{Colors.OKGREEN}--------------------------------{Colors.ENDC}")

                    # Imprimir respuesta
                    print(f"\n{Colors.OKGREEN}{Colors.BOLD}[{npc.name}] > {Colors.ENDC}{npc_response}")

                    # Registrar diálogo en el NPC
                    game_engine.process_dialogue(dialogue_obj, player_input)

                    if game_engine.game_state_controller.data.player_state.upper() == "NORMAL":
                        game_engine.game_state_controller.update_state("NORMAL")
                        game_engine.game_state_controller.data.player_target = ""
                        print(f"\n{Colors.OKBLUE}[INFO] Conversación finalizada con {npc.name}. Volviendo a exploración.{Colors.ENDC}")

                    game_engine.save()

                    # DEBUG: Imprimir GameState actualizado
                    print(f"\n{Colors.OKCYAN}{Colors.BOLD}--- DEBUG: GameState ---{Colors.ENDC}")
                    print(game_engine.game_state_controller.data.model_dump_json(indent=2))
                    print(f"{Colors.OKCYAN}------------------------{Colors.ENDC}")

                else:
                    # Seguir en exploración normal, usar narrador general
                    md_narrator = game_engine.get_narrative_context_markdown(player_input)
                    if not eval_result.allowed:
                        md_narrator += f"\n\n> [!WARNING]\n> El jugador intentó realizar una acción no válida: '{player_input}'. Razón del fallo: {eval_result.reason}. Narra por qué falló de manera orgánica."

                    narrative_ctx = MarkdownContext(markdown_content=md_narrator)

                    # DEBUG: Imprimir NarrativeContext
                    print(f"\n{Colors.OKCYAN}{Colors.BOLD}--- DEBUG: NarrativeContext ---{Colors.ENDC}")
                    print(md_narrator)
                    print(f"{Colors.OKCYAN}--------------------------------{Colors.ENDC}")

                    # Generar narración
                    narration_result = dm.execute(
                        rules_path=NARRATOR_RULES_PATH,
                        gamecontext=narrative_ctx,
                        player_input=player_input,
                        response_model=NarrativeResponse,
                        profile_name="narrator"
                    )
                    narration_text = narration_result["msg"]

                    # DEBUG: Imprimir NarrativeResponse
                    print(f"\n{Colors.OKGREEN}{Colors.BOLD}--- DEBUG: NarrativeResponse ---{Colors.ENDC}")
                    print(json.dumps(narration_result, indent=2, ensure_ascii=False))
                    print(f"{Colors.OKGREEN}---------------------------------{Colors.ENDC}")

                    # Imprimir narración
                    print(f"\n{Colors.OKGREEN}{Colors.BOLD}[Dungeon Master] > {Colors.ENDC}{narration_text}")

                    # Registrar la narración en el historial
                    game_engine.mutator.add_turn_to_history(game_engine.game_state_controller, player_input, narration_text)

                    game_engine.save()

                    # DEBUG: Imprimir GameState actualizado
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
