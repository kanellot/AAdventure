input_classifier/
│
├── classifier.py          # Fachada pública
├── prompt_builder.py      # Construcción del prompt
├── llm_adapter.py         # Comunicación con el modelo
├── validator.py           # Validación Pydantic
├── models.py              # Modelos de entrada/salida
├── exceptions.py          # Excepciones propias
└── prompts/
    └── classifier.md

Con esto cada clase tiene una única responsabilidad.

Componentes
1. InputClassifier
Responsabilidad

Es la fachada pública del módulo y el único punto de entrada utilizado por el resto del motor.

Su única función es coordinar el flujo completo de clasificación.

No contiene lógica de IA.

No conoce el funcionamiento del modelo.

No conoce Pydantic.

No construye manualmente prompts.

No interpreta resultados.

Dependencias
InputClassifier
    ├── PromptBuilder
    ├── LLMAdapter
    └── OutputValidator
Métodos públicos
class InputClassifier:

    def classify(
        self,
        player_input: str,
        context: ClassificationContext
    ) -> InputAction:
        ...
Flujo
player_input

↓

PromptBuilder.build()

↓

LLMAdapter.generate()

↓

OutputValidator.validate()

↓

InputAction
2. PromptBuilder
Responsabilidad

Construir el prompt enviado al modelo.

Toda la ingeniería de prompts queda aislada en esta clase.

Esto permite modificar el prompt sin afectar al resto del sistema.

Métodos
class PromptBuilder:

    def build(
        self,
        player_input: str,
        context: ClassificationContext
    ) -> str:
        ...
Responsabilidades
insertar el mensaje del jugador;
incorporar el contexto mínimo;
incluir las instrucciones del sistema;
definir el formato JSON esperado.

No realiza llamadas al modelo.

No interpreta resultados.

3. LLMAdapter
Responsabilidad

Encapsular completamente el backend del modelo.

El resto del sistema nunca interactúa directamente con llama-cpp-python.

En el futuro podrá sustituirse por cualquier otro proveedor sin modificar el resto del código.

Métodos
class LLMAdapter:

    def generate(
        self,
        prompt: str
    ) -> dict:
        ...
Responsabilidades
cargar el modelo;
ejecutar la inferencia;
configurar temperatura;
configurar número máximo de tokens;
configurar formato JSON;
devolver un diccionario Python.

No valida.

No corrige.

No interpreta.

4. OutputValidator
Responsabilidad

Validar que la salida del modelo cumple exactamente el contrato definido por el módulo.

Utiliza Pydantic como mecanismo de validación.

Métodos
class OutputValidator:

    def validate(
        self,
        raw_output: dict
    ) -> InputAction:
        ...
Responsabilidades

Comprobar:

JSON válido;
existencia de los campos obligatorios;
tipos correctos;
listas válidas;
diccionario de atributos.

Si la validación falla, lanzará una excepción específica.

No modifica la información.

No intenta completar campos faltantes.

5. InputAction
Responsabilidad

Representar el contrato de salida del módulo.

Todos los módulos posteriores consumirán exclusivamente este objeto.

class InputAction(BaseModel):

    action: str

    targets: list[str] = []

    content: str | None = None

    attributes: dict[str, Any] = {}
6. ClassificationContext
Responsabilidad

Proporcionar únicamente el contexto mínimo necesario para resolver referencias lingüísticas.

No representa el estado del juego.

No contiene reglas.

No contiene información narrativa.

class ClassificationContext(BaseModel):

    visible_entities: list[str]

    previous_references: dict[str, str]

    active_conversation: str | None

    player_location: str | None
7. Excepciones

Definir excepciones propias facilita el tratamiento de errores en la pipeline y evita depender de excepciones genéricas.

class InputClassifierError(Exception):
    """Excepción base del módulo."""


class ModelGenerationError(InputClassifierError):
    """Error durante la generación del LLM."""


class OutputValidationError(InputClassifierError):
    """La salida del modelo no cumple el esquema esperado."""
Una mejora adicional: definir una interfaz para el modelo

Si desde el principio quieres que el módulo sea independiente del backend del LLM, incluso evitaría que InputClassifier dependiera directamente de LLMAdapter. En su lugar introduciría una abstracción:

from abc import ABC, abstractmethod

class BaseLLM(ABC):

    @abstractmethod
    def generate(self, prompt: str) -> dict:
        """Genera una respuesta estructurada a partir del prompt."""
        pass

Y la implementación concreta:

class LlamaCppAdapter(BaseLLM):
    ...

De esta forma, InputClassifier solo conoce BaseLLM, no llama-cpp-python. Esto sigue el principio de inversión de dependencias (DIP) y hace que el módulo sea completamente agnóstico al proveedor del modelo. Si en el futuro decides cambiar a Ollama, OpenAI, Mistral o cualquier otro backend, solo tendrás que implementar un nuevo adaptador sin modificar una sola línea del clasificador. Para un motor de RPG basado en LLM, esta pequeña abstracción suele compensar desde el principio porque el modelo es uno de los componentes con más probabilidades de cambiar durante la vida del proyecto.