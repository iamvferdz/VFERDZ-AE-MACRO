from unittest.mock import MagicMock

from core import runner as runner_module
from core.runner import MacroRunner


def _runner(task):
    runner = MacroRunner(MagicMock(), MagicMock(), MagicMock())
    runner._active_task = task
    runner._debug_save = MagicMock(return_value=None)
    return runner


def test_eclipse_prefers_configured_redeemed_soul_card(monkeypatch):
    modal = {"score": 0.88, "cx": 420, "cy": 300}
    monkeypatch.setattr(runner_module.vision, "find_image", lambda *_args, **_kwargs: modal)
    monkeypatch.setattr(runner_module.wm, "get_window_rect_screen", lambda _hwnd: (0, 0, 1152, 756))

    runner = _runner({
        "mode": "story",
        "story_event": "Eclipsed Infinite",
        "eclipse_soul": "Redeemed Soul",
    })
    assert runner._dismiss_reward_card_if_found(123)
    runner._mouse.click.assert_called_once_with(277, 392)


def test_eclipse_falls_back_when_preferred_card_is_not_found(monkeypatch):
    modal = {"score": 0.91, "cx": 576, "cy": 378}
    mouse = MagicMock()
    runner = MacroRunner(mouse, MagicMock(), MagicMock())
    runner._active_task = {
        "mode": "story",
        "story_event": "Eclipsed Infinite",
        "eclipse_soul": "Sacrificed Soul",
    }
    runner._debug_save = MagicMock(return_value=None)
    monkeypatch.setattr(runner_module.vision, "find_image", lambda *_args, **_kwargs: modal)
    monkeypatch.setattr(runner_module.wm, "get_window_rect_screen", lambda _hwnd: (0, 0, 1152, 756))

    assert runner._dismiss_reward_card_if_found(123)
    mouse.click.assert_called_once_with(576, 392)
