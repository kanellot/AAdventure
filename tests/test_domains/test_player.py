"""Pruebas unitarias para el modelo del Jugador (domains.player)."""

import unittest

from domains.player import Player


class TestPlayerModel(unittest.TestCase):
    """Pruebas del modelo Player, inventario, ubicación inicial y estado."""

    def test_player_defaults(self):
        player = Player(id="p1", name="Aventurero", description="Un valiente héroe.")
        self.assertEqual(player.id, "p1")
        self.assertEqual(player.name, "Aventurero")
        self.assertEqual(player.gold, 10)
        self.assertEqual(player.inventory, [])
        self.assertEqual(player.state, "EXPLORE")
        self.assertEqual(player.travel_speed, 4.5)
        self.assertEqual(player.initial_location, "")

    def test_player_initial_location(self):
        p1 = Player(id="p1", name="Héroe", description="Héroe", initial_location="Plaza Mayor")
        self.assertEqual(p1.initial_location, "Plaza Mayor")

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
