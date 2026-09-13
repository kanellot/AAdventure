"""Persistencia de preferencias del usuario y aventura predeterminada."""

import os
import json
from typing import Optional, List, Dict, Any

PREFERENCES_FILE_PATH = os.path.join("Resources", "system_data", "debugger_preferences.json")
FALLBACK_ADVENTURE_PATH = os.path.join("Resources", "adventure_data", "Adventure.aad")


def _get_prefs_file_path() -> str:
    """Devuelve la ruta absoluta del archivo de preferencias."""
    return os.path.abspath(PREFERENCES_FILE_PATH)


def load_preferences() -> Dict[str, Any]:
    """Carga el diccionario de preferencias guardado o uno por defecto si no existe."""
    prefs_path = _get_prefs_file_path()
    if os.path.exists(prefs_path):
        try:
            with open(prefs_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    return {
        "last_selected_aad": None,
        "recent_adventures": [],
    }


def save_preferences(prefs: Dict[str, Any]) -> None:
    """Guarda el diccionario de preferencias en disco."""
    prefs_path = _get_prefs_file_path()
    os.makedirs(os.path.dirname(prefs_path), exist_ok=True)
    try:
        with open(prefs_path, "w", encoding="utf-8") as f:
            json.dump(prefs, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[WARN] No se pudieron guardar las preferencias del selector: {e}")


def get_default_adventure_path() -> Optional[str]:
    """Obtiene la ruta a la aventura predeterminada (la última seleccionada).

    Si la guardada en preferencias no existe o no se ha definido, busca el fallback Adventure.aad.
    """
    prefs = load_preferences()
    last_aad = prefs.get("last_selected_aad")
    if last_aad and os.path.exists(last_aad):
        return os.path.abspath(last_aad)

    # Fallback si existe la aventura por defecto del proyecto
    if os.path.exists(FALLBACK_ADVENTURE_PATH):
        return os.path.abspath(FALLBACK_ADVENTURE_PATH)

    # Buscar si alguna de las recientes todavía existe
    for recent in prefs.get("recent_adventures", []):
        if recent and os.path.exists(recent):
            return os.path.abspath(recent)

    return None


def set_default_adventure_path(aad_path: str) -> None:
    """Registra una aventura como la predeterminada y la añade a las recientes."""
    if not aad_path:
        return

    abs_path = os.path.abspath(aad_path)
    prefs = load_preferences()
    prefs["last_selected_aad"] = abs_path

    recent: List[str] = prefs.get("recent_adventures", [])
    # Evitar duplicados y colocar al principio
    if abs_path in recent:
        recent.remove(abs_path)
    recent.insert(0, abs_path)

    # Limitar a las 10 más recientes
    prefs["recent_adventures"] = recent[:10]
    save_preferences(prefs)


def get_recent_adventures() -> List[str]:
    """Devuelve las rutas existentes registradas en el historial de recientes."""
    prefs = load_preferences()
    result = []
    for p in prefs.get("recent_adventures", []):
        if p and os.path.exists(p):
            result.append(os.path.abspath(p))
    return result
