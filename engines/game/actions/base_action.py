"""Clase base para las acciones narrativas del juego."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Generic, Optional, Tuple, Type, TypeVar

from domains import ContextType, ResponseType
from engines.game.prompt_builder import PromptBuilder
from engines.game.state_controller import GameStateController
from engines.transformer import TransformerEngine

logger = logging.getLogger(__name__)

C = TypeVar("C", bound=ContextType)
R = TypeVar("R", bound=ResponseType)


@dataclass
class NarrativeResult:
    """Resultado enriquecido de una acción narrativa."""

    msg: str
    extra: Any = None
    prompt: Optional[str] = None


class BaseAction(ABC, Generic[C, R]):
    """Interfaz base para las acciones narrativas del juego."""

    @property
    @abstractmethod
    def rules_path(self) -> str:
        """Ruta al archivo Markdown de reglas de rol para el LLM."""
        pass

    @property
    @abstractmethod
    def response_model(self) -> Type[R]:
        """Clase del modelo Pydantic para validar la respuesta estructurada del LLM."""
        pass

    @property
    def profile_name(self) -> str:
        """Nombre del perfil de inferencia del LLM."""
        return "narrator"

    @abstractmethod
    def build_context(
            self,
            controller: GameStateController,
            player_input: str = "",
    ) -> C:
        """Construye y retorna el modelo de contexto para el LLM."""
        pass

    def get_template_tags(self, ctx: C) -> Dict[str, str]:
        """Genera tags runtime para inyectar en la plantilla del prompt."""
        return {}

    def to_markdown(self, ctx: C) -> str:
        """Genera la representación Markdown de respaldo del contexto."""
        return ""

    def build_prompt(self, ctx: C, player_input: str) -> str:
        """Construye el prompt completo utilizando PromptBuilder."""
        tags = self.get_template_tags(ctx)
        ctx_md = self.to_markdown(ctx)
        return PromptBuilder.build(
            rules_path=self.rules_path,
            game_context_str=ctx_md,
            user_input=player_input,
            template_tags=tags,
        )

    @abstractmethod
    def fallback_narrative(self, controller: GameStateController, ctx: C) -> Tuple[str, Any]:
        """Genera la narración determinista de respaldo cuando no se usa LLM."""
        pass

    def generate_narrative(
            self,
            controller: GameStateController,
            player_input: str = "",
            transformer_engine: Optional[TransformerEngine] = None,
    ) -> NarrativeResult:
        """Genera la narrativa del turno invocando al TransformerEngine o usando el fallback determinista."""
        ctx = self.build_context(controller, player_input)
        prompt: Optional[str] = None

        if transformer_engine is not None:
            try:
                prompt = self.build_prompt(ctx, player_input)
                schema = self.response_model.model_json_schema()
                raw_dict = transformer_engine.execute(
                    prompt=prompt,
                    response_schema=schema,
                    response_model=self.response_model,
                    profile_name=self.profile_name,
                )
                msg = raw_dict.get("msg", "").strip()
                extra = raw_dict.get("affinity", None)
                if msg:
                    return NarrativeResult(msg=msg, extra=extra, prompt=prompt)
            except Exception as e:
                logger.warning("Fallo en inferencia LLM para %s: %s. Usando fallback.", self.__class__.__name__, e)

        fb_msg, fb_extra = self.fallback_narrative(controller, ctx)
        return NarrativeResult(msg=fb_msg, extra=fb_extra, prompt=prompt)
