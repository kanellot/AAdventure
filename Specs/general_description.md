# Especificación de Arquitectura (MVP)

## Motor de Narrativa IA para Aventuras de Texto

## 1. Objetivo

El objetivo del proyecto es desarrollar un motor de aventuras narrativas donde un Modelo de Lenguaje (LLM) actúe como **Dungeon Master**, guiando al jugador a través de un mundo previamente definido.

El jugador interactúa únicamente mediante texto libre y el sistema es responsable de mantener la coherencia narrativa, el estado del mundo y la continuidad de la historia.

Desde el punto de vista arquitectónico, el LLM **no es el motor del juego**, sino únicamente el generador de narrativa. Toda la información relevante del mundo y de la partida será gestionada por componentes deterministas independientes.

La arquitectura debe ser sencilla en su primera versión (MVP), permitiendo evolucionar posteriormente hacia sistemas más complejos sin necesidad de rediseñar el núcleo del proyecto.

---

# 2. Objetivos de diseño

* Arquitectura modular.
* Separación estricta entre conocimiento, estado y narración.
* Minimizar la responsabilidad del LLM.
* Facilitar la sustitución del modelo de IA sin modificar el resto del sistema.
* Favorecer la extensibilidad del proyecto.
* Mantener una implementación sencilla para el primer prototipo.

---

# 3. Tecnologías

## Lenguaje

Python 3.12+

## Backend IA

* llama-cpp-python
* Modelos GGUF ejecutados localmente

## Sistema Operativo

El proyecto deberá funcionar de forma idéntica en:

* Windows
* Linux

No deberá depender de APIs exclusivas del sistema operativo.

## Almacenamiento

Para el MVP se priorizarán tecnologías ligeras:

* JSON para contenido estático.
* SQLite para datos dinámicos.
* Sin necesidad de servidor externo.

Esto permitirá distribuir el proyecto como una aplicación completamente autocontenida.

---

# 4. Arquitectura general

```
Jugador
    │
    ▼
EntityResolver
    │
    ▼
ContextBuilder
    │
    ├────────────┬─────────────┬─────────────┐
    ▼            ▼             ▼
WorldData   GameState   StoryMemory
    │
    ▼
ModelManager
    │
    ▼
OutcomeProcessor
    │
    ▼
EventBus
    │
 ┌──┴───────────────┐
 ▼                  ▼
GameState     StoryMemory
```

---

# 5. Componentes

5.1 InputClassificator
### Responsabilidad

Interpretar el mensaje del jugador utilizando un LLM y traducir el lenguaje natural a una representación semántica estructurada que pueda ser procesada por el resto del sistema.

Este módulo no toma decisiones sobre el juego, no modifica el estado y no genera narrativa. Su única responsabilidad es comprender la intención del jugador y expresar dicha intención mediante una estructura de datos normalizada.

La salida del módulo constituye el contrato de comunicación entre el jugador y el motor del juego.

Objetivos

El módulo debe ser capaz de:

Identificar la intención principal del jugador.
Detectar las entidades mencionadas.
Resolver referencias contextuales ("él", "ella", "allí", "esa espada", etc.).
Extraer modificadores y detalles presentes en el texto.
Generar una representación estructurada sin interpretar las consecuencias de la acción.
Arquitectura

El EntityResolver estará implementado mediante un LLM de propósito específico.

Su función será exclusivamente la traducción semántica del texto del jugador.

No tendrá acceso directo a:

GameState
WorldData
StoryMemory

Únicamente recibirá el mensaje del jugador y el contexto mínimo necesario para resolver referencias contextuales cuando sea requerido.

Esto permite utilizar modelos pequeños, rápidos y especializados en comprensión del lenguaje.

Estructura de salida

La respuesta generada deberá seguir una estructura parcialmente fija.

Existirá un conjunto reducido de campos obligatorios y un bloque abierto de atributos donde el modelo podrá incluir cualquier información adicional detectada en el mensaje.

Campos obligatorios
action: acción principal detectada.
targets: lista de entidades implicadas en la acción.
content: contenido textual asociado a la acción (si existe).
Campos libres

El modelo podrá añadir cualquier número de atributos adicionales dentro de un bloque attributes.

Estos atributos no estarán predefinidos y podrán variar según el contexto del mensaje.

Ejemplos:

velocidad
actitud
emoción
dirección
intensidad
postura
objetivo
parte del cuerpo
forma de ejecutar la acción
cualquier otro matiz presente en el lenguaje del jugador

El resto del sistema deberá tratar este bloque como información opcional.

Ejemplos
Conversación

Entrada:

"Hablo con el herrero."

Salida:

{
    "action": "TALK",
    "targets": [
        "npc_blacksmith"
    ],
    "content": null,
    "attributes": {}
}
Conversación con contenido

Entrada:

"Le pregunto si conoce algún camino seguro hacia las montañas."

Salida:

{
    "action": "TALK",
    "targets": [
        "npc_old_man"
    ],
    "content": "¿Conoce algún camino seguro hacia las montañas?",
    "attributes": {
        "topic": "safe_route"
    }
}
Acción compleja

Entrada:

"Me acerco lentamente al anciano con la espada desenfundada."

Salida:

{
    "action": "MOVE",
    "targets": [
        "npc_old_man"
    ],
    "content": null,
    "attributes": {
        "speed": "slow",
        "weapon_state": "drawn"
    }
}
Referencia contextual

Entrada:

"Le doy la espada."

Salida:

{
    "action": "GIVE",
    "targets": [
        "npc_roderick"
    ],
    "content": null,
    "attributes": {
        "item": "sword"
    }
}
Restricciones

El EntityResolver no debe:

modificar el estado del juego;
decidir si una acción es válida;
inventar información que no aparezca en el mensaje del jugador;
consultar directamente la lógica del juego;
generar texto narrativo.

Su única función es producir una representación semántica fiel de la intención expresada por el jugador.

Implementación propuesta
Lenguaje: Python.
Tecnología: llama-cpp-python.
Modelo: LLM local especializado en comprensión del lenguaje.
Salida: JSON estructurado siguiendo un esquema definido.
Persistencia: No requiere almacenamiento propio.

La separación entre este módulo y el narrador permitirá sustituir o mejorar el modelo encargado de interpretar acciones sin afectar al resto de la arquitectura.

## 5.2 WorldData

### Responsabilidad

Contiene toda la información estática del universo.

Incluye:

* localizaciones
* NPC
* criaturas
* objetos
* facciones
* historia
* reglas
* cultura
* magia
* eventos predefinidos

Durante una partida se considera de solo lectura.

En un futuro podrá añadirse un módulo WorldPatch para aplicar modificaciones permanentes al mundo.

### Implementación propuesta

Estructura de carpetas.

```
world/

    locations/

    npcs/

    creatures/

    items/

    factions/

    lore/
```

Cada entidad será un archivo JSON independiente.

Ejemplo:

```
world/npcs/blacksmith.json
```

Ventajas:

* Muy fácil de editar.
* Compatible con Git.
* Fácil de ampliar.
* No requiere base de datos.

---

## 5.3 GameState

### Responsabilidad

Representa el estado actual de la partida.

Debe almacenar únicamente información dinámica.

Ejemplos:

Jugador

* posición
* salud
* maná
* inventario
* dinero
* reputación
* misiones activas

NPC

* localización
* estado
* confianza
* hostilidad
* vivo/muerto

Mundo

* puertas abiertas
* cofres abiertos
* clima
* fecha
* hora
* eventos activos

No almacena narrativa.

Solo estado.

### Implementación propuesta

SQLite.

Ventajas:

* ACID.
* Muy rápido.
* Sin servidor.
* Multiplataforma.
* Fácil de consultar desde Python.

---

## 5.4 StoryMemory

### Responsabilidad

Registrar la historia que se va construyendo durante la partida.

No guarda conversaciones completas.

Guarda eventos estructurados.

Ejemplo:

```
Evento

Jugador acepta la misión del rey.

Participantes

- jugador
- rey

Lugar

castillo

Consecuencia

Quest iniciada
```

Esto permitirá posteriormente realizar búsquedas, resúmenes o recuperación semántica.

### Implementación propuesta

SQLite.

Tabla principal:

* eventos
* participantes
* localización
* timestamp
* importancia
* resumen

En futuras versiones podrán añadirse embeddings sobre estos registros.

---

## 5.5 ContextBuilder

### Responsabilidad

Es el núcleo de la inteligencia del sistema.

Construye el contexto que recibirá el modelo.

Proceso:

1. Recibir la intención detectada.
2. Consultar GameState.
3. Consultar WorldData.
4. Consultar StoryMemory.
5. Seleccionar únicamente la información relevante.
6. Construir el prompt final.

En futuras versiones será el lugar donde incorporar:

* búsqueda semántica
* embeddings
* grafos
* filtros
* re-ranking
* resúmenes automáticos

El resto del sistema no deberá conocer cómo se recupera la información.

### Implementación propuesta

Módulo Python.

Sin almacenamiento propio.

---

## 5.6 ModelManager

### Responsabilidad

Únicamente ejecutar el modelo.

Entrada:

Prompt.

Salida:

Respuesta generada.

No debe conocer:

* GameState
* StoryMemory
* WorldData
* herramientas
* eventos

Debe ser un wrapper independiente del proveedor.

Esto permitirá sustituir fácilmente llama.cpp por cualquier otro backend.

### Implementación propuesta

Python.

Backend inicial:

llama-cpp-python.

Debe diseñarse mediante una interfaz para permitir futuros backends:

* Ollama
* OpenAI
* Anthropic
* vLLM

---

## 5.7 OutcomeProcessor

### Responsabilidad

Interpretar las consecuencias de la respuesta generada.

No procesa únicamente texto.

Procesa cambios en el estado del mundo.

Ejemplos:

* mover jugador
* modificar inventario
* iniciar misión
* finalizar misión
* abrir puerta
* cambiar clima
* cambiar relaciones entre NPC

Este componente genera eventos.

No modifica directamente el resto de módulos.

### Implementación propuesta

Módulo Python.

---

## 5.8 EventBus

### Responsabilidad

Desacoplar la comunicación entre componentes.

El OutcomeProcessor publica eventos.

Los distintos módulos reaccionan de forma independiente.

Ejemplos:

```
DoorOpened

QuestCompleted

NPCDied

ConversationStarted

ItemObtained
```

GameState escucha:

```
DoorOpened

↓

Actualizar puerta
```

StoryMemory escucha:

```
ConversationStarted

↓

Guardar evento
```

Este diseño evita dependencias directas entre módulos.

### Implementación propuesta

Para el MVP no será necesario un sistema de mensajería.

Será suficiente con un EventBus implementado en memoria mediante el patrón Observer (publish/subscribe).

En futuras versiones podrá sustituirse por un sistema distribuido sin modificar el resto de componentes.

---

# 6. Evolución prevista

La arquitectura está diseñada para crecer de forma incremental.

Algunas posibles ampliaciones:

* Sistema RAG para StoryMemory.
* Base de datos vectorial para recuperación semántica.
* Grafo de relaciones entre entidades.
* Quest Engine independiente.
* Sistema de combate.
* Sistema económico.
* Planificación autónoma de NPC.
* Simulación del paso del tiempo.
* Múltiples jugadores.
* Herramientas de edición del mundo.

La incorporación de estos módulos no debería requerir modificaciones significativas en la arquitectura principal.

---

# 7. Filosofía del proyecto

La IA debe centrarse exclusivamente en generar una narración coherente y diálogos naturales.

Toda la lógica del juego, el estado del mundo y la persistencia de la información deben mantenerse en componentes deterministas y verificables.

Esta separación proporciona un sistema más robusto, reproducible, fácil de depurar y preparado para evolucionar hacia motores narrativos mucho más complejos sin depender del comportamiento interno del modelo de lenguaje.
