# Detalles de Implementación: Módulo InputClassifier

### Estructura de Archivos del Módulo

El módulo `input_classifier` está ubicado en la raíz del proyecto y presenta la siguiente estructura modular:

```text
input_classifier/
├── __init__.py          # Fachada e iterfaz pública exportada
├── classifier.py        # Orquestador y fachada pública principal
├── prompt_builder.py    # Carga de plantillas e ingeniería de prompts
├── llm_adapter.py       # Abstracción DIP y adaptadores de LLM (llama-cpp-python)
├── validator.py         # Validación estructural de salida con Pydantic
├── models.py            # Modelos de datos Pydantic (ActionDetail, InputAction, ClassificationContext)
├── exceptions.py        # Jerarquía de excepciones personalizadas
└── prompts/
    └── classifier.md    # Plantilla en Markdown con las instrucciones de sistema para el LLM
```

---

### Componentes e Implementación Técnica

#### 1. InputClassifier (`classifier.py`)

Es la fachada pública principal. Orquesta el flujo de clasificación inyectando sus dependencias mediante desacoplamiento (DIP).

##### Firma de la clase:
```python
from .models import ClassificationContext, InputAction
from .llm_adapter import BaseLLM
from .prompt_builder import PromptBuilder
from .validator import OutputValidator

class InputClassifier:
    def __init__(
        self,
        llm_adapter: BaseLLM,
        prompt_builder: PromptBuilder = None,
        validator: OutputValidator = None
    ):
        self.llm_adapter = llm_adapter
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.validator = validator or OutputValidator()

    def classify(self, player_input: str, context: ClassificationContext) -> InputAction:
        prompt = self.prompt_builder.build(player_input, context)
        raw_output = self.llm_adapter.generate(prompt)
        validated_action = self.validator.validate(raw_output)
        return validated_action
```

##### Características de la implementación:
- No contiene lógica directa de inferencia de IA ni conoce la librería subyacente.
- Si no se proporcionan `prompt_builder` o `validator`, instancia las versiones por defecto.
- Lanza excepciones derivadas de `InputClassifierError` en caso de fallos en cualquier etapa del proceso.

---

#### 2. BaseLLM y LlamaCppAdapter (`llm_adapter.py`)

Aísla la tecnología del LLM mediante la interfaz abstracta `BaseLLM`.

##### Código de las clases:
```python
import json
from abc import ABC, abstractmethod
from typing import Any
from .exceptions import ModelGenerationError

class BaseLLM(ABC):
    """Interfaz abstracta (DIP) para los adaptadores de LLM."""

    @abstractmethod
    def generate(self, prompt: str) -> dict:
        """Genera una respuesta estructurada (JSON) a partir de un prompt."""
        pass
```

##### Implementación Concreta `LlamaCppAdapter`:
```python
DEFAULT_MODEL_PATH = "C:\\Users\\kanel\\.lmstudio\\models\\lmstudio-community\\gemma-3-4b-it-GGUF\\gemma-3-4b-it-Q4_K_M.gguf"

DEFAULT_MODEL_CONFIG = {
    "n_ctx": 2048,
    "n_gpu_layers": 0,
    "n_threads": 4,
    "temperature": 0.1,
    "max_tokens": 512,
}

class LlamaCppAdapter(BaseLLM):
    def __init__(self, model_path: str = DEFAULT_MODEL_PATH, config: dict[str, Any] = None):
        if llama_cpp is None:
            raise ModelGenerationError("La librería 'llama-cpp-python' no está instalada...")

        self.model_path = model_path
        self.config = config or DEFAULT_MODEL_CONFIG.copy()

        self.llm_params = {
            "n_ctx": self.config.get("n_ctx", 2048),
            "n_gpu_layers": self.config.get("n_gpu_layers", 0),
            "n_threads": self.config.get("n_threads", 4),
        }

        try:
            self.llm = llama_cpp.Llama(
                model_path=self.model_path,
                verbose=False,
                **self.llm_params
            )
        except Exception as e:
            raise ModelGenerationError(f"Error crítico al intentar cargar el modelo: {e}")

    def generate(self, prompt: str) -> dict:
        if not hasattr(self, "llm") or self.llm is None:
            raise ModelGenerationError("El modelo Llama no ha sido inicializado correctamente.")

        temperature = self.config.get("temperature", 0.1)
        max_tokens = self.config.get("max_tokens", 512)

        try:
            response = self.llm.create_chat_completion(
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=temperature,
                max_tokens=max_tokens
            )
            content_text = response["choices"][0]["message"]["content"]
            if not content_text:
                raise ModelGenerationError("El modelo retornó una respuesta de texto vacía.")
            return json.loads(content_text)
        except json.JSONDecodeError as jde:
            raise ModelGenerationError(f"El modelo generó un texto que no es JSON válido: {jde}")
        except Exception as e:
            raise ModelGenerationError(f"Error inesperado durante la inferencia: {e}")
```

---

#### 3. PromptBuilder (`prompt_builder.py`)

Encargado de combinar las plantillas de instrucciones con el contexto y la entrada del jugador.

##### Código:
```python
import os
import json
from .models import ClassificationContext

class PromptBuilder:
    def __init__(self, template_path: str = None):
        if template_path is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            template_path = os.path.join(current_dir, "prompts", "classifier.md")
        self.template_path = template_path
        self._template = None

    def _load_template(self) -> str:
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
        template = self._load_template()
        context_dict = context.model_dump()
        context_json_str = json.dumps(context_dict, indent=2, ensure_ascii=False)

        prompt = template.replace("{{context_json}}", context_json_str)
        prompt = prompt.replace("{{player_input}}", player_input)
        return prompt
```

- Carga por defecto `input_classifier/prompts/classifier.md`.
- Serializa el modelo Pydantic `context` mediante `context.model_dump()`.
- Incorpora un mecanismo de plantilla de reserva (*fallback*) en `_get_fallback_template()`.

---

#### 4. OutputValidator (`validator.py`)

Valida estructuralmente que el diccionario devuelto por el adaptador del LLM sea conforme con la clase Pydantic `InputAction`.

##### Código:
```python
from pydantic import ValidationError
from .models import InputAction
from .exceptions import OutputValidationError

class OutputValidator:
    def validate(self, raw_output: dict) -> InputAction:
        if not isinstance(raw_output, dict):
            raise OutputValidationError(
                f"La salida del adaptador del modelo no es un diccionario Python. Tipo recibido: {type(raw_output).__name__}"
            )

        try:
            return InputAction(**raw_output)
        except ValidationError as ve:
            raise OutputValidationError(
                f"La respuesta estructurada del modelo no coincide con el esquema InputAction esperado.\n"
                f"Detalles de validación de Pydantic:\n{ve}"
            )
```

---

#### 5. Modelos Pydantic (`models.py`)

Define los contratos formales para las entradas y salidas del sistema.

##### Código:
```python
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

class InputAction(BaseModel):
    """Contrato semántico de salida que envuelve la lista cronológica de acciones del jugador."""
    actions: list[ActionDetail] = Field(
        description="Lista de una o más acciones ordenadas cronológicamente que el jugador desea realizar."
    )

    @model_validator(mode="after")
    def validate_min_actions(self) -> "InputAction":
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
```

---

#### 6. Jerarquía de Excepciones (`exceptions.py`)

```python
class InputClassifierError(Exception):
    """Excepción base de todos los errores dentro de InputClassifier."""
    pass

class ModelGenerationError(InputClassifierError):
    """Lanzada cuando el modelo LLM falla al generar una respuesta."""
    pass

class OutputValidationError(InputClassifierError):
    """Lanzada cuando la respuesta generada por el LLM no cumple con el esquema esperado."""
    pass
```

---

### Inversión de Dependencias (DIP) y Diseño Extensible

El módulo aplica el principio de Inversión de Dependencias (DIP) desacoplando la fachada principal `InputClassifier` de cualquier librería o motor de inferencia de IA específico.

```text
               +--------------------+
               |  InputClassifier   |
               +---------+----------+
                         |
                         v
                +-----------------+
                |     BaseLLM     | (Interfaz Abstracta)
                +--------+--------+
                         ^
                         |
      +------------------+------------------+
      |                                     |
+-----+--------------+            +---------+----------+
|  LlamaCppAdapter   |            |  OllamaAdapter /   | (Futuras extensiones)
| (llama-cpp-python) |            |  OpenAIAdapter     |
+--------------------+            +--------------------+
```

De este modo, si en el futuro se desea cambiar la inferencia de `llama-cpp-python` a Ollama, OpenAI o un microservicio propio, basta con crear una nueva subclase de `BaseLLM` e inyectarla en `InputClassifier` sin necesidad de cambiar ninguna otra línea de código.