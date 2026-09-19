"""Pruebas unitarias para el modelo StoryConfig (domains.story_config)."""

import unittest
from domains.story_config import StoryConfig


class TestStoryConfigModel(unittest.TestCase):
    """Pruebas de validación, valores por defecto y serialización de StoryConfig."""

    def test_default_values(self):
        cfg = StoryConfig()
        self.assertTrue(cfg.elapsed_time)
        self.assertTrue(cfg.fog_war)
        self.assertTrue(cfg.affinity)

    def test_custom_values(self):
        cfg = StoryConfig(elapsed_time=False, fog_war=False, affinity=False)
        self.assertFalse(cfg.elapsed_time)
        self.assertFalse(cfg.fog_war)
        self.assertFalse(cfg.affinity)

    def test_backward_compatibility_without_affinity_key(self):
        data = {"elapsed_time": True, "fog_war": True}
        cfg = StoryConfig.model_validate(data)
        self.assertTrue(cfg.affinity)

    def test_serialization(self):
        cfg = StoryConfig(elapsed_time=False, fog_war=True, affinity=False)
        dumped = cfg.model_dump()
        self.assertEqual(dumped, {"elapsed_time": False, "fog_war": True, "affinity": False})


if __name__ == "__main__":
    unittest.main()
