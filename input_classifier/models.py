from typing import Any
from pydantic import BaseModel, Field, model_validator


class ActionDetail(BaseModel):
    """Representa los detalles de una única acción semántica del jugador."""
    action: str = Field(
        description="Acción principal detectada (ej. MOVE, TALK, LOOK, GIVE, OPEN, USE, TAKE, ATTACK, WAIT, EXPLAIN)."
    )
    targets: list[str] = Field(
        default_factory=list,
        description="Lista de IDs de entidades del juego involucradas en la acción."
    )
    attributes: dict[str, Any] = Field(
        default_factory=dict,
        description="Diccionario dinámico de atributos y matices opcionales (ej. speed, topic, weapon_state)."
    )


class InputActions(BaseModel):
    """Contrato semántico de salida que envuelve la lista cronológica de acciones del jugador."""
    actions: list[ActionDetail] = Field(
        description="Lista de una o más acciones ordenadas cronológicamente que el jugador desea realizar."
    )

    @model_validator(mode="after")
    def validate_min_actions(self) -> "InputActions":
        """Valida que la lista de acciones contenga al menos una acción."""
        if not self.actions:
            raise ValueError("La lista de acciones 'actions' debe contener al menos un elemento.")
        return self


class ClassificationContext(BaseModel):
    """Información de contexto mínima necesaria para resolver referencias en la clasificación."""
    visible_entities: list[str] = Field(
        default_factory=list,
        description="Lista de IDs de entidades que el jugador puede ver en la localización actual."
    )
    previous_references: dict[str, str] = Field(
        default_factory=dict,
        description="Diccionario de pronombres/referencias recientes y su entidad asociada (ej. {'él': 'npc_roderick'})."
    )
    active_conversation: str | None = Field(
        default=None,
        description="ID del NPC con el que se está conversando actualmente, si hay alguno activo."
    )
    player_location: str | None = Field(
        default=None,
        description="ID de la localización actual del jugador (ej. 'location_market')."
    )
