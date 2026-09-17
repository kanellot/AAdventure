"""Punto de entrada principal (Launcher) de AAdventure.

Parsea los argumentos de línea de comandos e inicia el subsistema correspondiente:
- --editor / -e: Editor gráfico de historias (editor)
- --debug / --play-debug / -d: Depurador gráfico Qt (game_debugger)
- Por defecto: Interfaz de consola interactiva (cli) con soporte de modo verbose (-v) y modo test (--test).
"""

import argparse
import os
import sys

from adventure_selector import (
    get_default_adventure_path,
    open_adventure_selector,
    set_default_adventure_path,
)
from engines import AdventureSession

DEFAULT_AAD_PATH = os.path.join("Resources", "adventure_data", "Adventure.aad")
LLM_CONFIG_PATH = os.path.join("Resources", "system_data", "llm_config.json")


def main():
    parser = argparse.ArgumentParser(description="AAdventure - Motor Narrativo D&D")
    parser.add_argument("--editor", "-e", action="store_true", help="Lanza el editor gráfico de historias")
    parser.add_argument("--debug", "--play-debug", "-d", dest="debug", action="store_true", help="Lanza el depurador gráfico interactivo")
    parser.add_argument("--select-adventure", "-s", action="store_true", help="Abre el selector gráfico de aventuras")
    parser.add_argument("--verbose", "-v", action="store_true", help="Activa el modo detallado/debug en la consola")
    parser.add_argument("--test", action="store_true", help="Arranca engines con backends simulados (mocked) para pruebas sin LLM externo")
    parser.add_argument("aad_file", nargs="?", default=None, help="Ruta al archivo de aventura .aad")
    args = parser.parse_args()

    # 1. Modo Editor Gráfico
    if args.editor:
        try:
            from editor.main import start_editor
            start_editor()
            sys.exit(0)
        except ImportError as ie:
            print(f"[ERROR] No se pudo iniciar el editor gráfico: {ie}")
            print("Asegúrate de tener instalado PySide6: pip install PySide6")
            sys.exit(1)

    # 2. Selector de Aventura (si se solicita explícitamente)
    if args.select_adventure:
        chosen = open_adventure_selector()
        if not chosen:
            print("[INFO] Selección de aventura cancelada. Saliendo.")
            sys.exit(0)
        args.aad_file = chosen

    # 3. Resolución de la ruta del paquete canónico .aad
    if args.aad_file:
        aad_to_load = args.aad_file
        if not os.path.exists(aad_to_load) or not aad_to_load.lower().endswith(".aad"):
            print(f"[ERROR] El archivo especificado no existe o no es un paquete .aad válido: {aad_to_load}")
            sys.exit(1)
        set_default_adventure_path(aad_to_load)
    else:
        aad_to_load = get_default_adventure_path() or DEFAULT_AAD_PATH

    if not os.path.exists(aad_to_load) or not aad_to_load.lower().endswith(".aad"):
        print(f"[ERROR CRÍTICO] No se encontró ningún paquete de aventura (.aad) en: {aad_to_load}")
        print("Usa --select-adventure (-s) para elegir una aventura disponible o especifica una ruta válida.")
        sys.exit(1)

    # 4. Inicialización de la sesión de aventura (Normal vs --test)
    try:
        if args.test:
            session = AdventureSession.start_for_testing(aad_to_load)
        else:
            session = AdventureSession.start(aad_to_load, config_path=LLM_CONFIG_PATH)
    except Exception as e:
        print(f"[ERROR CRÍTICO AL INICIALIZAR LA SESIÓN]: {e}")
        sys.exit(1)

    # 5. Despacho al cliente correspondiente
    if args.debug:
        try:
            from game_debugger.main import start_debugger
            start_debugger(session=session, aad_path=aad_to_load)
            sys.exit(0)
        except ImportError as ie:
            print(f"[ERROR] No se pudo iniciar el depurador gráfico: {ie}")
            print("Asegúrate de tener instalado PySide6: pip install PySide6")
            sys.exit(1)
    else:
        # Modo por defecto: Consola Interactiva (CLI)
        from cli import start_cli
        start_cli(session=session, verbose=args.verbose)


if __name__ == "__main__":
    main()
