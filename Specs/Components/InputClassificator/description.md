### InputClassifier

### Responsabilidad

El `InputClassifier` constituye el primer módulo de la pipeline de procesamiento del mensaje del jugador.

Su responsabilidad consiste exclusivamente en transformar lenguaje natural en una representación semántica estructurada.

- No interpreta consecuencias.
- No modifica el estado del juego.
- No genera narrativa.
- No consulta reglas del juego.

Su única salida es un objeto estructurado `InputAction` (y su correspondiente representación JSON válida) que representa fielmente la intención o secuencia de intenciones expresadas por el jugador.

Este módulo actúa como contrato de comunicación entre el jugador y el resto del motor.

---

### Objetivos

El módulo debe ser capaz de:

1. Identificar una o más acciones principales del jugador ordenadas cronológicamente;
2. Identificar las entidades mencionadas (`targets`);
3. Resolver referencias contextuales cuando exista información suficiente (pronombres, descripciones cortas);
4. Detectar modificadores y atributos presentes en el mensaje (`attributes`);
5. Producir una lista estructurada de acciones (`actions`);
6. Garantizar que dicha salida cumple estrictamente el esquema definido mediante Pydantic.

---

### Responsabilidades

#### El módulo sí debe:
- Clasificar la intención o secuencia de intenciones principales;
- Identificar objetivos de cada acción;
- Extraer parámetros y matices relevantes (dirección, sigilo, velocidad, postura, tema de conversación, etc.);
- Mantener cualquier información adicional encontrada en un diccionario abierto de atributos;
- Validar la salida mediante un esquema estructurado estricto.

#### El módulo no debe:
- Modificar `GameState`;
- Acceder a `WorldData`;
- Ejecutar lógica del juego;
- Decidir si una acción es válida dentro de las reglas;
- Generar respuestas narrativas;
- Inventar información ausente en la entrada o contexto.

El `InputClassifier` únicamente coordina el proceso de clasificación semántica.

---

### Componentes principales

#### 1. InputClassifier (Fachada Pública)
- **Responsabilidad**: Es la fachada pública del módulo y el único punto de entrada utilizado por el motor. Orquesta el flujo completo de clasificación mediante inyección de dependencias (`BaseLLM`, `PromptBuilder`, `OutputValidator`).
- **Métodos públicos**:
  ```python
  class InputClassifier:
      def __init__(
          self,
          llm_adapter: BaseLLM,
          prompt_builder: PromptBuilder = None,
          validator: OutputValidator = None
      ): ...

      def classify(
          self,
          player_input: str,
          context: ClassificationContext
      ) -> InputAction: ...
  ```

- **Flujo interno**:
  ```text
  recibe player_input + context
          ↓
  PromptBuilder.build()
          ↓
  BaseLLM.generate() (ej. LlamaCppAdapter)
          ↓
  OutputValidator.validate()
          ↓
  devuelve InputAction
  ```

#### 2. BaseLLM y LlamaCppAdapter
- **Responsabilidad**: Encapsular completamente el backend del modelo LLM mediante Inversión de Dependencias (DIP). El resto del sistema interactúa únicamente con la interfaz abstracta `BaseLLM`.
- **Implementación actual**: `LlamaCppAdapter` utiliza `llama-cpp-python` para ejecutar modelos locales formateados en GGUF (por defecto Gemma 3 4B GGUF), forzando una respuesta en formato de objeto JSON estructurado (`response_format={"type": "json_object"}`).
- **Método**:
  ```python
  class BaseLLM(ABC):
      @abstractmethod
      def generate(self, prompt: str) -> dict: ...
  ```

#### 3. PromptBuilder
- **Responsabilidad**: Construir el prompt completo que se envía al modelo integrando las instrucciones de sistema desde una plantilla (`prompts/classifier.md`), el contexto lingüístico serializado y el mensaje del jugador. Posee una plantilla de respaldo (*fallback*) integrada.

#### 4. OutputValidator
- **Responsabilidad**: Garantizar que el diccionario retornado por el adaptador LLM cumple exactamente con el esquema Pydantic `InputAction`. Lanza una excepción `OutputValidationError` en caso de discrepancias estructurales.

---

### Estructura de Salida y Contrato de Datos

El contrato entre `InputClassifier` y el resto del motor se define mediante los modelos Pydantic `InputAction` y `ActionDetail`.

#### 1. Objeto `ActionDetail`
Representa los detalles semánticos de una única acción identificada:
```python
class ActionDetail(BaseModel):
    action: str
    targets: list[str] = []
    attributes: dict[str, Any] = {}
```

- **`action`**: Nombre de la acción principal en mayúsculas (ej. `MOVE`, `TALK`, `LOOK`, `OPEN`, `USE`, `TAKE`, `GIVE`, `ATTACK`, `WAIT`, `EXPLAIN`).
- **`targets`**: Lista de IDs de entidades involucradas (ej. `["npc_blacksmith"]`, `["item_sword"]`). Si no hay ninguna entidad, devuelve lista vacía `[]`.
- **`attributes`**: Diccionario dinámico con matices u opciones extraídas (ej. `{"stealth": true}`, `{"direction": "north"}`, `{"topic": "safe_route"}`).

#### 2. Objeto `InputAction`
Representa la salida del módulo y envuelve la lista cronológica de acciones:
```python
class InputAction(BaseModel):
    actions: list[ActionDetail]
```
Garantiza mediante validación Pydantic (`@model_validator`) que la lista `actions` contenga al menos un elemento.

##### Representación JSON esperada:
```json
{
  "actions": [
    {
      "action": "MOVE",
      "targets": ["bld_tavern"],
      "attributes": {
        "stealth": true
      }
    },
    {
      "action": "LOOK",
      "targets": ["bld_tavern"],
      "attributes": {}
    }
  ]
}
```

---

### Contexto de Entrada (`ClassificationContext`)

El clasificador recibe únicamente el contexto lingüístico mínimo necesario para resolver referencias y entidades en la partida:

```python
class ClassificationContext(BaseModel):
    visible_entities: list[str] = []
    previous_references: dict[str, str] = {}
    active_conversation: str | None = None
    player_location: str | None = None
```

- `visible_entities`: Entidades presentes a la vista del jugador.
- `previous_references`: Mapeo reciente de pronombres o sustantivos a IDs de entidades.
- `active_conversation`: ID del NPC activo si hay una conversación en curso.
- `player_location`: ID de la localización actual.

---

### Flujo Completo de Ejemplo

**Entrada del Jugador**: `"Voy sigilosamente hacia la taberna y miro adentro."`

```text
Jugador
   ↓
"Voy sigilosamente hacia la taberna y miro adentro."
   ↓
InputClassifier.classify(player_input, context)
   ↓
PromptBuilder.build() -> genera el prompt con classifier.md
   ↓
LlamaCppAdapter.generate() -> LLM local llama-cpp
   ↓
{
  "actions": [
    {
      "action": "MOVE",
      "targets": ["bld_tavern"],
      "attributes": {"stealth": true}
    },
    {
      "action": "LOOK",
      "targets": ["bld_tavern"],
      "attributes": {}
    }
  ]
}
   ↓
OutputValidator.validate() -> valida con Pydantic
   ↓
InputAction (Objeto Python validado)
   ↓
Siguientes componentes del motor (ActionResolver / Narrative Engine)
```

---

### Manejo de Errores

El módulo define una jerarquía de excepciones personalizadas derivadas de `InputClassifierError`:

- **`InputClassifierError`**: Excepción base del módulo.
- **`ModelGenerationError`**: Se produce durante la inicialización del modelo, la inferencia de `llama-cpp-python` o si el LLM retoma una salida ilegible o texto que no es JSON válido.
- **`OutputValidationError`**: Se produce cuando el JSON retornado por el modelo no coincide con el esquema Pydantic `InputAction` (ej. falta la clave `"actions"` o sus elementos no son válidos).

---

### Principios de Diseño

1. **Responsabilidad Única (SRP)**: Cada componente (`InputClassifier`, `PromptBuilder`, `BaseLLM`, `OutputValidator`) tiene un cometido específico y aislado.
2. **Inversión de Dependencias (DIP)**: `InputClassifier` no depende de una librería de LLM específica, sino de la abstracción `BaseLLM`.
3. **Contrato Estructurado Estable**: `InputAction` es la única estructura pública retornada hacia el resto del motor.
4. **Extensibilidad**: Permite reemplazar el proveedor de LLM (ej. de llama-cpp a Ollama o OpenAI) o cambiar el prompt sin modificar la lógica del clasificador ni del resto del motor.
5. **Soporte Secuencial Multi-Acción**: Permite traducir entradas compuestas en secuencias cronológicas de acciones.
6. **Fail-Fast**: Toda respuesta que no cumpla con el formato es rechazada antes de propagarse en la pipeline del juego.