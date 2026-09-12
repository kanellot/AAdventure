"""Modelo de dominio para el registro histórico de conversaciones con NPCs."""

from typing import Dict, List
from pydantic import BaseModel, Field


class ConversationRecord(BaseModel):
    """Registro secuencial de mensajes intercambiados en un diálogo."""

    id: str
    msg: List[Dict[str, str]] = Field(default_factory=list)
