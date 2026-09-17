"""Pruebas unitarias para el modelo de Objetos/Items (domains.items)."""

import unittest
from domains.items import Item, GameObject


class TestItemModels(unittest.TestCase):
    """Pruebas del modelo Item y GameObject."""

    def test_item_creation(self):
        item = Item(
            id="obj_llave_hierro",
            name="Llave de Hierro",
            description="Una llave pesada y oxidada.",
            initial_place="Plaza Mayor"
        )
        self.assertEqual(item.id, "obj_llave_hierro")
        self.assertEqual(item.name, "Llave de Hierro")
        self.assertEqual(item.state, "default")
        self.assertEqual(item.initial_place, "Plaza Mayor")

    def test_game_object_alias(self):
        self.assertIs(GameObject, Item)
        obj = GameObject(id="obj_espada", name="Espada Corta", description="Una espada afilada.")
        self.assertEqual(obj.id, "obj_espada")


if __name__ == "__main__":
    unittest.main()
