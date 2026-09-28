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


def main():
    parser = argparse.ArgumentParser(description="AAdventure - Motor Narrativo D&D")
    parser.add_argument("--editor", "-e", action="store_true", help="Lanza el editor gráfico de historias")
    parser.add_argument("--debug", "--play-debug", "-d", dest="debug", action="store_true", help="Lanza el depurador gráfico interactivo")
    parser.add_argument("--select-adventure", "-s", action="store_true", help="Abre el selector gráfico de aventuras")
    parser.add_argument("--verbose", "-v", action="store_true", help="Activa el modo detallado/debug en la consola")
    parser.add_argument("--test", "-t", action="store_true", help="Activa el modo de prueba usando backends mock para LLM y embeddings")
    args = parser.parse_args()

    if args.test:
        os.environ["TESTING"] = "1"

    # 1. Selector de aventura si se solicita explícitamente
    if args.select_adventure:
        chosen = open_adventure_selector()
        if chosen:
            set_default_adventure_path(chosen)
            print(f"[INFO] Aventura seleccionada como predeterminada: {chosen}")
        sys.exit(0)

    # 2. Resolución de la aventura a cargar
    if os.path.exists(DEFAULT_AAD_PATH):
        aad_to_load = DEFAULT_AAD_PATH
    else:
        aad_to_load = get_default_adventure_path() or DEFAULT_AAD_PATH

    # 3. Suite gráfica unificada: Editor o Depurador
    if args.editor:
        try:
            from editor_debugger.main import start_editor_debugger
            start_editor_debugger(mode="editor", aad_path=aad_to_load if os.path.exists(aad_to_load) else None)
            sys.exit(0)
        except ImportError as ie:
            print(f"[ERROR] No se pudo iniciar la suite gráfica: {ie}")
            print("Asegúrate de tener instalado PySide6: pip install PySide6")
            sys.exit(1)

    if args.debug:
        try:
            from editor_debugger.main import start_editor_debugger
            start_editor_debugger(mode="debugger", aad_path=aad_to_load)
            sys.exit(0)
        except ImportError as ie:
            print(f"[ERROR] No se pudo iniciar el depurador gráfico: {ie}")
            print("Asegúrate de tener instalado PySide6: pip install PySide6")
            sys.exit(1)

    # 4. Verificación para consola interactiva
    if not os.path.exists(aad_to_load) or not aad_to_load.lower().endswith(".aad"):
        print(f"[ERROR CRÍTICO] No se encontró ningún paquete de aventura (.aad) en: {aad_to_load}")
        print("Usa --select-adventure (-s) para elegir una aventura disponible o especifica una ruta válida.")
        sys.exit(1)

    # Modo por defecto: Consola Interactiva (CLI) con AdventureSession
    try:
        session = AdventureSession.create(aad_to_load)
    except Exception as e:
        print(f"[ERROR CRÍTICO AL INICIALIZAR LA SESIÓN]: {e}")
        sys.exit(1)

    from cli import start_cli
    start_cli(session=session, verbose=args.verbose)


if __name__ == "__main__":
    main()
