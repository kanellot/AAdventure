"""Pruebas unitarias para el modelo del Jugador (domains.player)."""

import unittest
from domains.player import Player


class TestPlayerModel(unittest.TestCase):
    """Pruebas del modelo Player, inventario, sincronización de ubicaciones y estado."""

    def test_player_defaults(self):
        player = Player(id="p1", name="Aventurero", description="Un valiente héroe.")
        self.assertEqual(player.id, "p1")
        self.assertEqual(player.name, "Aventurero")
        self.assertEqual(player.gold, 10)
        self.assertEqual(player.inventory, [])
        self.assertEqual(player.state, "EXPLORE")
        self.assertEqual(player.travel_speed, 4.5)

    def test_location_synchronization(self):
        # Si se especifica initial_place, player_location se sincroniza
        p1 = Player(id="p1", name="Héroe", description="Héroe", initial_place="Plaza Mayor")
        self.assertEqual(p1.initial_place, "Plaza Mayor")
        self.assertEqual(p1.player_location, "Plaza Mayor")

        # Si se especifica player_location, initial_place se sincroniza
        p2 = Player(id="p2", name="Héroe", description="Héroe", player_location="Taberna")
        self.assertEqual(p2.initial_place, "Taberna")
        self.assertEqual(p2.player_location, "Taberna")

    def test_active_block_synchronization(self):
        # Sincronización entre active_block y active_quest
        p1 = Player(id="p1", name="Héroe", description="Héroe", active_block="mision_01")
        self.assertEqual(p1.active_block, "mision_01")
        self.assertEqual(p1.active_quest, "mision_01")

        p2 = Player(id="p2", name="Héroe", description="Héroe", active_quest="mision_02")
        self.assertEqual(p2.active_block, "mision_02")
        self.assertEqual(p2.active_quest, "mision_02")


if __name__ == "__main__":
    unittest.main()
