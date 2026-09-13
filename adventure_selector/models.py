"""Modelos de datos para el selector de aventuras."""

from typing import Optional
from pydantic import BaseModel, Field


class AdventureMetadata(BaseModel):
    """Metadatos descriptivos de un archivo de aventura (.aad)."""

    file_path: str = Field(..., description="Ruta absoluta o relativa al archivo .aad")
    file_name: str = Field(..., description="Nombre del archivo con extensión")
    file_size_kb: float = Field(default=0.0, description="Tamaño del archivo en kilobytes")
    modified_time: str = Field(default="", description="Fecha y hora de última modificación")

    # Datos narrativos y de mundo
    title: str = Field(default="Aventura sin título", description="Nombre del mundo o título de la aventura")
    description: str = Field(default="", description="Descripción narrativa del mundo")
    player_name: str = Field(default="Aventurero", description="Nombre del personaje principal")
    player_description: str = Field(default="", description="Descripción del personaje")
    initial_place: str = Field(default="", description="Lugar de inicio de la aventura")

    # Métricas y conteo de entidades
    locations_count: int = Field(default=0, description="Número de localizaciones/regiones")
    places_count: int = Field(default=0, description="Número total de lugares")
    npcs_count: int = Field(default=0, description="Número total de NPCs")
    objects_count: int = Field(default=0, description="Número de objetos en el catálogo")
    lore_blocks_count: int = Field(default=0, description="Número de bloques de lore en el catálogo")

    # Estado de integridad
    is_valid: bool = Field(default=True, description="True si el archivo es un .aad válido y legible")
    error_message: Optional[str] = Field(default=None, description="Mensaje de error si el archivo es inválido o corrupto")
