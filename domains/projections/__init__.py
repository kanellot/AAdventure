"""Subpaquete de modelos de proyección (DTOs) para AAdventure.

Organizado en dos capas:
- `game.py`: Proyecciones exclusivas para la interfaz de usuario de juego (Game UI).
- `debug.py`: Proyecciones técnicas y diagnósticas para el depurador (Game Debugger) y herramientas de inspección.
"""

from domains.projections.game import (
    ActionCommand,
    ActionCommandProjection,
    AvailableActionsProjection,
    LocationHierarchyProjection,
    MoveOptionProjection,
    PlaceProjection,
    TurnResultProjection,
    UIStateProjection,
    WorldHierarchyProjection,
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
    # Game UI Projections
    "ActionCommand",
    "ActionCommandProjection",
    "AvailableActionsProjection",
    "LocationHierarchyProjection",
    "MoveOptionProjection",
    "PlaceProjection",
    "TurnResultProjection",
    "UIStateProjection",
    "WorldHierarchyProjection",
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
