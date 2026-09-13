"""Modelo de configuración de simulación de historia."""

from pydantic import BaseModel, Field


class StoryConfig(BaseModel):
    """Banderas de configuración para la simulación de la historia."""

    elapsed_time: bool = Field(default=True, description="Si está activo, el movimiento avanza el tiempo transcurrido.")
    fog_war: bool = Field(default=True, description="Si está activo, solo los lugares visitados y contiguos son conocidos.")
