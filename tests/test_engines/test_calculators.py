"""Pruebas unitarias para PathCalculator y TimeCalculator."""

import unittest
from domains.world import Place, Connection
from engines.game.utils import PathCalculator, TimeCalculator


class TestCalculators(unittest.TestCase):
    """Verifica el cálculo de rutas mínimas y progresión del tiempo."""

    def setUp(self):
        # Configuración de grafo espacial para pruebas:
        # p1 --(150m, village)--> p2 --(250m, road)--> p3 --(120m, village)--> p4
        # p1 --(600m, mountain)--> p4
        self.places = {
            "Plaza Mayor": Place(
                id="p_01",
                name="Plaza Mayor",
                description="Una plaza concurrida.",
                connections={
                    "norte": Connection(target="Calle Pobre", distance=150, terrain_type="village"),
                    "este": Connection(target="Taberna", distance=600, terrain_type="mountain"),
                },
            ),
            "Calle Pobre": Place(
                id="p_02",
                name="Calle Pobre",
                description="Una calle modesta.",
                connections={
                    "sur": Connection(target="Plaza Mayor", distance=150, terrain_type="village"),
                    "norte": Connection(target="Plaza Menor", distance=250, terrain_type="road"),
                },
            ),
            "Plaza Menor": Place(
                id="p_03",
                name="Plaza Menor",
                description="Una plazoleta con fuente.",
                connections={
                    "sur": Connection(target="Calle Pobre", distance=250, terrain_type="road"),
                    "este": Connection(target="Taberna", distance=120, terrain_type="village"),
                },
            ),
            "Taberna": Place(
                id="p_04",
                name="Taberna",
                description="Una taberna acogedora.",
                connections={
                    "oeste": Connection(target="Plaza Menor", distance=120, terrain_type="village"),
                    "oeste_lejos": Connection(target="Plaza Mayor", distance=600, terrain_type="mountain"),
                },
            ),
        }

    def test_find_shortest_path_by_name(self):
        conns, full_path = PathCalculator.find_shortest_path(self.places, "Plaza Mayor", "Taberna")
        self.assertEqual(len(conns), 3)
        self.assertEqual([p.name for p in full_path], ["Plaza Mayor", "Calle Pobre", "Plaza Menor", "Taberna"])

    def test_find_intermediate_places(self):
        intermediate = PathCalculator.find_intermediate_places(self.places, "Plaza Mayor", "Taberna")
        self.assertEqual([p.name for p in intermediate], ["Calle Pobre", "Plaza Menor"])

    def test_path_resolution_by_id(self):
        conns_id, full_id = PathCalculator.find_shortest_path(self.places, "p_01", "p_04")
        self.assertEqual(len(conns_id), 3)
        self.assertEqual(full_id[-1].name, "Taberna")

    def test_same_origin_and_destination(self):
        conns, full_path = PathCalculator.find_shortest_path(self.places, "Plaza Mayor", "Plaza Mayor")
        self.assertEqual(len(conns), 0)
        self.assertEqual(len(full_path), 1)
        self.assertEqual(PathCalculator.find_intermediate_places(self.places, "Plaza Mayor", "Plaza Mayor"), [])

    def test_time_calculator_travel_time(self):
        conns, _ = PathCalculator.find_shortest_path(self.places, "Plaza Mayor", "Taberna")
        travel_time = TimeCalculator.calculate_travel_time(conns, travel_speed=4.5)
        self.assertEqual(travel_time, 7)

    def test_time_calculator_between_places(self):
        time_between = TimeCalculator.calculate_travel_time_between_places(
            self.places, "Plaza Mayor", "Taberna", travel_speed=4.5
        )
        self.assertEqual(time_between, 7)

    def test_time_calculator_dialogue(self):
        self.assertEqual(TimeCalculator.calculate_dialogue_time(), 1)
        self.assertEqual(TimeCalculator.calculate_dialogue_time(turns=4), 4)

    def test_time_calculator_formatting(self):
        self.assertEqual(TimeCalculator.format_elapsed_time(0), "Día 0, 00:00")
        self.assertEqual(TimeCalculator.format_elapsed_time(75), "Día 0, 01:15")
        self.assertEqual(TimeCalculator.format_elapsed_time(1500), "Día 1, 01:00")


if __name__ == "__main__":
    unittest.main()
