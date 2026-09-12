"""Constructor de prompts e inyección de plantillas para Game Engine."""

import os
from typing import Dict, Optional
from pydantic import BaseModel


class PromptBuilder:
    """Construye el prompt final inyectando contexto y reglas antes de invocar al LLM."""

    @classmethod
    def build(
        cls,
        rules_path: str,
        gamecontext: BaseModel,
        game_context_str: str,
        user_input: str,
        template_tags: Optional[Dict[str, str]] = None,
    ) -> str:
        """Lee el template de reglas, sustituye tags y devuelve el prompt compilado."""
        if not os.path.exists(rules_path):
            raise FileNotFoundError(f"No se encontró el archivo de reglas en '{rules_path}'.")

        with open(rules_path, "r", encoding="utf-8") as f:
            template = f.read()

        tags_found = False
        if template_tags:
            for tag_name, tag_value in template_tags.items():
                tag_marker = f"<{tag_name}>"
                if tag_marker in template:
                    template = template.replace(tag_marker, str(tag_value))
                    tags_found = True

        if "<player_input>" in template:
            template = template.replace("<player_input>", user_input)
            tags_found = True

        if "{{context_json}}" in template or "{{player_input}}" in template:
            prompt = template.replace("{{context_json}}", game_context_str)
            prompt = prompt.replace("{{player_input}}", user_input)
        elif tags_found:
            prompt = template
        else:
            prompt = (
                f"# REGLAS E INSTRUCCIONES DEL ROL\n"
                f"{template}\n\n"
                f"# CONTEXTO DEL JUEGO (ESTADO ACTUAL)\n"
                f"```markdown\n"
                f"{game_context_str}\n"
                f"```\n\n"
                f"# ACCIÓN DEL JUGADOR / SOLICITUD\n"
                f'"{user_input}"\n\n'
                f"Genera únicamente el JSON estructurado válido según el formato especificado."
            )

        return prompt
