# AAdventure: Plataforma de Aventuras Narrativas con Inteligencia Artificial

AAdventure es una plataforma de juegos de rol y aventuras interactivas basada en texto. Su objetivo principal es ofrecer una experiencia similar a tener un director de juego (Dungeon Master) interactivo impulsado por Inteligencia Artificial que funciona de manera 100% local, sin necesidad de servidores externos ni suscripciones a servicios en la nube.

El juego combina la libertad creativa de los modelos de lenguaje con la solidez de un motor de reglas tradicional: mientras la Inteligencia Artificial se encarga de narrar y dar vida a los personajes, el motor gestiona el mapa, las distancias, el paso del tiempo, el inventario y las relaciones entre personajes.

---

## 1. Modulos del Proyecto

El proyecto se divide en cuatro areas principales pensadas para cubrir todo el ciclo de vida de una aventura:

### Editor de Historias (`editor`)
Una herramienta visual para crear mundos, historias y personajes sin necesidad de tocar codigo o archivos de datos a mano:
- Creacion de mapas con regiones, ciudades y lugares detallados.
- Conexion de caminos indicando distancias y dificultades del terreno.
- Creacion de personajes no jugadores (NPCs) con personalidad, ocupacion, afinidad inicial y lo que les gusta o disgusta.
- Definicion de eventos de historia y secretos que se activan solo bajo ciertas situaciones.
- Empaquetado de la aventura completa en un unico archivo facil de compartir (`.aad`).

### Motor de Juego (`engines`)
Es el cerebro central que controla todo lo que ocurre durante la partida:
- Aplica las reglas del mundo: calcula el tiempo que tardas en viajar, gestiona el oro y actualiza el estado de las misiones.
- Sistema de niebla de exploracion: el jugador solo conoce los lugares que ha explorado o que tiene a la vista, y los personajes permanecen ocultos hasta que se visita su ubicacion.
- Memoria y activacion de secretos (RAG): analiza lo que dice o hace el jugador y, si menciona un tema relevante, recupera la informacion secreta adecuada para que el narrador la use en su respuesta.
- Conexion con la Inteligencia Artificial: envia el contexto del turno al modelo de lenguaje local y procesa su respuesta de forma segura.
- Arquitectura desacoplada: el motor no depende de ninguna interfaz grafica, lo que permite que sea utilizado tanto por el depurador de escritorio como por una futura aplicacion movil.

### Depurador de Juego (`game_debugger`)
Una aplicacion grafica de escritorio pensada para probar, calibrar y disfrutar de las aventuras durante su desarrollo:
- Permite jugar la partida escribiendo mensajes o usando botones de accion directa (Moverse, Mirar, Hablar).
- Muestra en tiempo real como piensa el motor: que secretos se activaron con tu frase, que instrucciones se enviaron a la IA y como cambio el estado del mundo tras tu accion.
- Ofrece mapas de exploracion y fichas del estado actual del jugador y los personajes.

### Futura Aplicacion Android (Uso Local)
El destino natural del proyecto para los jugadores finales:
- Una aplicacion para telefonos moviles disenada para jugar sin conexion a internet.
- Utiliza modelos de inteligencia artificial optimizados para ejecutarse directamente en el chip del dispositivo movil.
- Interfaz conversacional adaptada a pantallas tactiles que aprovecha la independencia del motor de juego para ofrecer la misma experiencia que en el ordenador.

---

## 2. Filosofia: Como Funciona el Juego

Muchos juegos basados en inteligencia artificial sufren de inconsistencias o inventan datos que rompen la historia (alucinaciones). AAdventure resuelve este problema dividiendo el trabajo de forma clara:

1. **El motor manda sobre las reglas**:
   Si intentas viajar a un lugar que esta a 5 kilometros, el motor calcula el tiempo real que tardas caminando, comprueba si el camino esta despejado y te traslada al destino. La IA no decide si puedes o no viajar; solo se encarga de narrar tu viaje de forma inmersiva con los datos que le proporciona el motor.

2. **Memoria selectiva mediante antenas**:
   Para evitar saturar a la IA con todo el texto de la historia a la vez, cada evento o secreto tiene asociadas varias frases de activacion ("antenas"). Si el jugador escribe algo parecido a esa intencion (por ejemplo, preguntar por un rumor o un objeto perdido), el sistema detecta la coincidencia semantica y le entrega a la IA exactamente la informacion que necesita para ese turno.

3. **Relacion viva con los personajes**:
   Los personajes tienen un nivel de afinidad que cambia segun como los trates. Si hablas de temas que les gustan o cumples sus peticiones, su afinidad aumentara y desbloquearan nuevos secretos o informacion. Si eres hostil, su trato cambiara.

4. **Separacion total entre motor y pantalla**:
   Toda la informacion que la pantalla necesita (mapa visible, oro, tiempo, estado del personaje) se entrega en paquetes de datos cerrados y seguros. De este modo, la interfaz grafica solo se encarga de pintar bonito lo que el motor decide, facilitando crear interfaces nuevas (como la app de Android) sin tocar una sola linea de las reglas.

---

## 3. El Depurador de Juego (`game_debugger`)

El depurador te permite vivir la aventura y ver simultaneamente los engranajes internos del juego. Se organiza en dos columnas principales:

### Panel de Juego y Control (Columna Izquierda)
- **Pestana Juego**: Es la sala de juego principal. Contiene el historial de conversacion en estilo pergamino, botones para acciones directas (MOVE para viajar, LOOK para inspeccionar detalles y TALK para conversar), un selector de objetivos y una insignia que te muestra el nivel de afinidad actual con el personaje con el que estas hablando.
- **Pestana RAG**: Muestra que secretos o eventos escucho el sistema tras tu mensaje, que puntuacion de coincidencia obtuvo cada frase y cual fue la instruccion inyectada al narrador.
- **Pestana Prompt**: Te permite inspeccionar el texto exacto que se le envio a la inteligencia artificial en ese turno, incluyendo la ambientacion y las reglas de conducta.
- **Pestana Result**: Desglosa la respuesta devuelta: la narracion en si, los cambios en el juego (si ganaste oro o si cambio la afinidad) y los datos tecnicos devueltos por el modelo.

### Panel de Mapa e Inspeccion (Columna Derecha)
- **Pestana Navigation**: Muestra el mapa desde la perspectiva del jugador con niebla de exploracion. Los lugares visitados y los personajes que ya conoces aparecen en azul, mientras que los caminos colindantes aun sin explorar se muestran accesibles para moverte a ellos. Al pulsar sobre cualquier lugar o personaje, se selecciona automaticamente como objetivo.
- **Pestana Entities**: Muestra el mapa completo sin niebla para que el creador pueda comprobar todas las zonas del mundo.
- **Pestana Game State**: Muestra en tiempo real la ficha completa del personaje: oro, inventario, misiones activas, lugar donde se encuentra y el estado de la conversacion activa.

---

## 4. El Editor de Historias (`editor`)

El editor permite construir mundos interactivos a traves de una interfaz grafica intuitiva:

- **Ciudades y Lugares**: Define el nombre y la descripcion que recibira el jugador al llegar.
- **Caminos y Conexiones**: Conecta lugares indicando la direccion (Norte, Sur, etc.), la distancia en metros y si se trata de un camino de tierra, bosque o sendero pedregoso.
- **Personajes**: Dales un nombre, descripcion, ocupacion y define sus motivaciones para que la IA sepa que cosas le agradan o le molestan durante la conversacion.
- **Bloques de Lore y Secretos**: Anade eventos de historia, directivas de comportamiento y frases gatillo que la IA recordara cuando el jugador toque esos temas.
- **Compilacion**: Guarda tu aventura en un unico paquete `.aad` listo para abrir y jugar.

---

## 5. Capturas de Pantalla

A continuacion se muestran algunas pantallas del entorno de desarrollo y juego:

#### Editor de Aventuras: Gestion de Lugares y Mundo
![Editor de Aventuras](Docs/screenshot.17.jpg)

#### Diseno de Historia y Reglas
![Diseno de Historia](Docs/screenshot.18.jpg)

#### Vista de Prompt e Inspeccion de Inteligencia Artificial
![Inspeccion de Prompt](Docs/screenshot.19.jpg)

---

## 6. Estado del Proyecto (WIP)

Este proyecto se encuentra actualmente en fase activa de desarrollo (Work In Progress).

Aspectos importantes a tener en cuenta:
- Los archivos con los datos de las aventuras (mundos, personajes, mapas y misiones) no estan incluidos en el repositorio.
- Las herramientas de autor y el motor de juego continuan evolucionando y refinandose activamente.
- El repositorio se enfoca en el codigo del nucleo del motor, el depurador visual y el editor de contenido.

### Comandos de Ejecucion (Entorno de Desarrollo)

- Iniciar el depurador visual de juego:
  ```bash
  python main.py --play-debug
  ```

- Iniciar el editor de aventuras:
  ```bash
  python main.py --editor
  ```

- Ejecutar en modo consola:
  ```bash
  python main.py
  ```
