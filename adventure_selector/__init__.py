"""Módulo desacoplado para selección, inspección y gestión de aventuras (.aad)."""

from typing import Optional
from adventure_selector.models import AdventureMetadata
from adventure_selector.reader import read_adventure_metadata
from adventure_selector.scanner import scan_adventures
from adventure_selector.storage import (
    get_default_adventure_path,
    set_default_adventure_path,
    get_recent_adventures,
    load_preferences,
    save_preferences,
)
from adventure_selector.dialog import AdventureSelectorDialog


def open_adventure_selector(parent=None, preselected_path: Optional[str] = None) -> Optional[str]:
    """Abre el diálogo modal de selección de aventura y devuelve la ruta elegida (o None si se canceló)."""
    dialog = AdventureSelectorDialog(parent=parent, preselected_path=preselected_path)
    if dialog.exec():
        return dialog.get_selected_path()
    return None


__all__ = [
    "AdventureMetadata",
    "read_adventure_metadata",
    "scan_adventures",
    "get_default_adventure_path",
    "set_default_adventure_path",
    "get_recent_adventures",
    "load_preferences",
    "save_preferences",
    "AdventureSelectorDialog",
    "open_adventure_selector",
]
