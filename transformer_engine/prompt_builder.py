import os

class PromptBuilder:
    """Clase responsable de la ingeniería de prompts y construcción de la entrada para el LLM."""

    @staticmethod
    def build(rules_path: str, game_context_json: str, user_input: str) -> str:
        """Construye e integra el prompt final para el LLM cargando las reglas desde rules_path.

        Soporta plantillas con placeholders {{context_json}} y {{player_input}},
        o bien concatena las reglas, el contexto y la entrada por defecto.

        Args:
            rules_path: Ruta al archivo Markdown que contiene las instrucciones o reglas.
            game_context_json: Representación JSON del contexto actual (ej. de PlayerState).
            user_input: Entrada del jugador en lenguaje natural o en formato estructurado.

        Returns:
            str: El prompt formateado y listo para ser enviado al LLM.
        """
        if not os.path.exists(rules_path):
            raise FileNotFoundError(f"No se encontró el archivo de reglas en '{rules_path}'.")

        with open(rules_path, "r", encoding="utf-8") as f:
            template = f.read()

        # Si el template tiene las marcas de reemplazo de variables, las sustituimos
        if "{{context_json}}" in template or "{{player_input}}" in template:
            prompt = template.replace("{{context_json}}", game_context_json)
            prompt = prompt.replace("{{player_input}}", user_input)
        else:
            # Si no las tiene, concatenamos de manera predeterminada en un prompt estructurado
            prompt = (
                f"# REGLAS E INSTRUCCIONES DEL ROL\n"
                f"{template}\n\n"
                f"# CONTEXTO DEL JUEGO (ESTADO ACTUAL)\n"
                f"```json\n"
                f"{game_context_json}\n"
                f"```\n\n"
                f"# ACCIÓN DEL JUGADOR / SOLICITUD\n"
                f"\"{user_input}\"\n\n"
                f"Genera únicamente el JSON estructurado válido según el formato especificado."
            )

        return prompt
