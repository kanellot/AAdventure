"""Pruebas unitarias para modelos de Personajes No Jugadores (domains.npcs)."""

import unittest
from domains.npcs import NPC, NPCMotivations
from domains.conversation import ConversationRecord


class TestNPCModels(unittest.TestCase):
    """Pruebas de modelos de NPC, motivaciones y conversaciones."""

    def test_npc_defaults_and_affinities(self):
        npc = NPC(
            id="npc_tabernero",
            name="Goran",
            description="El tabernero local.",
            occupation="Tabernero",
            initial_place="Taberna",
            affinity=0.6,
        )
        self.assertEqual(npc.id, "npc_tabernero")
        self.assertEqual(npc.name, "Goran")
        self.assertEqual(npc.affinity, 0.6)
        self.assertEqual(npc.initial_place, "Taberna")
        self.assertIsNotNone(npc.motivations)
        self.assertEqual(npc.motivations.likes, [])
        self.assertEqual(npc.motivations.dislikes, [])

    def test_npc_motivations(self):
        motivations = NPCMotivations(
            likes=["cerveza", "historias de viajes"],
            dislikes=["peleas", "clientes ruidosos"]
        )
        npc = NPC(
            id="npc_tabernero",
            name="Goran",
            description="Tabernero",
            motivations=motivations,
        )
        self.assertIn("cerveza", npc.motivations.likes)
        self.assertIn("peleas", npc.motivations.dislikes)

    def test_conversation_record(self):
        record = ConversationRecord(id="conv_01")
        self.assertEqual(len(record.msg), 0)

        record.msg.append({"Player": "Hola, ¿cómo estás?"})
        record.msg.append({"Npc": "Bienvenido a mi posada."})
        self.assertEqual(len(record.msg), 2)
        self.assertEqual(record.msg[0]["Player"], "Hola, ¿cómo estás?")
        self.assertEqual(record.msg[1]["Npc"], "Bienvenido a mi posada.")


if __name__ == "__main__":
    unittest.main()
