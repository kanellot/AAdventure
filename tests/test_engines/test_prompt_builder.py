"""Pruebas unitarias para PromptBuilder."""

import unittest
import os
import tempfile
from pydantic import BaseModel
from engines.game.prompt_builder import PromptBuilder


class DummyContext(BaseModel):
    state: str = "exploring"


class TestPromptBuilder(unittest.TestCase):
    """Verifica el ensamblado e inyección de contexto y reglas en el prompt."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_missing_rules_file_raises(self):
        with self.assertRaises(FileNotFoundError):
            PromptBuilder.build(
                rules_path="non_existent_rules.txt",
                gamecontext=DummyContext(),
                game_context_str="{}",
                user_input="hola",
            )

    def test_build_with_template_tags(self):
        rules_path = os.path.join(self.temp_dir.name, "rules_tags.txt")
        with open(rules_path, "w", encoding="utf-8") as f:
            f.write("Reglas base. <role_directive> Jugador: <player_input>")

        prompt = PromptBuilder.build(
            rules_path=rules_path,
            gamecontext=DummyContext(),
            game_context_str="{}",
            user_input="mirar alrededor",
            template_tags={"role_directive": "Se breve."},
        )

        self.assertIn("Se breve.", prompt)
        self.assertIn("mirar alrededor", prompt)
        self.assertNotIn("<role_directive>", prompt)
        self.assertNotIn("<player_input>", prompt)

    def test_build_with_mustache_tags(self):
        rules_path = os.path.join(self.temp_dir.name, "rules_mustache.txt")
        with open(rules_path, "w", encoding="utf-8") as f:
            f.write("Contexto: {{context_json}}\nComando: {{player_input}}")

        prompt = PromptBuilder.build(
            rules_path=rules_path,
            gamecontext=DummyContext(),
            game_context_str='{"place": "Taberna"}',
            user_input="pedir sidra",
        )

        self.assertIn('{"place": "Taberna"}', prompt)
        self.assertIn("pedir sidra", prompt)

    def test_build_default_fallback_formatting(self):
        rules_path = os.path.join(self.temp_dir.name, "rules_plain.txt")
        with open(rules_path, "w", encoding="utf-8") as f:
            f.write("Eres el narrador.")

        prompt = PromptBuilder.build(
            rules_path=rules_path,
            gamecontext=DummyContext(),
            game_context_str="Estado: OK",
            user_input="examinar cofre",
        )

        self.assertIn("# REGLAS E INSTRUCCIONES DEL ROL", prompt)
        self.assertIn("# CONTEXTO DEL JUEGO (ESTADO ACTUAL)", prompt)
        self.assertIn("examinar cofre", prompt)


if __name__ == "__main__":
    unittest.main()
