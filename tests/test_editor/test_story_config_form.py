"""Pruebas unitarias para StoryConfigForm (editor.views.story_config_form)."""

import unittest
from PySide6.QtWidgets import QApplication
from editor.views.story_config_form import StoryConfigForm
from domains.story_config import StoryConfig


class TestStoryConfigForm(unittest.TestCase):
    """Verifica el enlace bidireccional y controles de StoryConfigForm."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(["test", "-platform", "offscreen"])

    def setUp(self):
        self.form = StoryConfigForm()

    def test_initial_state(self):
        self.assertTrue(self.form.elapsed_time_cb.isChecked())
        self.assertTrue(self.form.fog_war_cb.isChecked())
        self.assertTrue(self.form.affinity_cb.isChecked())

    def test_set_config(self):
        cfg = StoryConfig(elapsed_time=False, fog_war=True, affinity=False)
        self.form.set_config(cfg)
        self.assertFalse(self.form.elapsed_time_cb.isChecked())
        self.assertTrue(self.form.fog_war_cb.isChecked())
        self.assertFalse(self.form.affinity_cb.isChecked())

    def test_toggle_affinity_checkbox(self):
        cfg = StoryConfig(elapsed_time=True, fog_war=True, affinity=True)
        self.form.set_config(cfg)

        # Desmarcar checkbox
        self.form.affinity_cb.setChecked(False)
        self.assertFalse(self.form.config.affinity)

        # Marcar checkbox
        self.form.affinity_cb.setChecked(True)
        self.assertTrue(self.form.config.affinity)


if __name__ == "__main__":
    unittest.main()
