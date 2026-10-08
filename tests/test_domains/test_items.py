"""Pruebas unitarias para el modelo de Ítems (domains.items)."""

import unittest

from domains.items import Item


class TestItemModels(unittest.TestCase):
    """Pruebas del modelo Item y su ubicación inicial."""

    def test_item_creation(self):
        item = Item(
            id="obj_llave_hierro",
            name="Llave de Hierro",
            description="Una llave pesada y oxidada.",
            initial_location="Plaza Mayor"
        )
        self.assertEqual(item.id, "obj_llave_hierro")
        self.assertEqual(item.name, "Llave de Hierro")
        self.assertEqual(item.state, "default")
        self.assertEqual(item.initial_location, "Plaza Mayor")


if __name__ == "__main__":
    unittest.main()
