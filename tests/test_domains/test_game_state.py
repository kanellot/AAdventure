"""Pruebas unitarias para el modelo de dominio canónico GameState."""

import unittest
from pydantic import ValidationError
from domains.game_state import (
    EntityMapItem,
    EntityMapLocation,
    EntityMapNPC,
    EntityMapPlace,
    GameState,
    Inventory,
    LoreBlockHierarchy,
    NotebookEntry,
)
from domains.world import Place


class TestGameStateDomain(unittest.TestCase):
    """Pruebas de validación, estructura y ergonomía de GameState estándar."""

    def test_default_values(self):
        """Verifica que los valores por defecto del GameState sean los esperados."""
        gs = GameState()
        self.assertEqual(gs.player_name, "")
        self.assertEqual(gs.player_state, "EXPLORE")
        self.assertIsNone(gs.player_target)
        self.assertEqual(gs.current_location, "")
        self.assertIsNone(gs.current_time)
        self.assertEqual(gs.inventory, [])
        self.assertEqual(gs.gold, 0)
        self.assertIsNone(gs.place)
        self.assertEqual(gs.entity_map, [])
        self.assertIsInstance(gs.loreblocks, LoreBlockHierarchy)
        self.assertEqual(gs.loreblocks.unknown, [])
        self.assertEqual(gs.loreblocks.active, [])
        self.assertEqual(gs.loreblocks.done, [])
        self.assertEqual(gs.notebook, [])
        self.assertEqual(gs.conversations, {})

    def test_player_name(self):
        """Verifica la asignación directa de player_name."""
        gs = GameState(player_name="Link")
        self.assertEqual(gs.player_name, "Link")
        gs.player_name = "Zelda"
        self.assertEqual(gs.player_name, "Zelda")

    def test_player_state_validation(self):
        """Verifica que player_state solo acepte EXPLORE, TALK o LOOK."""
        for valid_state in ("EXPLORE", "TALK", "LOOK"):
            gs = GameState(player_state=valid_state)
            self.assertEqual(gs.player_state, valid_state)

        with self.assertRaises(ValidationError):
            GameState(player_state="INVALID_STATE")

    def test_player_target_field(self):
        """Verifica el campo player_target estándar."""
        gs = GameState()
        self.assertIsNone(gs.player_target)
        gs.player_target = "npc_guard"
        self.assertEqual(gs.player_target, "npc_guard")

    def test_current_location_and_current_time(self):
        """Verifica current_location y el comportamiento de current_time."""
        gs1 = GameState(current_location="place_town_square", current_time=None)
        self.assertEqual(gs1.current_location, "place_town_square")
        self.assertIsNone(gs1.current_time)

        gs2 = GameState(
            current_location="place_castle",
            current_time="Día 1, 14:30",
        )
        self.assertEqual(gs2.current_location, "place_castle")
        self.assertEqual(gs2.current_time, "Día 1, 14:30")

    def test_inventory(self):
        """Verifica el manejo de la lista de items en el inventario."""
        gs = GameState(inventory=["sword_01", "shield_wooden", "potion_health"])
        self.assertEqual(len(gs.inventory), 3)
        self.assertIn("sword_01", gs.inventory)

        # Normalización desde diccionarios u objetos con id
        gs_norm = GameState(inventory=[{"id": "key_brass"}, "rope"])
        self.assertEqual(gs_norm.inventory, ["key_brass", "rope"])

    def test_place_entity(self):
        """Verifica que place contenga la entidad Place completa para current_location."""
        full_place = Place(
            id="place_tavern",
            name="Taberna del Jabalí",
            description="Una taberna ruidosa y acogedora.",
            blocked_place=False,
        )
        gs = GameState(
            current_location="place_tavern",
            place=full_place,
        )
        self.assertIsNotNone(gs.place)
        self.assertEqual(gs.place.id, "place_tavern")
        self.assertEqual(gs.place.name, "Taberna del Jabalí")
        self.assertEqual(gs.place.description, "Una taberna ruidosa y acogedora.")

    def test_entity_map_structure(self):
        """Verifica la estructura y validación de entity_map jerárquico."""
        raw_map = [
            {
                "id": "loc_town",
                "name": "Pueblo de Inicio",
                "places": [
                    {
                        "id": "place_01",
                        "name": "Plaza Central",
                        "status": "visited",
                        "items": [
                            {"id": "item_apple", "name": "Manzana", "visible": True},
                            {"id": "item_coin", "name": "Moneda de oro", "visible": False},
                        ],
                        "npcs": [
                            {"id": "npc_merchant", "name": "Mercader", "status": "Known", "affinity": 0.6},
                            {"id": "npc_guard", "name": "Guardia", "status": "visible"},
                        ],
                    },
                    {
                        "id": "place_02",
                        "name": "Callejón Oscuro",
                        "status": "hidden",
                        "items": [],
                        "npcs": [],
                    },
                ],
            }
        ]
        gs = GameState(entity_map=raw_map)
        self.assertEqual(len(gs.entity_map), 1)

        loc = gs.entity_map[0]
        self.assertIsInstance(loc, EntityMapLocation)
        self.assertEqual(loc.id, "loc_town")
        self.assertEqual(len(loc.places), 2)

        p1 = loc.places[0]
        self.assertIsInstance(p1, EntityMapPlace)
        self.assertEqual(p1.id, "place_01")
        self.assertEqual(p1.status, "visited")
        self.assertEqual(len(p1.items), 2)
        self.assertIsInstance(p1.items[0], EntityMapItem)
        self.assertEqual(p1.items[0].id, "item_apple")
        self.assertTrue(p1.items[0].visible)
        self.assertEqual(len(p1.npcs), 2)
        self.assertIsInstance(p1.npcs[0], EntityMapNPC)
        self.assertEqual(p1.npcs[0].affinity, 0.6)

        p2 = loc.places[1]
        self.assertEqual(p2.status, "hidden")

    def test_loreblocks_hierarchy(self):
        """Verifica la jerarquía de loreblocks organizada en unknown, active, done."""
        lore_data = {
            "unknown": [
                {"id": "chapter_2", "name": "Capítulo 2", "children": []},
            ],
            "active": [
                {
                    "id": "quest_prologo",
                    "name": "Prólogo",
                    "children": [
                        {"id": "task_hablar_alcalde", "name": "Hablar con el alcalde"},
                    ],
                }
            ],
            "done": [
                {"id": "event_intro", "name": "Introducción", "children": []},
            ],
        }
        gs = GameState(loreblocks=lore_data)
        self.assertEqual(len(gs.loreblocks["unknown"]), 1)
        self.assertEqual(gs.loreblocks["unknown"][0]["id"], "chapter_2")
        self.assertEqual(len(gs.loreblocks["active"]), 1)
        self.assertEqual(len(gs.loreblocks["done"]), 1)
        self.assertEqual(gs.loreblocks.active[0]["id"], "quest_prologo")

        gs_empty_list = GameState(loreblocks=[])
        self.assertIsInstance(gs_empty_list.loreblocks, LoreBlockHierarchy)
        self.assertEqual(gs_empty_list.loreblocks["active"], [])

    def test_notebook_quests(self):
        """Verifica notebook con misiones activas y completadas."""
        quests = [
            {
                "id": "quest_sword",
                "name": "La Espada Perdida",
                "description": "Encuentra la espada oculta en las catacumbas.",
                "status": "active",
            },
            {
                "id": "quest_welcome",
                "name": "Bienvenida a la Aldea",
                "description": "Visita al anciano de la aldea.",
                "status": "done",
            },
        ]
        gs = GameState(notebook=quests)
        self.assertEqual(len(gs.notebook), 2)
        self.assertIsInstance(gs.notebook[0], NotebookEntry)
        self.assertEqual(gs.notebook[0].id, "quest_sword")
        self.assertEqual(gs.notebook[0].status, "active")
        self.assertEqual(gs.notebook[1].status, "done")

    def test_conversations_field(self):
        """Verifica el historial secuencial de conversaciones indexadas por target."""
        gs = GameState(
            conversations={
                "npc_tom": [
                    {"player": "Hola Tom"},
                    {"tom": "¡Bienvenido a la posada!"},
                ]
            }
        )
        self.assertIn("npc_tom", gs.conversations)
        self.assertEqual(len(gs.conversations["npc_tom"]), 2)
        self.assertEqual(gs.conversations["npc_tom"][0]["player"], "Hola Tom")
        self.assertEqual(gs.conversations["npc_tom"][1]["tom"], "¡Bienvenido a la posada!")

    def test_inventory_gold_manipulation(self):
        """Verifica la gestión de oro dentro del inventario de GameState."""
        gs = GameState(inventory={"items": ["sword", "shield"], "gold": 50})
        self.assertEqual(gs.inventory.gold, 50)
        self.assertEqual(gs.gold, 50)
        self.assertEqual(len(gs.inventory), 2)
        self.assertEqual(gs.inventory.items, ["sword", "shield"])

        gs.gold += 25
        self.assertEqual(gs.gold, 75)
        self.assertEqual(gs.inventory.gold, 75)

        gs.inventory.gold = 100
        self.assertEqual(gs.gold, 100)

        gs.inventory.append("magic_wand")
        self.assertEqual(len(gs.inventory), 3)
        self.assertIn("magic_wand", gs.inventory)

        dump = gs.model_dump()
        self.assertEqual(dump["inventory"]["gold"], 100)
        self.assertIn("magic_wand", dump["inventory"]["items"])

    def test_serialization_roundtrip(self):
        """Verifica serialización completa a diccionario y json."""
        gs = GameState(
            player_name="Robin",
            player_state="LOOK",
            player_target="p_forest",
            current_location="p_forest",
            current_time="Día 2, 09:15",
            inventory={"items": ["bow", "arrows"], "gold": 15},
            place=Place(id="p_forest", name="Bosque", description="Bosque denso"),
            entity_map=[
                EntityMapLocation(
                    id="loc_wilds",
                    name="Tierras Salvajes",
                    places=[
                        EntityMapPlace(
                            id="p_forest",
                            name="Bosque",
                            status="visited",
                            items=[EntityMapItem(id="arrow", name="Flecha", visible=True)],
                            npcs=[EntityMapNPC(id="npc_elf", name="Elfo", status="Known", affinity=0.8)],
                        )
                    ],
                )
            ],
            loreblocks=LoreBlockHierarchy(
                unknown=[],
                active=[{"id": "lb_survive", "name": "Sobrevivir"}],
                done=[],
            ),
            notebook=[
                NotebookEntry(id="lb_survive", name="Sobrevivir", description="Resiste el frío")
            ],
            conversations={"npc_elf": [{"player": "Saludos"}, {"elfo": "Bienvenido"}]},
        )

        data = gs.model_dump()
        self.assertEqual(data["player_name"], "Robin")
        self.assertEqual(data["player_state"], "LOOK")
        self.assertEqual(data["player_target"], "p_forest")
        self.assertEqual(data["current_location"], "p_forest")
        self.assertEqual(data["current_time"], "Día 2, 09:15")
        self.assertEqual(data["inventory"], {"items": ["bow", "arrows"], "gold": 15})
        self.assertEqual(data["place"]["id"], "p_forest")
        self.assertEqual(data["entity_map"][0]["id"], "loc_wilds")
        self.assertEqual(data["entity_map"][0]["places"][0]["id"], "p_forest")
        self.assertEqual(data["entity_map"][0]["places"][0]["npcs"][0]["affinity"], 0.8)
        self.assertEqual(data["loreblocks"]["active"][0]["id"], "lb_survive")
        self.assertEqual(data["notebook"][0]["id"], "lb_survive")
        self.assertEqual(len(data["conversations"]["npc_elf"]), 2)

        # Validación round-trip desde JSON
        json_str = gs.model_dump_json()
        gs_restored = GameState.model_validate_json(json_str)
        self.assertEqual(gs_restored.player_name, "Robin")
        self.assertEqual(gs_restored.gold, 15)
        self.assertEqual(gs_restored.entity_map[0].places[0].npcs[0].affinity, 0.8)


if __name__ == "__main__":
    unittest.main()
