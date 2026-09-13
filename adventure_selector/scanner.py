"""Escáner y catalogador de archivos de aventura (.aad) en el proyecto."""

import os
from typing import List, Optional
from adventure_selector.models import AdventureMetadata
from adventure_selector.reader import read_adventure_metadata
from adventure_selector.storage import (
    get_default_adventure_path,
    get_recent_adventures,
)

DEFAULT_SCAN_DIRS = [
    os.path.join("Resources", "adventure_data"),
]


def scan_adventures(extra_directories: Optional[List[str]] = None) -> List[AdventureMetadata]:
    """Escanea las carpetas estándar y el historial reciente para catalogar todas las aventuras disponibles."""
    all_dirs = list(DEFAULT_SCAN_DIRS)
    if extra_directories:
        for d in extra_directories:
            if d and os.path.isdir(d) and d not in all_dirs:
                all_dirs.append(d)

    found_paths: List[str] = []
    seen = set()

    # 1. Asegurar que la aventura por defecto actual se incluya si existe
    default_path = get_default_adventure_path()
    if default_path and os.path.exists(default_path):
        norm = os.path.normcase(os.path.abspath(default_path))
        if norm not in seen:
            seen.add(norm)
            found_paths.append(default_path)

    # 2. Aventuras recientes registradas
    for recent_p in get_recent_adventures():
        if os.path.exists(recent_p):
            norm = os.path.normcase(os.path.abspath(recent_p))
            if norm not in seen:
                seen.add(norm)
                found_paths.append(recent_p)

    # 3. Escaneo de directorios
    for scan_dir in all_dirs:
        if not os.path.isdir(scan_dir):
            continue
        for entry in os.listdir(scan_dir):
            if entry.lower().endswith(".aad"):
                full_path = os.path.join(scan_dir, entry)
                if os.path.isfile(full_path):
                    norm = os.path.normcase(os.path.abspath(full_path))
                    if norm not in seen:
                        seen.add(norm)
                        found_paths.append(full_path)

    # 4. Extraer metadatos de cada archivo
    metadata_list: List[AdventureMetadata] = []
    for path in found_paths:
        meta = read_adventure_metadata(path)
        metadata_list.append(meta)

    # 5. Ordenar: Predeterminada primero, luego válidas por fecha mod reciente, luego erróneas
    default_norm = os.path.normcase(os.path.abspath(default_path)) if default_path else ""

    def sort_key(item: AdventureMetadata):
        is_default = 1 if (default_norm and os.path.normcase(os.path.abspath(item.file_path)) == default_norm) else 0
        is_val = 1 if item.is_valid else 0
        mod_t = item.modified_time or ""
        return (is_default, is_val, mod_t)

    metadata_list.sort(key=sort_key, reverse=True)
    return metadata_list
