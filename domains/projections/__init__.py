"""Subpaquete de modelos de proyección (DTOs) para AAdventure.

Organizado en dos capas:
- `game.py`: Proyecciones exclusivas para la interfaz de usuario de juego (Game UI).
- `debug.py`: Proyecciones técnicas y diagnósticas para el depurador (Game Debugger) y herramientas de inspección.
"""

from domains.projections.game import (
    ActionCommandProjection,
    AvailableActionsProjection,
    InventoryItemDTO,
    InventoryProjection,
    LocationHierarchyProjection,
    MapItemDTO,
    MapLocationDTO,
    MapNPCDTO,
    MapPlaceDTO,
    MoveOptionProjection,
    NotebookProjection,
    PlaceProjection,
    TurnOutput,
    TurnResultProjection,
    UIStateProjection,
    WorldHierarchyProjection,
    WorldMapProjection,
)
from domains.projections.debug import (
    ConnectionProjection,
    GameSnapshotProjection,
    GameStateProjection,
    LoreBlockDetailProjection,
    LoreConditionDetailProjection,
    LoreGraphProjection,
    PlaceDetailProjection,
    PlayerSummaryProjection,
    RagAntennaScoreProjection,
    RagEvaluationProjection,
    TurnDebugProjection,
)

__all__ = [
    # Game UI Projections & DTOs
    "ActionCommandProjection",
    "TurnOutput",
    "MapItemDTO",
    "MapNPCDTO",
    "MapPlaceDTO",
    "MapLocationDTO",
    "WorldMapProjection",
    "InventoryItemDTO",
    "InventoryProjection",
    "NotebookProjection",
    "TurnResultProjection",
    "PlaceProjection",
    "LocationHierarchyProjection",
    "WorldHierarchyProjection",
    "MoveOptionProjection",
    "AvailableActionsProjection",
    "UIStateProjection",
    # Debug Projections
    "ConnectionProjection",
    "GameSnapshotProjection",
    "GameStateProjection",
    "LoreBlockDetailProjection",
    "LoreConditionDetailProjection",
    "LoreGraphProjection",
    "PlaceDetailProjection",
    "PlayerSummaryProjection",
    "RagAntennaScoreProjection",
    "RagEvaluationProjection",
    "TurnDebugProjection",
]
