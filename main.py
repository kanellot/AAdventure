import sys
import os
import json
from transformer_engine import DungeonMaster, TransformerModel
from pydantic import ValidationError
from domains import Actions, ActionItem, PreActionContext, NarrationResponse, DialogueResponse, Conversation, Message
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

            # Determinar el estado de la máquina de estados actual
            current_state = game_state.player_state.data.player_state.upper()

            if current_state == "TALK":
                # --- ESTADO TALK (Conversación Activa) ---
                # 1. Asegurar que active_conversations esté inicializado
                active = game_state.player_state.data.active_conversations
                if not active:
                    conversation_id = f"c_{len(game_state.world_state.world.conversations) + 1}"
                    active = Conversation(
                        id=conversation_id,
                        character_01="Player",
                        character_02=game_state.player_state.data.player_target,
                        messages=[]
                    )
                    game_state.player_state.data.active_conversations = active

                # 2. Registrar el mensaje enviado por el jugador
                msg_id = f"m_{len(active.messages) + 1}"
                active.messages.append(Message(
                    id=msg_id,
                    character="Player",
                    msg=player_input
                ))

                # 3. Capturar estado previo del jugador
                prev_player_state = game_state.player_state.data.model_copy(deep=True)

                # 4. Construir contexto para el diálogo (usamos TALK como acción ejecutada)
                executed_actions = Actions(actions=[
                    ActionItem(
                        action="TALK",
                        targets=[game_state.player_state.data.player_target],
                        content=player_input
                    )
                ])
                narrative_ctx = ContextBuilder.build_narrative_context(
                    prev_state=prev_player_state,
                    curr_state=game_state.player_state.data,
                    executed_actions=executed_actions,
                    player_input=player_input,
                    world_state=game_state.world_state
                )

                # DEBUG: Imprimir NARRATIVE_CONTEXT
                print(f"\n{Colors.OKCYAN}{Colors.BOLD}--- DEBUG: NARRATIVE_CONTEXT (TALK - Dialogue) ---{Colors.ENDC}")
                print(narrative_ctx.model_dump_json(indent=2))
                print(f"{Colors.OKCYAN}---------------------------------------------------{Colors.ENDC}")

                # 5. Generar diálogo usando la skill dialogue.md
                dialogue_rules_path = r"Resources/system_data/rules/dialogue.md"
                dialogue_result = dm.execute(
                    rules_path=dialogue_rules_path,
                    gamecontext=narrative_ctx,
                    player_input=player_input,
                    response_model=DialogueResponse
                )
                npc_response = dialogue_result["narration"]
                dialogue_state = dialogue_result["dialogue_state"].upper()

                # Imprimir la respuesta del NPC
                print(f"\n{Colors.OKGREEN}{Colors.BOLD}[{game_state.player_state.data.player_target}] > {Colors.ENDC}{npc_response}")

                # 6. Registrar la respuesta del NPC en el historial
                active = game_state.player_state.data.active_conversations
                msg_id = f"m_{len(active.messages) + 1}"
                active.messages.append(Message(
                    id=msg_id,
                    character=game_state.player_state.data.player_target,
                    msg=npc_response
                ))

                # 7. Si el diálogo ha finalizado, archivar y volver a NORMAL
                if dialogue_state == "NORMAL":
                    # Mover conversación a la lista global en el world state
                    game_state.world_state.world.conversations.append(active)
                    game_state.player_state.data.active_conversations = None
                    game_state.player_state.update_state("NORMAL")
                    game_state.player_state.data.player_target = ""
                    print(f"\n{Colors.OKBLUE}[INFO] Conversación finalizada con {prev_player_state.player_target}. Volviendo a exploración.{Colors.ENDC}")
                
                game_state.player_state.save(game_state.world_state)

            else:
                # --- ESTADO NORMAL (Exploración) ---
                # 1. Construir el objeto de contexto PRE_ACTION
                pre_action_ctx = PreActionContext(
                    player_state=game_state.player_state.data,
                    player_input=player_input
                )

                # DEBUG: Imprimir PRE_ACTION
                print(f"\n{Colors.OKCYAN}{Colors.BOLD}--- DEBUG: PRE_ACTION (PreActionContext) ---{Colors.ENDC}")
                print(pre_action_ctx.model_dump_json(indent=2))
                print(f"{Colors.OKCYAN}--------------------------------------------{Colors.ENDC}")

                # 2. Clasificar acción usando DungeonMaster
                action_result = dm.execute(
                    rules_path=rules_path,
                    gamecontext=pre_action_ctx,
                    player_input=player_input,
                    response_model=Actions
                )

                # 3. Capturar el estado del jugador antes de la mutación
                prev_player_state = game_state.player_state.data.model_copy(deep=True)

                # 4. Mutar el estado del juego
                game_state.mutate(action_result)

                # DEBUG: Imprimir ACTION
                print(f"\n{Colors.OKGREEN}{Colors.BOLD}--- DEBUG: ACTION (Clasificación de Acciones) ---{Colors.ENDC}")
                print(json.dumps(action_result, indent=2, ensure_ascii=False))
                print(f"{Colors.OKGREEN}-------------------------------------------------{Colors.ENDC}")

                # 5. Comprobar si la mutación nos ha llevado al estado TALK
                if game_state.player_state.data.player_state.upper() == "TALK":
                    # Inicializar nueva conversación
                    conversation_id = f"c_{len(game_state.world_state.world.conversations) + 1}"
                    active = Conversation(
                        id=conversation_id,
                        character_01="Player",
                        character_02=game_state.player_state.data.player_target,
                        messages=[]
                    )
                    game_state.player_state.data.active_conversations = active

                    # Registrar mensaje inicial del jugador
                    msg_id = f"m_{len(active.messages) + 1}"
                    active.messages.append(Message(
                        id=msg_id,
                        character="Player",
                        msg=player_input
                    ))

                    # Construir contexto para el diálogo inicial
                    narrative_ctx = ContextBuilder.build_narrative_context(
                        prev_state=prev_player_state,
                        curr_state=game_state.player_state.data,
                        executed_actions=Actions.model_validate(action_result),
                        player_input=player_input,
                        world_state=game_state.world_state
                    )

                    # Generar primera réplica del NPC usando dialogue.md
                    dialogue_rules_path = r"Resources/system_data/rules/dialogue.md"
                    dialogue_result = dm.execute(
                        rules_path=dialogue_rules_path,
                        gamecontext=narrative_ctx,
                        player_input=player_input,
                        response_model=DialogueResponse
                    )
                    npc_response = dialogue_result["narration"]
                    dialogue_state = dialogue_result["dialogue_state"].upper()

                    # Imprimir respuesta
                    print(f"\n{Colors.OKGREEN}{Colors.BOLD}[{game_state.player_state.data.player_target}] > {Colors.ENDC}{npc_response}")

                    # Registrar réplica del NPC
                    active = game_state.player_state.data.active_conversations
                    msg_id = f"m_{len(active.messages) + 1}"
                    active.messages.append(Message(
                        id=msg_id,
                        character=game_state.player_state.data.player_target,
                        msg=npc_response
                    ))

                    if dialogue_state == "NORMAL":
                        game_state.world_state.world.conversations.append(active)
                        game_state.player_state.data.active_conversations = None
                        game_state.player_state.update_state("NORMAL")
                        game_state.player_state.data.player_target = ""
                        print(f"\n{Colors.OKBLUE}[INFO] Conversación finalizada. Volviendo a exploración.{Colors.ENDC}")

                    game_state.player_state.save(game_state.world_state)

                else:
                    # Seguir en exploración normal, usar narrador general (narrator.md)
                    narrative_ctx = ContextBuilder.build_narrative_context(
                        prev_state=prev_player_state,
                        curr_state=game_state.player_state.data,
                        executed_actions=Actions.model_validate(action_result),
                        player_input=player_input,
                        world_state=game_state.world_state
                    )

                    # DEBUG: Imprimir NARRATIVE_CONTEXT
                    print(f"\n{Colors.OKCYAN}{Colors.BOLD}--- DEBUG: NARRATIVE_CONTEXT (NORMAL) ---{Colors.ENDC}")
                    print(narrative_ctx.model_dump_json(indent=2))
                    print(f"{Colors.OKCYAN}-----------------------------------------{Colors.ENDC}")

                    # Generar narración
                    narrator_rules_path = r"Resources/system_data/rules/narrator.md"
                    narration_result = dm.execute(
                        rules_path=narrator_rules_path,
                        gamecontext=narrative_ctx,
                        player_input=player_input,
                        response_model=NarrationResponse
                    )
                    narration_text = narration_result["narration"]

                    # Imprimir narración
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
