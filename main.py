import sys
from input_classifier import (
    InputClassifier,
    LlamaCppAdapter,
    ClassificationContext,
    InputClassifierError,
)

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

    # Contexto lingüístico simulado inicial
    context = ClassificationContext(
        visible_entities=["npc_blacksmith", "npc_guard", "bld_tavern", "bld_shop", "obj_fountain"],
        previous_references={},
        active_conversation=None,
        player_location="location_village_square"
    )

    print(f"{Colors.OKCYAN}{Colors.BOLD}--- Contexto Inicial ---{Colors.ENDC}")
    print(f"Localización: {context.player_location}")
    print(f"Entidades:    {context.visible_entities}")
    print("-" * 65 + "\n")

    # Inicialización directa del adaptador real llama-cpp
    try:
        adapter = LlamaCppAdapter()
        classifier = InputClassifier(llm_adapter=adapter)
        print(f"{Colors.OKGREEN}[INFO] LlamaCppAdapter inicializado correctamente.{Colors.ENDC}")
    except Exception as e:
        print(f"{Colors.FAIL}[ERROR DE CONFIGURACIÓN]{Colors.ENDC}")
        print(f"No se pudo cargar el clasificador semántico: {e}")
        print("\nPor favor, instala 'llama-cpp-python' y configura el modelo local GGUF.")
        sys.exit(1)

    print(f"\nIntroduce tu acción. Escribe {Colors.BOLD}'exit'{Colors.ENDC} para salir.")

    while True:
        try:
            player_input = input(f"\n{Colors.BOLD}[Jugador] > {Colors.ENDC}").strip()
            if not player_input:
                continue

            if player_input.lower() in ["exit", "quit", "q"]:
                print(f"\n{Colors.OKBLUE}Saliendo... ¡Hasta pronto!{Colors.ENDC}")
                break

            # Clasificación mediante el LLM
            action_result = classifier.classify(player_input, context)

            print(f"\n{Colors.OKGREEN}{Colors.BOLD}--- JSON de Entrada Clasificada ---{Colors.ENDC}")
            print(action_result.model_dump_json(indent=4))
            print(f"{Colors.OKGREEN}-----------------------------------{Colors.ENDC}")

            # Resolución y actualización secuencial básica del contexto lingüístico
            for act in action_result.actions:
                if act.targets:
                    main_target = act.targets[0]
                    context.previous_references["eso"] = main_target
                    if "npc_" in main_target:
                        context.previous_references["él"] = main_target
                        if act.action == "TALK":
                            context.active_conversation = main_target
                    elif "item_" in main_target:
                        context.previous_references["objeto"] = main_target

        except InputClassifierError as ice:
            print(f"\n{Colors.FAIL}[ERROR DE CLASIFICACIÓN]: {ice}{Colors.ENDC}")
        except KeyboardInterrupt:
            print(f"\n\n{Colors.OKBLUE}Saliendo...{Colors.ENDC}")
            break
        except Exception as e:
            print(f"\n{Colors.FAIL}[ERROR INESPERADO]: {e}{Colors.ENDC}")


if __name__ == "__main__":
    main()
