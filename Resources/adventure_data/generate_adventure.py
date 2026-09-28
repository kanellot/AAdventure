"""
Script generador canónico para Adventure.aad.
Crea el paquete de aventura por defecto de AAdventure ("El Enigma de Villa Roca y la Corona de Arturo")
que sirve como benchmark funcional integral para la totalidad de mecanismos del motor de simulación.
"""

import os
import sys

# Asegurar que el directorio raíz del proyecto está en el PATH
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from adventure_packager import AdventurePackager


def build_adventure_data():
    # -------------------------------------------------------------------------
    # 1. WORLD DATA (11 Lugares en Villa Roca)
    # -------------------------------------------------------------------------
    world_data = {
        "world": {
            "id": "w01",
            "name": "Shire",
            "description": "Shire es una tranquila comarca de Amoen, su principal pueblo es Villa Roca.",
            "initial_text": "Despiertas bajo el cielo despejado de Villa Roca. Las campanas de la iglesia tañen a lo lejos y el murmullo de los mercaderes comienza a llenar las calles empedradas de la comarca. Tu gran aventura está a punto de comenzar.",
            "locations": [
                {
                    "id": "l_01",
                    "name": "Villa Roca",
                    "description": "Villa principal de la comarca de Shire, rodeada de montañas y colindante al castillo real.",
                    "places": [
                        {
                            "id": "p_00",
                            "name": "Plaza Mayor",
                            "description": "El corazón de Villa Roca. El sol ilumina una hermosa plaza con una gran fuente circular en el centro. Al norte el camino conduce a la Calle Pobre, al sur hacia el parque, al este hacia la iglesia y al oeste hacia la mansión del Mago.",
                            "blocked_place": False,
                            "visible_entities": [],
                            "connections": {
                                "North": {"target": "p_01", "distance": 150, "terrain_type": "village"},
                                "South": {"target": "p_09", "distance": 200, "terrain_type": "village"},
                                "East": {"target": "p_08", "distance": 100, "terrain_type": "village"},
                                "West": {"target": "p_07", "distance": 300, "terrain_type": "village"},
                            },
                        },
                        {
                            "id": "p_01",
                            "name": "Calle Pobre",
                            "description": "Calle estrecha y empedrada bajo viejos soportales de madera donde suelen cobijarse los más desfavorecidos de la villa pidiendo limosna.",
                            "blocked_place": False,
                            "visible_entities": ["npc_mendigo"],
                            "connections": {
                                "North": {"target": "p_02", "distance": 250, "terrain_type": "village"},
                                "South": {"target": "p_00", "distance": 150, "terrain_type": "village"},
                            },
                        },
                        {
                            "id": "p_02",
                            "name": "Plaza Menor",
                            "description": "Segunda plaza de la villa, animada y comercial. Al oeste el aroma a malta anuncia la taberna, al este relucen los mostradores de la tienda y al norte se alza el puente del castillo.",
                            "blocked_place": False,
                            "visible_entities": [],
                            "connections": {
                                "North": {"target": "p_05", "distance": 400, "terrain_type": "village"},
                                "South": {"target": "p_01", "distance": 250, "terrain_type": "village"},
                                "East": {"target": "p_04", "distance": 80, "terrain_type": "village"},
                                "West": {"target": "p_03", "distance": 120, "terrain_type": "village"},
                            },
                        },
                        {
                            "id": "p_03",
                            "name": "Taberna",
                            "description": "Taberna 'El Jabalí Dorado', concurrido punto de reunión de lugareños y viajeros. Mesas de roble, una chimenea crepitante y jarras de cerveza sobre el mostrador.",
                            "blocked_place": False,
                            "visible_entities": ["npc_tabernero"],
                            "connections": {
                                "East": {"target": "p_02", "distance": 120, "terrain_type": "village"},
                            },
                        },
                        {
                            "id": "p_04",
                            "name": "Tienda",
                            "description": "El Bazar Principal de ultramarinos y reliquias de Villa Roca. Repisas abarrotadas de víveres, mapas y salvoconductos sellados.",
                            "blocked_place": False,
                            "visible_entities": ["npc_comerciante"],
                            "connections": {
                                "West": {"target": "p_02", "distance": 80, "terrain_type": "village"},
                            },
                        },
                        {
                            "id": "p_05",
                            "name": "Entrada al Castillo",
                            "description": "Imponente puente levadizo sobre el foso de la fortaleza real. Pesadas cadenas y rastrillos de hierro protegen el paso bajo la severa mirada de la guardia real.",
                            "blocked_place": False,
                            "visible_entities": ["npc_guardia"],
                            "connections": {
                                "North": {"target": "p_06", "distance": 500, "terrain_type": "village"},
                                "South": {"target": "p_02", "distance": 400, "terrain_type": "village"},
                            },
                        },
                        {
                            "id": "p_06",
                            "name": "Sala del Rey",
                            "description": "El solemne salón del trono de Amoen. Tapices de la corona, vitrales dorados y estatuas de piedra conducen al trono del Rey Arturo.",
                            "blocked_place": True,  # Bloqueado inicialmente
                            "visible_entities": ["npc_rey_arturo"],
                            "connections": {
                                "South": {"target": "p_05", "distance": 500, "terrain_type": "village"},
                            },
                        },
                        {
                            "id": "p_07",
                            "name": "Casa Mago",
                            "description": "Mansión de piedra oscura repleta de pergaminos arcanos y estantes alquímicos. En una esquina, una trampilla con runas mágicas conduce al sótano subterráneo.",
                            "blocked_place": False,
                            "visible_entities": ["npc_mago"],
                            "connections": {
                                "East": {"target": "p_00", "distance": 300, "terrain_type": "village"},
                                "Down": {"target": "p_10", "distance": 20, "terrain_type": "village"},
                            },
                        },
                        {
                            "id": "p_08",
                            "name": "Iglesia",
                            "description": "Antigua capilla de piedra consagrada a la paz y la luz. La atmósfera es serena y silenciosa, iluminada por cirios encendidos ante el altar mayor.",
                            "blocked_place": False,
                            "visible_entities": ["npc_cura"],
                            "connections": {
                                "West": {"target": "p_00", "distance": 100, "terrain_type": "village"},
                            },
                        },
                        {
                            "id": "p_09",
                            "name": "Parque",
                            "description": "Hermosos jardines públicos con estanques transparentes y sauces llorones donde juegan los niños de la villa.",
                            "blocked_place": False,
                            "visible_entities": ["npc_nino_01", "npc_nino_02"],
                            "connections": {
                                "North": {"target": "p_00", "distance": 200, "terrain_type": "village"},
                            },
                        },
                        {
                            "id": "p_10",
                            "name": "Sótano del Mago",
                            "description": "Cámara subterránea secreta excavada en roca viva. En el centro descansa un pedestal de mármol negro que custodia un grimorio de poder arcano.",
                            "blocked_place": True,  # Bloqueado inicialmente
                            "visible_entities": [],
                            "connections": {
                                "Up": {"target": "p_07", "distance": 20, "terrain_type": "village"},
                            },
                        },
                    ],
                }
            ],
        }
    }

    # -------------------------------------------------------------------------
    # 2. NPCS DATA (9 Personajes)
    # -------------------------------------------------------------------------
    npcs_data = {
        "npcs": [
            {
                "id": "npc_mendigo",
                "name": "Mendigo",
                "description": "Un anciano encorvado vestido con harapos remendados. Tartamudea por el frío, pero su mirada se llena de agradecimiento si alguien le ofrece compasión o comida.",
                "state": "none",
                "affinity": 0.5,
                "motivations": {
                    "likes": ["Que le den limosna o comida", "Palabras amables", "Trato respetuoso"],
                    "dislikes": ["Burlas", "Amenazas", "Desprecio"],
                },
                "dynamic_lore": [],
                "initial_location": "p_01",
            },
            {
                "id": "npc_tabernero",
                "name": "Tabernero",
                "description": "El dueño de 'El Jabalí Dorado'. Un hombre robusto y franco, de delantal manchado y risa contagiosa que adora escuchar anécdotas de tierras lejanas.",
                "state": "none",
                "affinity": 0.5,
                "motivations": {
                    "likes": ["Elogios a su cerveza", "Historias de viajes", "Clientes educados"],
                    "dislikes": ["Peleas en su taberna", "Regatear habitaciones"],
                },
                "dynamic_lore": [],
                "initial_location": "p_03",
            },
            {
                "id": "npc_comerciante",
                "name": "Comerciante",
                "description": "Mercader perspicaz del bazar principal. Viste túnicas finas con anillos brillantes; valora la puntualidad y los tratos claros y rentables.",
                "state": "none",
                "affinity": 0.5,
                "motivations": {
                    "likes": ["Compradores decididos", "Oro contante y sonante", "Reliquias de valor"],
                    "dislikes": ["Hacerle perder el tiempo", "Regateos absurdos"],
                },
                "dynamic_lore": [],
                "initial_location": "p_04",
            },
            {
                "id": "npc_guardia",
                "name": "Guardia Real",
                "description": "Un veterano de la guardia real con armadura de placas bruñida y alabarda. Severo, disciplinado e incorruptible.",
                "state": "none",
                "affinity": 0.3,
                "motivations": {
                    "likes": ["Salvoconductos oficiales", "Disciplina marcial", "Respeto a la corona"],
                    "dislikes": ["Cruzar sin permiso", "Insolencias", "Faltas de respeto"],
                },
                "dynamic_lore": [],
                "initial_location": "p_05",
            },
            {
                "id": "npc_rey_arturo",
                "name": "Rey Arturo",
                "description": "El noble y prudente soberano de Amoen. Porta capa de armiño y corona de oro, guiado por el honor y la justicia hacia su pueblo.",
                "state": "none",
                "affinity": 0.5,
                "motivations": {
                    "likes": ["Lealtad", "Resolución de enigmas arcanos", "Valor demostrado"],
                    "dislikes": ["Traición", "Cobardía", "Falsedad"],
                },
                "dynamic_lore": [],
                "initial_location": "p_06",
            },
            {
                "id": "npc_mago",
                "name": "Mago",
                "description": "Sabio erudito de la corte con túnica bordada en constelaciones. Fascinado por los misterios arcanos y las runas de tiempos remotos.",
                "state": "none",
                "affinity": 0.5,
                "motivations": {
                    "likes": ["Curiosidad mágica", "Grimorios antiguos", "Preguntas intelectuales"],
                    "dislikes": ["Interrupciones vulgares", "Ignorancia arrogante"],
                },
                "dynamic_lore": [],
                "initial_location": "p_07",
            },
            {
                "id": "npc_cura",
                "name": "Cura",
                "description": "El párroco de la iglesia, de mirada compasiva y voz serena. Siempre dispuesto a impartir bendiciones y consuelo a los viajeros.",
                "state": "none",
                "affinity": 0.5,
                "motivations": {
                    "likes": ["Caridad", "Oraciones devotas", "Humildad"],
                    "dislikes": ["Profanaciones", "Violencia injustificada"],
                },
                "dynamic_lore": [],
                "initial_location": "p_08",
            },
            {
                "id": "npc_nino_01",
                "name": "Niño Alegre",
                "description": "Un jovencito enérgico que corre por el parque haciendo rodar su aro de madera.",
                "state": "none",
                "affinity": 0.5,
                "motivations": {
                    "likes": ["Juegos", "Carreras", "Aventuras"],
                    "dislikes": ["Gente aburrida", "Regañinas"],
                },
                "dynamic_lore": [],
                "initial_location": "p_09",
            },
            {
                "id": "npc_nino_02",
                "name": "Niña Juguetona",
                "description": "Una risueña pequeña que trenza coronas de flores junto al estanque del parque y canta melodías populares.",
                "state": "none",
                "affinity": 0.5,
                "motivations": {
                    "likes": ["Flores", "Canciones", "Cuentos de hadas"],
                    "dislikes": ["Bichos molestos", "Estar sola"],
                },
                "dynamic_lore": [],
                "initial_location": "p_09",
            },
        ]
    }

    # -------------------------------------------------------------------------
    # 3. ITEMS DATA (8 Objetos variados)
    # -------------------------------------------------------------------------
    items_data = {
        "items": [
            {
                "id": "item_pan",
                "name": "Hogaza de Pan",
                "description": "Una tierna hogaza de pan recién horneada en la tienda de ultramarinos.",
                "state": "default",
                "initial_location": "p_04",
            },
            {
                "id": "item_llave_bodega",
                "name": "Llave de Bronce",
                "description": "Una pequeña llave de bronce escondida bajo las tablas de una mesa en la taberna.",
                "state": "default",
                "initial_location": "p_03",
            },
            {
                "id": "item_llave_arcana",
                "name": "Llave Arcana",
                "description": "Una llave imbuida en magia azulada capaz de abrir el sótano sellado del mago.",
                "state": "default",
                "initial_location": "p_07",
            },
            {
                "id": "item_salvoconducto",
                "name": "Salvoconducto Real",
                "description": "Un documento oficial con el sello del senescal que autoriza el paso al castillo real.",
                "state": "default",
                "initial_location": "p_04",
            },
            {
                "id": "item_caliz_plata",
                "name": "Cáliz de Plata",
                "description": "Un hermoso cáliz de plata bendecido por el párroco de la iglesia.",
                "state": "default",
                "initial_location": "p_08",
            },
            {
                "id": "item_grimorio_antiguo",
                "name": "Grimorio Arcano",
                "description": "Un antiguo tomo encuadernado en cuero negro con runas mágicas palpitantes.",
                "state": "default",
                "initial_location": "p_10",
            },
            {
                "id": "item_moneda_antigua",
                "name": "Moneda Antigua",
                "description": "Una rara moneda conmemorativa de Villa Roca grabada con el escudo de los primeros reyes.",
                "state": "default",
                "initial_location": "p_01",
            },
            {
                "id": "item_aro_madera",
                "name": "Aro de Madera",
                "description": "Un pulido aro de sauce con el que juegan los niños en los jardines del parque.",
                "state": "default",
                "initial_location": "p_09",
            },
        ]
    }

    # -------------------------------------------------------------------------
    # 4. PLAYER DATA
    # -------------------------------------------------------------------------
    player_data = {
        "player": {
            "id": "player",
            "name": "Aventurero",
            "description": "Un intrépido aventurero que llega a Villa Roca con el anhelo de conseguir una audiencia real con el Rey Arturo.",
            "state": "none",
            "gold": 15,
            "active_quest": "c1_villa_roca",
            "completed_quests": [],
            "inventory": [],
            "travel_speed": 4.5,
            "elapsed_time": 0,
            "active_block": "c1_villa_roca",
            "initial_location": "p_00",
        }
    }

    # -------------------------------------------------------------------------
    # 5. LOREBLOCKS DATA (Árbol HSM Benchmark Integral)
    # -------------------------------------------------------------------------
    lore_data = {
        "lore_blocks": [
            # Popup inicial al entrar
            {
                "id": "popup_bienvenida",
                "name": "Llegada a Villa Roca",
                "title": "Llegada a Villa Roca",
                "description": "¡Bienvenido a Villa Roca! Tu objetivo es lograr una audiencia con el Rey Arturo en su castillo.",
                "type": "popup",
                "parent_id": None,
                "state": "unknown",
                "active_conditions": [
                    {
                        "rag_enabled": False,
                        "trigger_phrases": [],
                        "conditions": [
                            {
                                "entity_type": "place",
                                "entity_id": "p_00",
                                "sub_condition": "current_location",
                                "value": None,
                                "is_negated": False,
                            }
                        ],
                    }
                ],
                "done_conditions": [],
                "effects": [],
            },
            # Capítulo 1: Contenedor raíz
            {
                "id": "c1_villa_roca",
                "name": "Capítulo 1: Los Secretos de Villa Roca",
                "title": "Capítulo 1: Los Secretos de Villa Roca",
                "description": "Explora la villa, asiste a sus gentes y descubre cómo franquear las defensas del castillo real.",
                "type": "Chapter",
                "parent_id": None,
                "state": "active",
                "active_conditions": [],
                "done_conditions": [
                    {
                        "rag_enabled": False,
                        "trigger_phrases": [],
                        "conditions": [
                            {
                                "entity_type": "loreblock",
                                "entity_id": "c1_villa_roca",
                                "sub_condition": "all_children_done",
                                "value": None,
                                "is_negated": False,
                            }
                        ],
                    }
                ],
                "effects": [
                    {
                        "target": None,
                        "action": "hook",
                        "elapsed_time": "00:00",
                        "directive": "Has llegado a Villa Roca. Debes explorar el entorno para abrirte paso hasta el castillo.",
                        "bypass_llm": False,
                        "gold_delta": 0,
                        "affinity_delta": 0.0,
                        "give_items": [],
                        "take_items": [],
                        "unlock_places": [],
                        "unlock_npcs": [],
                        "unlock_items": [],
                        "block_places": [],
                        "unblock_places": [],
                    }
                ],
            },
            # Quest 1: El Favor del Mendigo
            {
                "id": "q_favor_mendigo",
                "name": "Misión: El Favor del Mendigo",
                "title": "Misión: El Favor del Mendigo",
                "description": "Ayuda al mendigo de la Calle Pobre para ganarte su confianza y obtener pistas sobre la villa.",
                "type": "Quest",
                "parent_id": "c1_villa_roca",
                "state": "active",
                "active_conditions": [],
                "done_conditions": [
                    {
                        "rag_enabled": False,
                        "trigger_phrases": [],
                        "conditions": [
                            {
                                "entity_type": "loreblock",
                                "entity_id": "q_favor_mendigo",
                                "sub_condition": "all_children_done",
                                "value": None,
                                "is_negated": False,
                            }
                        ],
                    }
                ],
                "effects": [
                    {
                        "target": "npc_mendigo",
                        "action": "hook",
                        "elapsed_time": "00:00",
                        "directive": "El mendigo parece hambriento y desamparado. Una buena acción podría recompensarte.",
                        "bypass_llm": False,
                        "gold_delta": 0,
                        "affinity_delta": 0.0,
                        "give_items": [],
                        "take_items": [],
                        "unlock_places": [],
                        "unlock_npcs": [],
                        "unlock_items": [],
                        "block_places": [],
                        "unblock_places": [],
                    }
                ],
            },
            # Tarea 1.1: Hablar con el mendigo
            {
                "id": "t_hablar_mendigo",
                "name": "Escuchar al mendigo",
                "title": "Escuchar al mendigo",
                "description": "Conversa con el mendigo en la Calle Pobre para conocer sus pesares.",
                "type": "Task",
                "parent_id": "q_favor_mendigo",
                "state": "active",
                "active_conditions": [],
                "done_conditions": [
                    {
                        "rag_enabled": False,
                        "trigger_phrases": [],
                        "conditions": [
                            {
                                "entity_type": "npc",
                                "entity_id": "npc_mendigo",
                                "sub_condition": "talk",
                                "value": None,
                                "is_negated": False,
                            }
                        ],
                    }
                ],
                "effects": [
                    {
                        "target": "npc_mendigo",
                        "action": "hook",
                        "elapsed_time": "00:05",
                        "directive": "El mendigo te mira con timidez y te agradece que te detengas a escucharle.",
                        "bypass_llm": False,
                        "gold_delta": 0,
                        "affinity_delta": 0.1,
                        "give_items": [],
                        "take_items": [],
                        "unlock_places": [],
                        "unlock_npcs": [],
                        "unlock_items": [],
                        "block_places": [],
                        "unblock_places": [],
                    }
                ],
            },
            # Tarea 1.2: Dar pan al mendigo
            {
                "id": "t_dar_pan_mendigo",
                "name": "Entregar comida al mendigo",
                "title": "Entregar comida al mendigo",
                "description": "Ofrécele una hogaza de pan al mendigo para saciar su apetito.",
                "type": "Task",
                "parent_id": "q_favor_mendigo",
                "state": "unknown",
                "active_conditions": [
                    {
                        "rag_enabled": False,
                        "trigger_phrases": [],
                        "conditions": [
                            {
                                "entity_type": "loreblock",
                                "entity_id": "t_hablar_mendigo",
                                "sub_condition": "done",
                                "value": None,
                                "is_negated": False,
                            }
                        ],
                    }
                ],
                "done_conditions": [
                    {
                        "rag_enabled": True,
                        "trigger_phrases": ["dar pan", "ofrecer comida", "tomar un trozo de pan", "aquí tienes pan"],
                        "conditions": [
                            {
                                "entity_type": "npc",
                                "entity_id": "npc_mendigo",
                                "sub_condition": "talk",
                                "value": None,
                                "is_negated": False,
                            },
                            {
                                "entity_type": "item",
                                "entity_id": "item_pan",
                                "sub_condition": "have",
                                "value": None,
                                "is_negated": False,
                            },
                        ],
                    }
                ],
                "effects": [
                    {
                        "target": "npc_mendigo",
                        "action": "hook",
                        "elapsed_time": "00:05",
                        "directive": "El mendigo devora el pan con infinita gratitud y a cambio te entrega una rara moneda antigua.",
                        "bypass_llm": True,
                        "gold_delta": 0,
                        "affinity_delta": 0.3,
                        "give_items": ["item_moneda_antigua"],
                        "take_items": ["item_pan"],
                        "unlock_places": [],
                        "unlock_npcs": [],
                        "unlock_items": [],
                        "block_places": [],
                        "unblock_places": [],
                    }
                ],
            },
            # Quest 2: El Secreto del Mago
            {
                "id": "q_secreto_mago",
                "name": "Misión: El Secreto del Mago",
                "title": "Misión: El Secreto del Mago",
                "description": "Investiga el misterio del sótano sellado en la mansión del mago y recupera su grimorio.",
                "type": "Quest",
                "parent_id": "c1_villa_roca",
                "state": "active",
                "active_conditions": [],
                "done_conditions": [
                    {
                        "rag_enabled": False,
                        "trigger_phrases": [],
                        "conditions": [
                            {
                                "entity_type": "loreblock",
                                "entity_id": "q_secreto_mago",
                                "sub_condition": "all_children_done",
                                "value": None,
                                "is_negated": False,
                            }
                        ],
                    }
                ],
                "effects": [
                    {
                        "target": "npc_mago",
                        "action": "hook",
                        "elapsed_time": "00:00",
                        "directive": "El mago busca un aventurero valiente dispuesto a descender a su sótano arcano.",
                        "bypass_llm": False,
                        "gold_delta": 0,
                        "affinity_delta": 0.0,
                        "give_items": [],
                        "take_items": [],
                        "unlock_places": [],
                        "unlock_npcs": [],
                        "unlock_items": [],
                        "block_places": [],
                        "unblock_places": [],
                    }
                ],
            },
            # Tarea 2.1: Encontrar la Llave Arcana
            {
                "id": "t_llave_arcana",
                "name": "Localizar la Llave Arcana",
                "title": "Localizar la Llave Arcana",
                "description": "Encuentra la llave mágica en la Casa del Mago.",
                "type": "Task",
                "parent_id": "q_secreto_mago",
                "state": "active",
                "active_conditions": [],
                "done_conditions": [
                    {
                        "rag_enabled": False,
                        "trigger_phrases": [],
                        "conditions": [
                            {
                                "entity_type": "place",
                                "entity_id": "p_07",
                                "sub_condition": "current_location",
                                "value": None,
                                "is_negated": False,
                            },
                            {
                                "entity_type": "item",
                                "entity_id": "item_llave_arcana",
                                "sub_condition": "visible",
                                "value": None,
                                "is_negated": False,
                            },
                        ],
                    }
                ],
                "effects": [
                    {
                        "target": None,
                        "action": "hook",
                        "elapsed_time": "00:05",
                        "directive": "Descubres la Llave Arcana reluciendo sobre la mesa de pergaminos.",
                        "bypass_llm": False,
                        "gold_delta": 0,
                        "affinity_delta": 0.0,
                        "give_items": ["item_llave_arcana"],
                        "take_items": [],
                        "unlock_places": [],
                        "unlock_npcs": [],
                        "unlock_items": [],
                        "block_places": [],
                        "unblock_places": [],
                    }
                ],
            },
            # Tarea 2.2: Desbloquear el sótano
            {
                "id": "t_abrir_sotano",
                "name": "Abrir el Sótano del Mago",
                "title": "Abrir el Sótano del Mago",
                "description": "Usa la Llave Arcana para abrir la trampilla sellada que desciende al sótano.",
                "type": "Task",
                "parent_id": "q_secreto_mago",
                "state": "unknown",
                "active_conditions": [
                    {
                        "rag_enabled": False,
                        "trigger_phrases": [],
                        "conditions": [
                            {
                                "entity_type": "item",
                                "entity_id": "item_llave_arcana",
                                "sub_condition": "have",
                                "value": None,
                                "is_negated": False,
                            }
                        ],
                    }
                ],
                "done_conditions": [
                    {
                        "rag_enabled": False,
                        "trigger_phrases": [],
                        "conditions": [
                            {
                                "entity_type": "place",
                                "entity_id": "p_07",
                                "sub_condition": "current_location",
                                "value": None,
                                "is_negated": False,
                            },
                            {
                                "entity_type": "item",
                                "entity_id": "item_llave_arcana",
                                "sub_condition": "have",
                                "value": None,
                                "is_negated": False,
                            },
                        ],
                    }
                ],
                "effects": [
                    {
                        "target": None,
                        "action": "hook",
                        "elapsed_time": "00:05",
                        "directive": "Introduces la Llave Arcana en la trampilla; con un chasquido resplandeciente, el sótano queda desbloqueado.",
                        "bypass_llm": False,
                        "gold_delta": 0,
                        "affinity_delta": 0.0,
                        "give_items": [],
                        "take_items": [],
                        "unlock_places": ["p_10"],
                        "unlock_npcs": [],
                        "unlock_items": ["item_grimorio_antiguo"],
                        "block_places": [],
                        "unblock_places": ["p_10"],
                    }
                ],
            },
            # Tarea 2.3: Recuperar el grimorio
            {
                "id": "t_recuperar_grimorio",
                "name": "Recuperar el Grimorio Arcano",
                "title": "Recuperar el Grimorio Arcano",
                "description": "Desciende al sótano y toma posesión del tomo arcano.",
                "type": "Task",
                "parent_id": "q_secreto_mago",
                "state": "unknown",
                "active_conditions": [
                    {
                        "rag_enabled": False,
                        "trigger_phrases": [],
                        "conditions": [
                            {
                                "entity_type": "loreblock",
                                "entity_id": "t_abrir_sotano",
                                "sub_condition": "done",
                                "value": None,
                                "is_negated": False,
                            }
                        ],
                    }
                ],
                "done_conditions": [
                    {
                        "rag_enabled": False,
                        "trigger_phrases": [],
                        "conditions": [
                            {
                                "entity_type": "place",
                                "entity_id": "p_10",
                                "sub_condition": "current_location",
                                "value": None,
                                "is_negated": False,
                            }
                        ],
                    }
                ],
                "effects": [
                    {
                        "target": None,
                        "action": "hook",
                        "elapsed_time": "00:10",
                        "directive": "Tomas el Grimorio Arcano del pedestal. Un poder misterioso palpita en tus manos.",
                        "bypass_llm": False,
                        "gold_delta": 0,
                        "affinity_delta": 0.0,
                        "give_items": ["item_grimorio_antiguo"],
                        "take_items": [],
                        "unlock_places": [],
                        "unlock_npcs": [],
                        "unlock_items": [],
                        "block_places": [],
                        "unblock_places": [],
                    }
                ],
            },
            # Quest 3: Conseguir el Salvoconducto
            {
                "id": "q_salvoconducto",
                "name": "Misión: Conseguir el Salvoconducto",
                "title": "Misión: Conseguir el Salvoconducto",
                "description": "Adquiere el pase real para que la guardia te permita el acceso al castillo.",
                "type": "Quest",
                "parent_id": "c1_villa_roca",
                "state": "active",
                "active_conditions": [],
                "done_conditions": [
                    {
                        "rag_enabled": False,
                        "trigger_phrases": [],
                        "conditions": [
                            {
                                "entity_type": "item",
                                "entity_id": "item_salvoconducto",
                                "sub_condition": "have",
                                "value": None,
                                "is_negated": False,
                            }
                        ],
                    }
                ],
                "effects": [
                    {
                        "target": "npc_guardia",
                        "action": "hook",
                        "elapsed_time": "00:00",
                        "directive": "El centinela real no te permitirá pasar sin un salvoconducto sellado.",
                        "bypass_llm": False,
                        "gold_delta": 0,
                        "affinity_delta": 0.0,
                        "give_items": [],
                        "take_items": [],
                        "unlock_places": [],
                        "unlock_npcs": [],
                        "unlock_items": [],
                        "block_places": [],
                        "unblock_places": [],
                    }
                ],
            },
            # Tarea 3.1: Comprar el salvoconducto en la tienda
            {
                "id": "t_comprar_salvoconducto",
                "name": "Comprar pase y provisiones en la tienda",
                "title": "Comprar pase y provisiones en la tienda",
                "description": "Paga 10 monedas de oro en el bazar para obtener el salvoconducto y una hogaza de pan.",
                "type": "Task",
                "parent_id": "q_salvoconducto",
                "state": "active",
                "active_conditions": [],
                "done_conditions": [
                    {
                        "rag_enabled": False,
                        "trigger_phrases": [],
                        "conditions": [
                            {
                                "entity_type": "place",
                                "entity_id": "p_04",
                                "sub_condition": "current_location",
                                "value": None,
                                "is_negated": False,
                            },
                            {
                                "entity_type": "gold",
                                "entity_id": "gold",
                                "sub_condition": "have",
                                "value": 10,
                                "is_negated": False,
                            },
                        ],
                    }
                ],
                "effects": [
                    {
                        "target": "npc_comerciante",
                        "action": "hook",
                        "elapsed_time": "00:10",
                        "directive": "Pagas 10 monedas de oro al comerciante y recibes el Salvoconducto Real junto a una hogaza de pan.",
                        "bypass_llm": False,
                        "gold_delta": -10,
                        "affinity_delta": 0.1,
                        "give_items": ["item_salvoconducto", "item_pan"],
                        "take_items": [],
                        "unlock_places": [],
                        "unlock_npcs": [],
                        "unlock_items": [],
                        "block_places": [],
                        "unblock_places": [],
                    }
                ],
            },
            # Evento Semántico RAG: Secreto de la taberna
            {
                "id": "ev_taberna_secreto",
                "name": "Secreto bajo la mesa de la Taberna",
                "title": "Secreto bajo la mesa de la Taberna",
                "description": "Una discreta búsqueda táctil revela un compartimento oculto bajo una mesa del mesón.",
                "type": "Event",
                "parent_id": "c1_villa_roca",
                "state": "active",
                "active_conditions": [],
                "done_conditions": [
                    {
                        "rag_enabled": True,
                        "trigger_phrases": ["mirar bajo la mesa", "buscar bajo la mesa", "agacharme a inspeccionar el suelo", "inspeccionar las tablas"],
                        "conditions": [
                            {
                                "entity_type": "place",
                                "entity_id": "p_03",
                                "sub_condition": "current_location",
                                "value": None,
                                "is_negated": False,
                            }
                        ],
                    }
                ],
                "effects": [
                    {
                        "target": None,
                        "action": "hook",
                        "elapsed_time": "00:05",
                        "directive": "¡Tus dedos palpan un objeto metálico fijado con cera! Extraes una antigua Llave de Bronce.",
                        "bypass_llm": True,
                        "gold_delta": 0,
                        "affinity_delta": 0.0,
                        "give_items": ["item_llave_bodega"],
                        "take_items": [],
                        "unlock_places": [],
                        "unlock_npcs": [],
                        "unlock_items": [],
                        "block_places": [],
                        "unblock_places": [],
                    }
                ],
            },
            # Evento Temporal y de Afinidad: Bendición en la iglesia
            {
                "id": "ev_iglesia_bendicion",
                "name": "Bendición Matutina del Cura",
                "title": "Bendición Matutina del Cura",
                "description": "Durante las horas del día, el párroco imparte su bendición a los piadosos que conversan con él.",
                "type": "Event",
                "parent_id": "c1_villa_roca",
                "state": "active",
                "active_conditions": [],
                "done_conditions": [
                    {
                        "rag_enabled": False,
                        "trigger_phrases": [],
                        "conditions": [
                            {
                                "entity_type": "place",
                                "entity_id": "p_08",
                                "sub_condition": "visited",
                                "value": None,
                                "is_negated": False,
                            },
                            {
                                "entity_type": "time",
                                "entity_id": "time",
                                "sub_condition": "time_range",
                                "value": "08:00-18:00",
                                "is_negated": False,
                            },
                            {
                                "entity_type": "npc",
                                "entity_id": "npc_cura",
                                "sub_condition": "talk",
                                "value": None,
                                "is_negated": False,
                            },
                        ],
                    }
                ],
                "effects": [
                    {
                        "target": "npc_cura",
                        "action": "hook",
                        "elapsed_time": "00:05",
                        "directive": "El párroco traza una bendición en tu frente, deseándote fortuna y rectitud en tu periplo.",
                        "bypass_llm": False,
                        "gold_delta": 0,
                        "affinity_delta": 0.2,
                        "give_items": [],
                        "take_items": [],
                        "unlock_places": [],
                        "unlock_npcs": [],
                        "unlock_items": [],
                        "block_places": [],
                        "unblock_places": [],
                    }
                ],
            },
            # Evento de Parque y Visibilidad de Entidades
            {
                "id": "ev_parque_juegos",
                "name": "La Alegría del Parque",
                "title": "La Alegría del Parque",
                "description": "Encuentro con los niños del parque en sus juegos cotidianos.",
                "type": "Event",
                "parent_id": "c1_villa_roca",
                "state": "active",
                "active_conditions": [],
                "done_conditions": [
                    {
                        "rag_enabled": False,
                        "trigger_phrases": [],
                        "conditions": [
                            {
                                "entity_type": "place",
                                "entity_id": "p_09",
                                "sub_condition": "current_location",
                                "value": None,
                                "is_negated": False,
                            },
                            {
                                "entity_type": "npc",
                                "entity_id": "npc_nino_01",
                                "sub_condition": "visible",
                                "value": None,
                                "is_negated": False,
                            },
                        ],
                    }
                ],
                "effects": [
                    {
                        "target": None,
                        "action": "hook",
                        "elapsed_time": "00:05",
                        "directive": "Los niños corretean alegremente a tu alrededor, llenando el parque de risas.",
                        "bypass_llm": False,
                        "gold_delta": 0,
                        "affinity_delta": 0.0,
                        "give_items": [],
                        "take_items": [],
                        "unlock_places": [],
                        "unlock_npcs": [],
                        "unlock_items": [],
                        "block_places": [],
                        "unblock_places": [],
                    }
                ],
            },
            # Capítulo 2: La Corona y el Arcano (Se activa al completar Capítulo 1)
            {
                "id": "c2_el_castillo",
                "name": "Capítulo 2: La Corona y el Arcano",
                "title": "Capítulo 2: La Corona y el Arcano",
                "description": "Franquea la guardia real y obtén tu ansiada audiencia en el salón del trono del Rey Arturo.",
                "type": "Chapter",
                "parent_id": None,
                "state": "unknown",
                "active_conditions": [
                    {
                        "rag_enabled": False,
                        "trigger_phrases": [],
                        "conditions": [
                            {
                                "entity_type": "loreblock",
                                "entity_id": "c1_villa_roca",
                                "sub_condition": "done",
                                "value": None,
                                "is_negated": False,
                            }
                        ],
                    }
                ],
                "done_conditions": [
                    {
                        "rag_enabled": False,
                        "trigger_phrases": [],
                        "conditions": [
                            {
                                "entity_type": "loreblock",
                                "entity_id": "q_audiencia_real",
                                "sub_condition": "done",
                                "value": None,
                                "is_negated": False,
                            }
                        ],
                    }
                ],
                "effects": [
                    {
                        "target": None,
                        "action": "hook",
                        "elapsed_time": "00:05",
                        "directive": "Has completado todas las hazañas de la villa. El puente del castillo se abre solemnemente.",
                        "bypass_llm": False,
                        "gold_delta": 0,
                        "affinity_delta": 0.0,
                        "give_items": [],
                        "take_items": [],
                        "unlock_places": ["p_06"],
                        "unlock_npcs": ["npc_rey_arturo"],
                        "unlock_items": [],
                        "block_places": [],
                        "unblock_places": ["p_06"],  # Desbloquea la Sala del Rey
                    }
                ],
            },
            # Quest 4: Audiencia con el Rey Arturo
            {
                "id": "q_audiencia_real",
                "name": "Misión: Audiencia con el Rey Arturo",
                "title": "Misión: Audiencia con el Rey Arturo",
                "description": "Entra en la Sala del Trono y entrega el Grimorio Arcano al soberano.",
                "type": "Quest",
                "parent_id": "c2_el_castillo",
                "state": "unknown",
                "active_conditions": [
                    {
                        "rag_enabled": False,
                        "trigger_phrases": [],
                        "conditions": [
                            {
                                "entity_type": "loreblock",
                                "entity_id": "c2_el_castillo",
                                "sub_condition": "active",
                                "value": None,
                                "is_negated": False,
                            }
                        ],
                    }
                ],
                "done_conditions": [
                    {
                        "rag_enabled": False,
                        "trigger_phrases": [],
                        "conditions": [
                            {
                                "entity_type": "place",
                                "entity_id": "p_06",
                                "sub_condition": "current_location",
                                "value": None,
                                "is_negated": False,
                            },
                            {
                                "entity_type": "item",
                                "entity_id": "item_grimorio_antiguo",
                                "sub_condition": "have",
                                "value": None,
                                "is_negated": False,
                            },
                            {
                                "entity_type": "npc",
                                "entity_id": "npc_rey_arturo",
                                "sub_condition": "talk",
                                "value": None,
                                "is_negated": False,
                            },
                        ],
                    }
                ],
                "effects": [
                    {
                        "target": "npc_rey_arturo",
                        "action": "hook",
                        "elapsed_time": "00:15",
                        "directive": "El Rey Arturo admira el Grimorio Arcano, te condecora como Campeón de Amoen y te recompensa con 100 monedas de oro.",
                        "bypass_llm": False,
                        "gold_delta": 100,
                        "affinity_delta": 0.5,
                        "give_items": [],
                        "take_items": ["item_grimorio_antiguo"],
                        "unlock_places": [],
                        "unlock_npcs": [],
                        "unlock_items": [],
                        "block_places": [],
                        "unblock_places": [],
                    }
                ],
            },
            # Popup de Victoria Final
            {
                "id": "popup_victoria",
                "name": "¡Victoria en Villa Roca!",
                "title": "¡Victoria en Villa Roca!",
                "description": "¡Felicidades! Has completado con éxito la aventura benchmark de AAdventure con la bendición del Rey Arturo.",
                "type": "popup",
                "parent_id": "c2_el_castillo",
                "state": "unknown",
                "active_conditions": [
                    {
                        "rag_enabled": False,
                        "trigger_phrases": [],
                        "conditions": [
                            {
                                "entity_type": "loreblock",
                                "entity_id": "q_audiencia_real",
                                "sub_condition": "done",
                                "value": None,
                                "is_negated": False,
                            }
                        ],
                    }
                ],
                "done_conditions": [],
                "effects": [],
            },
        ]
    }

    # -------------------------------------------------------------------------
    # 6. STORY CONFIG
    # -------------------------------------------------------------------------
    config_data = {
        "elapsed_time": True,
        "fog_war": True,
        "affinity": True,
    }

    return world_data, npcs_data, player_data, items_data, lore_data, config_data


def generate_and_pack(output_path: str):
    print(f"Generando estructuras canónicas de aventura para '{output_path}'...")
    world_data, npcs_data, player_data, items_data, lore_data, config_data = build_adventure_data()

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    AdventurePackager.pack(
        output_path=output_path,
        world_data=world_data,
        npcs_data=npcs_data,
        player_data=player_data,
        items_data=items_data,
        lore_data=lore_data,
        config_data=config_data,
    )
    print(f"¡Aventura empaquetada con éxito en: {output_path}!")


if __name__ == "__main__":
    aad_target = os.path.join(PROJECT_ROOT, "Resources", "adventure_data", "Adventure.aad")
    generate_and_pack(aad_target)
