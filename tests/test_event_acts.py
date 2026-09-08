import threading

import core.runner as runner_module
from core.runner import MacroRunner
from core import runner_constants as rc


def test_summer_modes_and_portals_are_mapped():
    assert set(runner_module.SUMMER_MODE_ORDER) == set(runner_module.SUMMER_MODE_IMAGES)
    assert runner_module.SUMMER_PORTAL_IMAGES[("Summer Portal", "1")] == ("summer_portal_tier_1",)
    assert runner_module.SUMMER_PORTAL_IMAGES[("Sky Ruins Portal", "5")] == ("sky_ruins_portal_tier_5",)
    assert runner_module.SUMMER_PORTAL_IMAGES[("Summer Portal", "Secret")] == ("sovereigns_portal",)
    assert runner_module.SUMMER_PORTAL_IMAGES[("Sky Ruins Portal", "Secret")] == ("lightning_gods_portal",)

def test_reach_summer_selection_uses_tidal_siege_act(monkeypatch):
    runner = object.__new__(MacroRunner)
    clicked = []
    runner._ensure_lobby = lambda hwnd, stop_event: True
    runner._checkpoint = lambda stop_event: False
    runner._set_status = lambda **kwargs: None
    runner._spam_back_until_gone = lambda hwnd, stop_event: None
    runner._click_found_image = lambda hwnd, name, timeout, stop_event: clicked.append(name) or {"score": 0.99}
    runner._click_found_color_image = runner._click_found_image
    monkeypatch.setattr(runner_module.time, "sleep", lambda seconds: None)

    assert runner._reach_summer_selection(
        123, threading.Event(), {"summer_mode": "Event Mode", "map": "Summer"}
    ) is True
    assert clicked == [
        "nav_event", "summer_tidal_siege", "event_gamemode",
        "summer_event_mode",
    ]


def test_reach_summer_selection_uses_selected_portal(monkeypatch):
    runner = object.__new__(MacroRunner)
    clicked = []
    runner._ensure_lobby = lambda hwnd, stop_event: True
    runner._checkpoint = lambda stop_event: False
    runner._set_status = lambda **kwargs: None
    runner._spam_back_until_gone = lambda hwnd, stop_event: None
    runner._click_found_image = lambda hwnd, name, timeout, stop_event: clicked.append(name) or {"score": 0.99}
    runner._click_found_color_image = runner._click_found_image
    monkeypatch.setattr(runner_module.time, "sleep", lambda seconds: None)

    assert runner._reach_summer_selection(
        123, threading.Event(), {
            "summer_mode": "Portal Mode", "map": "Sky Ruins Portal", "portal_tier": "3"
        }
    ) is True
    assert clicked == [
        "nav_event", "summer_tidal_siege", "event_gamemode",
        "summer_portal_mode", "sky_ruins_portal_tier_3",
        "activate_portal",
    ]


def test_reach_summer_selection_uses_secret_portal_image(monkeypatch):
    runner = object.__new__(MacroRunner)
    clicked = []
    runner._ensure_lobby = lambda hwnd, stop_event: True
    runner._checkpoint = lambda stop_event: False
    runner._set_status = lambda **kwargs: None
    runner._spam_back_until_gone = lambda hwnd, stop_event: None
    runner._click_found_image = lambda hwnd, name, timeout, stop_event: clicked.append(name) or {"score": 0.99}
    runner._click_found_color_image = runner._click_found_image
    monkeypatch.setattr(runner_module.time, "sleep", lambda seconds: None)

    assert runner._reach_summer_selection(
        123, threading.Event(), {
            "summer_mode": "Portal Mode",
            "map": "Summer Portal",
            "portal_tier": "Secret",
        }
    ) is True
    assert clicked[-2:] == ["sovereigns_portal", "activate_portal"]


def test_summer_portal_result_selects_middle_card(monkeypatch):
    runner = object.__new__(MacroRunner)
    runner._set_status = lambda **kwargs: None
    runner._log = lambda message: None
    runner._checkpoint = lambda stop_event: False
    state = {"clicks": 0}
    monkeypatch.setattr(
        runner_module.vision, "find_image",
        lambda hwnd, name: (
            {"score": 0.99}
            if name == "portal_reward_screen" and state["clicks"] < 3
            else {"score": 0.99}
            if name == "select_portal" and state["clicks"] >= 3
            else None
        ),
    )
    runner._interruptible_sleep = lambda seconds, stop_event: None
    runner._mouse = type("Mouse", (), {
        "click": lambda self, x, y: (clicked.append((x, y)), state.__setitem__("clicks", state["clicks"] + 1)),
        "move_to": lambda self, x, y: None,
    })()
    monkeypatch.setattr(runner_module.vision, "capture_game_bgr", lambda hwnd, region: object())
    monkeypatch.setattr(runner_module.ocr_windows, "ocr_image", lambda frame: "Tier 2 Sky Ruins Portal")
    monkeypatch.setattr(runner_module.ocr_windows, "ocr_lines", lambda frame: [
        {"text": "Tier 2", "cx": 200, "cy": 15},
        {"text": "Sky Ruins Portal", "cx": 200, "cy": 75},
    ])
    clicked = []
    monkeypatch.setattr(runner_module.vision, "ref_to_screen", lambda hwnd, x, y: (x, y))

    assert runner._select_summer_portal_card(
        123, threading.Event(), {"map": "Sky Ruins Portal", "portal_tier": "2"}
    ) is True
    assert clicked == [(460, 360), (460, 360), (460, 360)]


def test_summer_portal_result_clicks_middle_detected_portal_image(monkeypatch):
    runner = object.__new__(MacroRunner)
    clicked = []
    state = {"clicks": 0}
    runner._set_status = lambda **kwargs: None
    runner._log = lambda message: None
    runner._checkpoint = lambda stop_event: False
    runner._interruptible_sleep = lambda seconds, stop_event: None
    runner._mouse = type("Mouse", (), {
        "click": lambda self, x, y: clicked.append((x, y)),
        "move_to": lambda self, x, y: None,
    })()
    monkeypatch.setattr(
        runner_module.vision, "find_image",
        lambda hwnd, name: (
            {"score": 0.99}
            if name == "portal_reward_screen" and state["clicks"] < 3
            else {"score": 0.99}
            if name == "select_portal" and state["clicks"] >= 3
            else None
        ),
    )
    monkeypatch.setattr(runner_module.vision, "ref_to_screen", lambda hwnd, x, y: (x, y))
    monkeypatch.setattr(runner_module.wm, "activate_window", lambda hwnd: True)
    runner._mouse.click = lambda x, y: (clicked.append((x, y)), state.__setitem__("clicks", state["clicks"] + 1))

    assert runner._select_summer_portal_card(
        123, threading.Event(), {"map": "Sky Ruins Portal", "portal_tier": "5"}
    ) is True
    assert clicked == [(460, 360), (460, 360), (460, 360)]


def test_summer_portal_ocr_cannot_trigger_during_battle(monkeypatch):
    runner = object.__new__(MacroRunner)
    runner._log = lambda message: None
    monkeypatch.setattr(runner_module.vision, "find_image", lambda hwnd, name: None)
    monkeypatch.setattr(runner_module.ocr_windows, "ocr_image", lambda frame: (
        "Tier 3 Sky Ruins Portal Unit Manager Stage Info"
    ))

    assert runner._select_summer_portal_card(
        123, threading.Event(), {"map": "Sky Ruins Portal", "portal_tier": "3"}
    ) is False


def test_summer_portal_repeat_selects_configured_portal(monkeypatch):
    runner = object.__new__(MacroRunner)
    clicked = []
    runner._set_status = lambda **kwargs: None
    runner._log = lambda message: None
    runner._checkpoint = lambda stop_event: False
    runner._click_found_image = (
        lambda hwnd, name, timeout, stop_event, **kwargs: clicked.append(name) or {"score": 0.99}
    )
    runner._click_found_color_image = (
        lambda hwnd, name, timeout, stop_event, **kwargs: clicked.append(name) or {"score": 0.99}
    )
    runner._select_summer_portal_from_grid = (
        lambda hwnd, stop_event, portal, tier: clicked.append("sovereigns_portal") or True
    )
    monkeypatch.setattr(runner_module.time, "sleep", lambda seconds: None)

    assert runner._select_summer_portal_for_repeat(
        123, threading.Event(), {
            "map": "Summer Portal", "portal_tier": "Secret",
        }
    ) is True
    assert clicked == ["select_portal", "sovereigns_portal", "portal_selection_select", "nav_start_game"]


def test_all_portal_families_use_configured_repeat_selection(monkeypatch):
    for portal, tier, expected_image in (
        ("Summer Portal", "5", "summer_portal_tier_5"),
        ("Sky Ruins Portal", "5", "sky_ruins_portal_tier_5"),
        ("Sky Ruins Portal", "Secret", "lightning_gods_portal"),
    ):
        runner = object.__new__(MacroRunner)
        clicked = []
        runner._set_status = lambda **kwargs: None
        runner._log = lambda message: None
        runner._checkpoint = lambda stop_event: False
        runner._click_found_image = (
            lambda hwnd, name, timeout, stop_event, **kwargs:
            clicked.append(name) or {"score": 0.99}
        )
        runner._select_summer_portal_from_grid = (
            lambda hwnd, stop_event, selected_portal, selected_tier:
            clicked.append(runner_module.SUMMER_PORTAL_IMAGES[(selected_portal, selected_tier)][0]) or True
        )
        assert runner._select_summer_portal_for_repeat(
            123, threading.Event(), {"map": portal, "portal_tier": tier}
        ) is True
        assert clicked == [
            "select_portal", expected_image,
            "portal_selection_select", "nav_start_game",
        ]


def test_repeat_portal_selection_uses_full_screen_matcher(monkeypatch):
    runner = object.__new__(MacroRunner)
    calls = []
    runner._set_status = lambda **kwargs: None
    runner._log = lambda message: None
    runner._checkpoint = lambda stop_event: False
    runner._click_found_image = (
        lambda hwnd, name, timeout, stop_event, **kwargs:
        calls.append((name, kwargs)) or {"score": 0.99}
    )
    runner._select_summer_portal_from_grid = (
        lambda hwnd, stop_event, portal, tier: True
    )
    assert runner._select_summer_portal_for_repeat(
        123, threading.Event(), {"map": "Sky Ruins Portal", "portal_tier": "5"}
    ) is True
    assert calls[0] == ("select_portal", {})


def test_portal_result_button_is_a_victory_signal(monkeypatch):
    runner = object.__new__(MacroRunner)
    runner._checkpoint = lambda stop_event: False
    runner._set_status = lambda **kwargs: None
    runner._log = lambda message: None
    runner._run_battle_blocks_tick = lambda *args: None
    runner._tick_loop_phases = lambda *args: None
    runner._select_summer_portal_card = lambda *args: False
    runner._handle_disconnect = lambda *args: None
    runner._expedition_checkpoint_stalled = lambda: False
    runner._expedition_intercepts_stalled = lambda: False
    runner._save_debug_screenshot_unconditional = lambda *args: None
    runner._dismiss_reward_card_if_found = lambda *args: False
    runner._clear_result_obtainment_modal = lambda *args: True
    runner._battle_leave_requested = False
    monkeypatch.setattr(runner_module.vision, "find_image", lambda hwnd, name, **kwargs: (
        {"score": 1.0} if name == "select_portal" else None
    ))

    assert runner._wait_for_match_result(
        123,
        threading.Event(),
        task={"mode": "summer", "summer_mode": "Portal Mode"},
    ) == "win"
