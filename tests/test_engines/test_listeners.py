"""Pruebas unitarias para el módulo de listeners de engines."""

import unittest
from domains.projections import TurnResultProjection, UIStateProjection
from engines.events import ThinkingEvent
from engines.listeners import (
    BaseEngineEventListener,
    EngineEventListener,
    SyncCollectingEventListener,
)


class DummyListener(BaseEngineEventListener):
    pass


class TestListeners(unittest.TestCase):
    """Verifica el protocolo EngineEventListener y SyncCollectingEventListener."""

    def test_protocol_runtime_checkable(self):
        collector = SyncCollectingEventListener()
        self.assertTrue(isinstance(collector, EngineEventListener))

        dummy = DummyListener()
        self.assertTrue(isinstance(dummy, EngineEventListener))

    def test_sync_collecting_event_listener_lifecycle(self):
        listener = SyncCollectingEventListener()

        # 1. on_thinking_changed(True)
        evt_start = ThinkingEvent(task_id="t1", is_thinking=True, action="MOVE", target="Plaza")
        listener.on_thinking_changed(evt_start.model_dump_json())
        self.assertEqual(len(listener.thinking_events), 1)
        self.assertIsInstance(listener.thinking_events[0], str)

        # 2. on_task_completed
        res = TurnResultProjection(author="DM", msg="Llegaste.")
        listener.on_task_completed("t1", res.model_dump_json())
        self.assertEqual(len(listener.completed_tasks), 1)
        self.assertEqual(listener.last_task_id, "t1")
        self.assertEqual(listener.completed_tasks[0], ("t1", res.model_dump_json()))

        # 3. on_state_updated
        state = UIStateProjection(player_name="Hero", gold=100, current_location="Plaza", formatted_time="12:00", game_state="EXPLORE")
        listener.on_state_updated(state.model_dump_json())
        self.assertEqual(len(listener.state_updates), 1)
        self.assertEqual(listener.state_updates[0], state.model_dump_json())

        # 4. on_thinking_changed(False)
        evt_end = ThinkingEvent(task_id="t1", is_thinking=False)
        listener.on_thinking_changed(evt_end.model_dump_json())

        # 5. wait_for_completion debe retornar True de inmediato
        self.assertTrue(listener.wait_for_completion(timeout=0.1))

        # 6. reset_events
        listener.reset_events()
        self.assertEqual(len(listener.thinking_events), 0)
        self.assertEqual(len(listener.completed_tasks), 0)
        self.assertEqual(len(listener.state_updates), 0)

    def test_sync_collecting_event_listener_error(self):
        listener = SyncCollectingEventListener()
        listener.on_error("t_err", "Error de prueba", "TestError")
        self.assertEqual(len(listener.errors), 1)
        self.assertEqual(listener.errors[0], ("t_err", "Error de prueba", "TestError"))


if __name__ == "__main__":
    unittest.main()
