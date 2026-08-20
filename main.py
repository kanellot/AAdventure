import sys
import os
import json
from transformer_engine import DungeonMaster, TransformerModel
from pydantic import ValidationError
from domains import ActionResponse, ActionCtx, NarrativeResponse, DialogueResponse, TurnSummary, ConversationRecord
from game_data import GameData
from context_builder import ContextBuilder


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
    print("       AAdventure: Motor Narrativo D&D (Punto de Entrada)")
    print("=" * 65 + f"{Colors.ENDC}")


def main():
    print_banner()

    # =====================================================================
    # INICIALIZACIÓN DEL SISTEMA Y DATOS DE JUEGO
    # =====================================================================
    
    # 1. Construir WorldState, GameState, GameStateController
    print(f"{Colors.OKCYAN}[INFO] Inicializando GameStateController y cargando datos de aventura...{Colors.ENDC}")
    try:
        game_state = GameData(
            world_json_path=WORLD_JSON_PATH,
            npcs_json_path=NPCS_JSON_PATH,
            player_json_path=PLAYER_JSON_PATH
        )
        print(f"{Colors.OKGREEN}[INFO] GameData y entidades inicializados correctamente desde los archivos JSON.{Colors.ENDC}")
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
    print(game_state.game_state_controller.data.model_dump_json(indent=2))
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
            current_state = game_state.game_state_controller.data.player_state.upper()

            if current_state == "TALK":
                # --- ESTADO TALK (Conversación Activa) ---
                # 1. Buscar el NPC destino
                target_npc_name = game_state.game_state_controller.data.player_target
                npc = None
                if target_npc_name in game_state.world_state.npcs:
                    npc = game_state.world_state.npcs[target_npc_name]
                elif target_npc_name in game_state.world_state.npcs_by_name:
                    npc = game_state.world_state.npcs_by_name[target_npc_name]

                if not npc:
                    print(f"\n{Colors.FAIL}[ERROR] No se pudo encontrar al NPC '{target_npc_name}' en el mundo.{Colors.ENDC}")
                    game_state.game_state_controller.update_state("NORMAL")
                    continue

                # 2. Construir contexto para el diálogo
                dialogue_context = ContextBuilder.build_dialogue_ctx(npc, player_input)

                # DEBUG: Imprimir DialogueContext
                print(f"\n{Colors.OKCYAN}{Colors.BOLD}--- DEBUG: DialogueContext ---{Colors.ENDC}")
                print(dialogue_context.to_markdown())
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
                dialogue_state = dialogue_result["state"].upper()

                # DEBUG: Imprimir DialogueResponse
                print(f"\n{Colors.OKGREEN}{Colors.BOLD}--- DEBUG: DialogueResponse ---{Colors.ENDC}")
                print(json.dumps(dialogue_result, indent=2, ensure_ascii=False))
                print(f"{Colors.OKGREEN}--------------------------------{Colors.ENDC}")

                # Imprimir la respuesta del NPC
                print(f"\n{Colors.OKGREEN}{Colors.BOLD}[{npc.name}] > {Colors.ENDC}{npc_response}")

                # 4. Registrar diálogo en el NPC
                if not npc.conversation:
                    npc.conversation = ConversationRecord(id=f"c_{npc.id}", msg=[])
                npc.conversation.msg.append({"Player": player_input})
                npc.conversation.msg.append({"Npc": npc_response})

                # 5. Si el diálogo ha finalizado, volver a NORMAL
                if dialogue_state == "NORMAL":
                    game_state.game_state_controller.update_state("NORMAL")
                    game_state.game_state_controller.data.player_target = ""
                    print(f"\n{Colors.OKBLUE}[INFO] Conversación finalizada con {npc.name}. Volviendo a exploración.{Colors.ENDC}")
                
                # Almacenar en el historial de turnos anteriores de GameState
                game_state.game_state_controller.data.prev_turns.append(TurnSummary(player_input=player_input, narration=npc_response))
                game_state.game_state_controller.data.prev_turns = game_state.game_state_controller.data.prev_turns[-4:]
                
                game_state.game_state_controller.save(game_state.world_state)

                # DEBUG: Imprimir GameState actualizado
                print(f"\n{Colors.OKCYAN}{Colors.BOLD}--- DEBUG: GameState ---{Colors.ENDC}")
                print(game_state.game_state_controller.data.model_dump_json(indent=2))
                print(f"{Colors.OKCYAN}------------------------{Colors.ENDC}")

            else:
                # --- ESTADO NORMAL (Exploración) ---
                # 1. Construir el objeto de contexto ActionCtx
                action_ctx = ContextBuilder.build_action_ctx(
                    game_state.world_state,
                    player_input
                )

                # 2. Clasificar acción usando DungeonMaster
                action_result = dm.execute(
                    rules_path=CLASSIFIER_RULES_PATH,
                    gamecontext=action_ctx,
                    player_input=player_input,
                    response_model=ActionResponse,
                    profile_name="classifier"
                )

                # DEBUG: Imprimir ActionResponse
                print(f"\n{Colors.OKGREEN}{Colors.BOLD}--- DEBUG: ActionResponse ---{Colors.ENDC}")
                print(json.dumps(action_result, indent=2, ensure_ascii=False))
                print(f"{Colors.OKGREEN}------------------------------{Colors.ENDC}")

                # 3. Capturar el estado del jugador antes de la mutación
                prev_game_state = game_state.game_state_controller.data.model_copy(deep=True)

                # 4. Mutar el estado del juego
                game_state.mutate(action_result)

                # 5. Comprobar si la mutación nos ha llevado al estado TALK
                if game_state.game_state_controller.data.player_state.upper() == "TALK":
                    # Buscar el NPC
                    target_npc_name = game_state.game_state_controller.data.player_target
                    npc = None
                    if target_npc_name in game_state.world_state.npcs:
                        npc = game_state.world_state.npcs[target_npc_name]
                    elif target_npc_name in game_state.world_state.npcs_by_name:
                        npc = game_state.world_state.npcs_by_name[target_npc_name]

                    if not npc:
                        print(f"\n{Colors.FAIL}[ERROR] No se pudo encontrar al NPC '{target_npc_name}' en el mundo.{Colors.ENDC}")
                        game_state.game_state_controller.update_state("NORMAL")
                        continue

                    # Construir contexto para el diálogo inicial
                    dialogue_context = ContextBuilder.build_dialogue_ctx(npc, player_input)

                    # DEBUG: Imprimir DialogueContext
                    print(f"\n{Colors.OKCYAN}{Colors.BOLD}--- DEBUG: DialogueContext ---{Colors.ENDC}")
                    print(dialogue_context.to_markdown())
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
                    dialogue_state = dialogue_result["state"].upper()

                    # DEBUG: Imprimir DialogueResponse
                    print(f"\n{Colors.OKGREEN}{Colors.BOLD}--- DEBUG: DialogueResponse ---{Colors.ENDC}")
                    print(json.dumps(dialogue_result, indent=2, ensure_ascii=False))
                    print(f"{Colors.OKGREEN}--------------------------------{Colors.ENDC}")

                    # Imprimir respuesta
                    print(f"\n{Colors.OKGREEN}{Colors.BOLD}[{npc.name}] > {Colors.ENDC}{npc_response}")

                    # Registrar diálogo en el NPC
                    if not npc.conversation:
                        npc.conversation = ConversationRecord(id=f"c_{npc.id}", msg=[])
                    npc.conversation.msg.append({"Player": player_input})
                    npc.conversation.msg.append({"Npc": npc_response})

                    if dialogue_state == "NORMAL":
                        game_state.game_state_controller.update_state("NORMAL")
                        game_state.game_state_controller.data.player_target = ""
                        print(f"\n{Colors.OKBLUE}[INFO] Conversación finalizada con {npc.name}. Volviendo a exploración.{Colors.ENDC}")

                    # Almacenar en el historial de turnos anteriores de GameState
                    game_state.game_state_controller.data.prev_turns.append(TurnSummary(player_input=player_input, narration=npc_response))
                    game_state.game_state_controller.data.prev_turns = game_state.game_state_controller.data.prev_turns[-4:]

                    game_state.game_state_controller.save(game_state.world_state)

                    # DEBUG: Imprimir GameState actualizado
                    print(f"\n{Colors.OKCYAN}{Colors.BOLD}--- DEBUG: GameState ---{Colors.ENDC}")
                    print(game_state.game_state_controller.data.model_dump_json(indent=2))
                    print(f"{Colors.OKCYAN}------------------------{Colors.ENDC}")

                else:
                    # Seguir en exploración normal, usar narrador general
                    narrative_ctx = ContextBuilder.build_narrative_ctx(
                        world_state=game_state.world_state,
                        current_place_name=game_state.game_state_controller.data.current_place.name,
                        player_input=player_input
                    )

                    # DEBUG: Imprimir NarrativeContext
                    print(f"\n{Colors.OKCYAN}{Colors.BOLD}--- DEBUG: NarrativeContext ---{Colors.ENDC}")
                    print(narrative_ctx.to_markdown())
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

                    # Almacenar en el historial de turnos anteriores de GameState
                    game_state.game_state_controller.data.prev_turns.append(TurnSummary(player_input=player_input, narration=narration_text))
                    game_state.game_state_controller.data.prev_turns = game_state.game_state_controller.data.prev_turns[-4:]

                    game_state.game_state_controller.save(game_state.world_state)

                    # DEBUG: Imprimir GameState actualizado
                    print(f"\n{Colors.OKCYAN}{Colors.BOLD}--- DEBUG: GameState ---{Colors.ENDC}")
                    print(game_state.game_state_controller.data.model_dump_json(indent=2))
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
