import sys
import os
import json
from transformer_engine import DungeonMaster, TransformerModel
from jsonschema import ValidationError

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

    # Contexto lingüístico dinámico inicial como diccionario simple
    context = {
        "visible_entities": ["npc_blacksmith", "npc_guard", "bld_tavern", "bld_shop", "obj_fountain"],
        "previous_references": {},
        "active_conversation": None,
        "player_location": "location_village_square"
    }

    print(f"{Colors.OKCYAN}{Colors.BOLD}--- Contexto Inicial ---{Colors.ENDC}")
    print(f"Localización: {context['player_location']}")
    print(f"Entidades:    {context['visible_entities']}")
    print("-" * 65 + "\n")

    # Rutas de configuración, reglas y esquemas
    config_path = r"Resources/system_data/llm_config.json"
    rules_path = r"Resources/system_data/rules\classifier_rules.md"
    schema_path = r"Resources/system_data/schemas\input_classification.json"

    # Inicialización del adaptador del LLM y del DungeonMaster
    try:
        adapter = TransformerModel(config_path=config_path)
        dm = DungeonMaster(llm_adapter=adapter)
        print(f"{Colors.OKGREEN}[INFO] TransformerModel y DungeonMaster inicializados correctamente.{Colors.ENDC}")
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

            # Serializamos el contexto dinámico actual a JSON string
            context_json_str = json.dumps(context, indent=2, ensure_ascii=False)

            # Clasificación mediante el motor genérico DungeonMaster
            action_result = dm.execute(
                rules_path=rules_path,
                game_context_json=context_json_str,
                user_input=player_input,
                schema_path=schema_path
            )

            print(f"\n{Colors.OKGREEN}{Colors.BOLD}--- JSON de Entrada Clasificada ---{Colors.ENDC}")
            print(json.dumps(action_result, indent=4, ensure_ascii=False))
            print(f"{Colors.OKGREEN}-----------------------------------{Colors.ENDC}")

            # Resolución y actualización secuencial básica del contexto lingüístico
            actions = action_result.get("actions", [])
            for act in actions:
                targets = act.get("targets", [])
                action_name = act.get("action", "")
                
                if targets:
                    main_target = targets[0]
                    context["previous_references"]["eso"] = main_target
                    if "npc_" in main_target:
                        context["previous_references"]["él"] = main_target
                        if action_name == "TALK":
                            context["active_conversation"] = main_target
                    elif "item_" in main_target:
                        context["previous_references"]["objeto"] = main_target

        except ValidationError as ve:
            print(f"\n{Colors.FAIL}[ERROR DE VALIDACIÓN DE ESQUEMA]: {ve.message}{Colors.ENDC}")
        except KeyboardInterrupt:
            print(f"\n\n{Colors.OKBLUE}Saliendo...{Colors.ENDC}")
            break
        except Exception as e:
            print(f"\n{Colors.FAIL}[ERROR INESPERADO]: {e}{Colors.ENDC}")


if __name__ == "__main__":
    main()
