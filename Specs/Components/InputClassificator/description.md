### InputClassifier
### Responsabilidad

El InputClassifier constituye el primer módulo de la pipeline de procesamiento del mensaje del jugador.

Su responsabilidad consiste exclusivamente en transformar lenguaje natural en una representación semántica estructurada.

No interpreta consecuencias.
No modifica el estado del juego.
No genera narrativa.
No consulta reglas del juego.

Su única salida es un objeto JSON válido que representa fielmente la intención expresada por el jugador.

Este módulo actúa como contrato de comunicación entre el jugador y el resto del motor.

Objetivos

El módulo debe ser capaz de:

identificar la acción principal del jugador;
identificar las entidades mencionadas;
resolver referencias contextuales cuando exista información suficiente;
detectar modificadores presentes en el mensaje;
extraer contenido textual asociado a la acción;
producir un JSON estructurado;
garantizar que dicho JSON cumple el esquema definido.
Responsabilidades

El módulo sí debe

clasificar la intención principal;
identificar objetivos de la acción;
extraer parámetros relevantes;
mantener cualquier información adicional encontrada;
validar la salida mediante un esquema.

El módulo no debe

modificar GameState;
acceder a WorldData;
ejecutar lógica del juego;
decidir si una acción es válida;
generar respuestas narrativas;
inventar información ausente.


El InputClassifier únicamente coordina el proceso.

Componentes
1. InputClassifier
Responsabilidad

Es la fachada pública del módulo.

Orquesta el flujo completo de clasificación.

No contiene lógica de IA.

No conoce cómo funciona el modelo.

No conoce Pydantic.

Su única responsabilidad consiste en coordinar:

preparación del contexto;
llamada al modelo;
validación;
devolución del resultado.
Métodos públicos
class InputClassifier:

    def classify(
        self,
        player_input: str,
        context: ClassificationContext
    ) -> InputAction
Flujo interno
recibe texto

↓

construye prompt

↓

LLMAdapter.generate()

↓

OutputValidator.validate()

↓

InputAction
Responsabilidad exacta

Nunca interpreta.

Nunca modifica resultados.

Nunca altera el JSON recibido.

Su única función es coordinar.

2. LLMAdapter
Responsabilidad

Encapsular completamente el modelo LLM.

El resto del sistema nunca interactúa directamente con llama.cpp.

Esto permite sustituir el modelo sin afectar al resto del proyecto.

Hoy puede utilizar:

llama-cpp-python

Mañana podría utilizar:

Ollama
OpenAI
Mistral
vLLM
cualquier otro backend

sin modificar InputClassifier.

Métodos
class LLMAdapter:

    def generate(
        self,
        prompt: str
    ) -> dict
Responsabilidades

Construir la llamada al modelo.

Aplicar parámetros:

temperatura
stop tokens
max tokens
formato JSON

Recibir la respuesta.

Convertirla a diccionario.

Nada más.

No valida.

No interpreta.

No corrige.

3. OutputValidator
Responsabilidad

Garantizar que la salida cumple exactamente el contrato esperado.

Este componente utiliza Pydantic.

Métodos
class OutputValidator:

    def validate(
        self,
        raw_json: dict
    ) -> InputAction
Responsabilidades

Comprobar:

JSON válido
tipos correctos
campos obligatorios
listas
atributos opcionales

Si la validación falla:

lanza excepción
o devuelve un error controlado

Nunca intenta "adivinar" información.

Objeto InputAction

Representa el contrato entre InputClassifier y el resto del motor.

Una vez creado, todos los módulos posteriores trabajarán exclusivamente con este objeto.

class InputAction(BaseModel):

    action: str

    targets: list[str]

    content: str | None

    attributes: dict[str, Any]
Campos obligatorios

Siempre deben existir.

{
    "action": "...",
    "targets": [],
    "content": null,
    "attributes": {}
}

Incluso si están vacíos.

action

Acción principal detectada.

Ejemplos

MOVE

TALK

LOOK

OPEN

USE

WAIT

EXPLAIN

targets

Lista de entidades implicadas.

Puede contener

npc_blacksmith

npc_guard

item_sword

door_main

location_market

Si no existe ninguna entidad:

[]
content

Texto asociado a la acción.

Ejemplo

Le pregunto quién gobierna la ciudad.

↓

"¿Quién gobierna la ciudad?"

Si no existe:

null
attributes

Diccionario completamente abierto.

Nunca posee un esquema fijo.

Puede contener cualquier información relevante encontrada.

Ejemplos

{
    "speed":"slow",
    "direction":"north",
    "emotion":"angry",
    "weapon_state":"drawn",
    "body_part":"head",
    "distance":"close"
}

También puede estar vacío.

{}
Contexto de entrada

El clasificador recibe únicamente el contexto mínimo necesario.

class ClassificationContext:

    visible_entities

    previous_references

    active_conversation

    player_location

No contiene GameState completo.

No contiene reglas.

No contiene lógica.

Su única finalidad consiste en resolver referencias como:

él

ella

esa espada

allí

la puerta

aquello
Flujo completo
Jugador

↓

"Le doy la espada."

↓

InputClassifier

↓

LLMAdapter

↓

{
    action:"GIVE",
    targets:["npc_roderick"],
    content:null,
    attributes:{
        item:"sword"
    }
}

↓

OutputValidator

↓

InputAction

↓

ActionResolver
Manejo de errores

El módulo debe distinguir claramente entre errores del modelo y errores de validación.

Error del modelo

Ejemplos:

el modelo no responde;
timeout;
respuesta vacía;
formato ilegible.

Se considera un error de generación y debe propagarse para que la capa superior decida cómo actuar (reintentar, registrar el fallo, etc.).

Error de validación

Ejemplos:

falta action;
targets no es una lista;
attributes tiene un tipo incorrecto.

La salida debe rechazarse mediante una excepción específica, garantizando que ningún módulo posterior reciba datos inconsistentes.

Principios de diseño

El diseño del módulo debe seguir los siguientes principios:

Responsabilidad única (SRP): cada clase tiene una única responsabilidad bien definida.
Desacoplamiento: el resto del motor no conoce el proveedor del LLM ni la implementación del validador.
Contrato estable: InputAction es la única interfaz pública del módulo.
Extensibilidad: es posible cambiar el modelo, el prompt o el sistema de validación sin modificar el resto de la pipeline.
Determinismo estructural: aunque la interpretación semántica dependa del LLM, la estructura de salida siempre será la misma.
Fail-fast: cualquier salida inválida se detecta y rechaza antes de que alcance los módulos de resolución de acciones o narrativa.

Con esta arquitectura, el InputClassifier queda definido como un componente de clasificación semántica puro, fácilmente sustituible y mantenible, que establece un contrato sólido entre la entrada del jugador y el resto del motor del juego.