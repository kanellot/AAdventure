import os
import json
from .models import ClassificationContext


class PromptBuilder:
    """Clase responsable de la ingeniería de prompts y construcción de la entrada para el LLM."""

    def __init__(self, template_path: str = None):
        """Inicializa el constructor con la ruta de la plantilla de prompt.

        Args:
            template_path: Ruta al archivo Markdown que contiene las instrucciones del sistema.
                           Si es None, busca en 'input_classifier/prompts/classifier.md'.
        """
        if template_path is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            template_path = os.path.join(current_dir, "prompts", "classifier.md")
        self.template_path = template_path
        self._template = None

    def _load_template(self) -> str:
        """Carga la plantilla del sistema desde el disco o usa un fallback si no existe."""
        if self._template is None:
            if os.path.exists(self.template_path):
                try:
                    with open(self.template_path, "r", encoding="utf-8") as f:
                        self._template = f.read()
                except Exception:
                    self._template = self._get_fallback_template()
            else:
                self._template = self._get_fallback_template()
        return self._template

    def build(self, player_input: str, context: ClassificationContext) -> str:
        """Construye e integra el prompt final para el LLM.

        Args:
            player_input: Mensaje de entrada del jugador en lenguaje natural.
            context: Contexto lingüístico mínimo actual de la partida.

        Returns:
            str: El prompt formateado y listo para ser enviado al LLM.
        """
        template = self._load_template()

        # Serializamos el objeto context a formato JSON string amigable
        context_dict = context.model_dump()
        context_json_str = json.dumps(context_dict, indent=2, ensure_ascii=False)

        # Reemplazamos las variables en la plantilla
        prompt = template.replace("{{context_json}}", context_json_str)
        prompt = prompt.replace("{{player_input}}", player_input)

        return prompt

    def _get_fallback_template(self) -> str:
        """Plantilla de respaldo mínima y hardcodeada en caso de fallo en la lectura física de la plantilla."""
        return """Eres el motor de clasificación semántica para un juego de rol de texto interactivo.
Interpreta la entrada del usuario en lenguaje natural y tradúcela a un JSON estructurado con la intención semántica de su acción.

Format de salida esperado (JSON válido):
{
  "action": "Acción principal en mayúsculas (ej. MOVE, TALK, LOOK, GIVE, OPEN, USE, TAKE, ATTACK)",
  "targets": ["Lista de IDs de entidades involucradas. Coincidir con visible_entities o active_conversation"],
  "content": "Mensaje de diálogo literal si aplica (string o null)",
  "attributes": {"Matices de la acción como dirección, velocidad, tema, etc. (dict dinámico)"}
}

Contexto actual del juego:
{{context_json}}

Entrada del jugador:
"{{player_input}}"

Genera únicamente el JSON estructurado válido sin formato markdown adicional fuera de las comillas triples de código JSON.
"""
