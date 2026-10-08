"""Pruebas unitarias para el nuevo GameStateController."""

import os
import shutil
import tempfile
import unittest

from domains.game_state import LoreBlockHierarchy
from domains.items import Item
from domains.npcs import NPC
from domains.player import Player
from domains.world import Connection, Location, Place, World
from engines.game.state_controller import GameStateController


class TestGameStateController(unittest.TestCase):
    """Pruebas exhaustivas para el nuevo GameStateController."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

        # Configuración de Mundo: 1 Localización con 3 Lugares
        # P1 (Plaza) conectado a P2 (Taberna)
        # P2 conectado a P3 (Bosque profundo)
        self.p1 = Place(
            id="p1",
            name="Plaza Mayor",
            description="La plaza central del pueblo.",
            connections={"p2": Connection(target="p2", distance=100, terrain_type="village")},
        )
        self.p2 = Place(
            id="p2",
            name="Taberna",
            description="Una taberna acogedora.",
            connections={
                "p1": Connection(target="p1", distance=100, terrain_type="village"),
                "p3": Connection(target="p3", distance=500, terrain_type="forest"),
            },
        )
        self.p3 = Place(
            id="p3",
            name="Bosque Profundo",
            description="Un bosque oscuro y peligroso.",
            connections={"p2": Connection(target="p2", distance=500, terrain_type="forest")},
        )

        self.loc = Location(id="loc1", name="Aldea", description="Una aldea tranquila",
                            places=[self.p1, self.p2, self.p3])
        self.world = World(id="w1", name="Mundo", description="Un mundo fantástico", locations=[self.loc])

        self.player = Player(
            id="player1",
            name="Héroe",
            description="El protagonista",
            gold=30,
            inventory=["item_dagger"],
            initial_location="p1",
        )

        self.npc1 = NPC(id="npc_tom", name="Tom", description="Un aldeano amistoso", initial_location="p1")
        self.npc2 = NPC(id="npc_bartender", name="Tabernero", description="El dueño de la taberna",
                        initial_location="p2")

        self.item1 = Item(id="item_apple", name="Manzana", description="Fruta roja", initial_location="p1")
        self.item2 = Item(id="item_ale", name="Cerveza", description="Bebida espumosa", initial_location="p2")

        self.hierarchy = LoreBlockHierarchy(
            active=[
                {"id": "q1", "name": "Misión 1", "type": "Quest", "description": "Salva la aldea"},
                {"id": "t1", "name": "Tarea 1", "type": "Task"},
            ],
            done=[],
            unknown=[],
        )

        self.controller = GameStateController.create_initial(
            world=self.world,
            player=self.player,
            npcs=[self.npc1, self.npc2],
            items=[self.item1, self.item2],
            loreblocks_hierarchy=self.hierarchy,
            adventure_path=self.temp_dir,
            elapsed_time_enabled=True,
        )

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_initial_state(self):
        """Verifica la inicialización correcta del estado y la niebla de guerra (Opción B)."""
        gs = self.controller.game_state
        self.assertEqual(gs.player_name, "Héroe")
        self.assertEqual(gs.player_state, "EXPLORE")
        self.assertIsNone(gs.player_target)
        self.assertEqual(gs.current_location, "p1")
        self.assertEqual(gs.gold, 30)
        self.assertEqual(gs.inventory.items, ["item_dagger"])
        self.assertEqual(gs.current_time, "Día 1, 08:00")
        self.assertIsNotNone(gs.place)
        self.assertEqual(gs.place.id, "p1")

        # Niebla de guerra: P1 visited, P2 visible, P3 hidden
        places_map = {p.id: p for p in gs.entity_map[0].places}
        self.assertEqual(places_map["p1"].status, "visited")
        self.assertEqual(places_map["p2"].status, "visible")
        self.assertEqual(places_map["p3"].status, "hidden")

        # Entidades en P1 visibles
        self.assertTrue(places_map["p1"].items[0].visible)
        self.assertEqual(places_map["p1"].items[0].id, "item_apple")

        # Notebook contiene la Quest y Task activas iniciales
        self.assertEqual(len(gs.notebook), 2)
        self.assertEqual(gs.notebook[0].id, "q1")
        self.assertEqual(gs.notebook[0].status, "active")
        self.assertEqual(gs.notebook[1].id, "t1")
        self.assertEqual(gs.notebook[1].status, "active")

    def test_movement_and_fog_war_progression(self):
        """Verifica la actualización de posición y progresión de niebla de guerra."""
        self.controller.set_current_location("p2")
        gs = self.controller.game_state
        self.assertEqual(gs.current_location, "p2")
        self.assertEqual(gs.place.id, "p2")

        places_map = {p.id: p for p in gs.entity_map[0].places}
        self.assertEqual(places_map["p1"].status, "visited")
        self.assertEqual(places_map["p2"].status, "visited")
        # P3 ahora está conectado a P2, por lo que pasa de hidden a visible
        self.assertEqual(places_map["p3"].status, "visible")

    def test_inventory_and_gold_mutations(self):
        """Verifica mutaciones de inventario y oro."""
        self.controller.add_to_inventory("item_apple")
        self.assertIn("item_apple", self.controller.game_state.inventory)

        # El ítem recogido se retira del lugar
        places_map = {p.id: p for p in self.controller.game_state.entity_map[0].places}
        item_ids = [it.id for it in places_map["p1"].items]
        self.assertNotIn("item_apple", item_ids)

        self.controller.remove_from_inventory("item_dagger")
        self.assertNotIn("item_dagger", self.controller.game_state.inventory)

        self.controller.add_gold(20)
        self.assertEqual(self.controller.game_state.gold, 50)

        self.controller.remove_gold(15)
        self.assertEqual(self.controller.game_state.gold, 35)

        # No permite oro negativo
        self.controller.remove_gold(100)
        self.assertEqual(self.controller.game_state.gold, 0)

    def test_blocking_places(self):
        """Verifica bloqueo y desbloqueo de lugares."""
        self.assertFalse(self.controller.is_place_blocked("p2"))
        self.controller.block_place("p2")
        self.assertTrue(self.controller.is_place_blocked("p2"))

        self.controller.unblock_place("p2")
        self.assertFalse(self.controller.is_place_blocked("p2"))

    def test_affinity_and_conversation_history(self):
        """Verifica afinidad de NPCs e historial de diálogos con límite deslizante."""
        self.assertEqual(self.controller.get_npc_affinity("npc_tom"), 0.5)
        self.controller.update_npc_affinity("npc_tom", 0.85)
        self.assertEqual(self.controller.get_npc_affinity("npc_tom"), 0.85)

        # Registro de diálogo
        self.controller.append_dialogue_exchange(
            target_id="npc_tom",
            player_msg="Hola Tom",
            npc_name="Tom",
            npc_msg="Saludos viajero",
            max_messages=4,
        )
        conv = self.controller.get_conversation("npc_tom")
        self.assertEqual(len(conv), 2)
        self.assertEqual(conv[0]["player"], "Hola Tom")
        self.assertEqual(conv[1]["Tom"], "Saludos viajero")

        # Verificación de límite de ventana deslizante
        self.controller.append_dialogue_exchange(
            target_id="npc_tom",
            player_msg="¿Qué hay de nuevo?",
            npc_name="Tom",
            npc_msg="Nada nuevo hoy.",
            max_messages=4,
        )
        self.assertEqual(len(self.controller.get_conversation("npc_tom")), 4)

        # Quinto y sexto mensaje provocan descarte de los más antiguos
        self.controller.append_dialogue_exchange(
            target_id="npc_tom",
            player_msg="Adiós",
            npc_name="Tom",
            npc_msg="Hasta pronto",
            max_messages=4,
        )
        conv_pruned = self.controller.get_conversation("npc_tom")
        self.assertEqual(len(conv_pruned), 4)
        self.assertEqual(conv_pruned[-1]["Tom"], "Hasta pronto")

    def test_time_advancement(self):
        """Verifica el cálculo de tiempo transcurrido en minutos."""
        self.controller.add_elapsed_minutes(45)
        self.assertEqual(self.controller.game_state.current_time, "Día 1, 08:45")

        self.controller.add_elapsed_minutes(75)  # 1 hora y 15 minutos -> 10:00
        self.assertEqual(self.controller.game_state.current_time, "Día 1, 10:00")

    def test_persistence_save_and_load(self):
        """Verifica guardado y carga canónica sin pérdida de estado."""
        save_file = self.controller.save()
        self.assertTrue(os.path.exists(save_file))

        # Modificamos el estado en memoria
        self.controller.set_player_state("TALK")
        self.controller.set_player_target("npc_tom")
        self.controller.add_gold(100)

        # Cargamos el archivo previamente guardado
        loaded_state = self.controller.load(save_file)
        self.assertEqual(loaded_state.player_state, "EXPLORE")
        self.assertIsNone(loaded_state.player_target)
        self.assertEqual(loaded_state.gold, 30)
        self.assertEqual(self.controller.game_state.place.id, "p1")


if __name__ == "__main__":
    unittest.main()
