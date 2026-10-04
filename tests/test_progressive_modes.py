import re
import threading
from pathlib import Path

import pytest

from core import runner as runner_module
from core import runner_blocks
from core import stage_select
from core import templates as template_module
from core.runner import MacroRunner
from core.runner_constants import STORY_EVENT_STAGE_IMAGES

REPO = Path(__file__).resolve().parent.parent


def test_infernal_cult_story_references_are_registered():
    assert stage_select.STORY_EVENT_IMAGES["Infernal Cult"] == "story_infernal_cult"
    assert STORY_EVENT_STAGE_IMAGES["Infernal Cult"] == "story_infernal_cult_stage"
    for name in ("story_infernal_cult", "story_infernal_cult_stage"):
        assert list((REPO / "Assets" / "ui" / name).glob("*.png"))

    app_js = (REPO / "ui" / "app.js").read_text(encoding="utf-8")
    story_data = re.search(r"story:\s*\{.*?events:\s*\[(.*?)\]", app_js, re.S)
    assert story_data
    assert "Infernal Cult" in story_data.group(1)


def test_boss_rush_task_data_offers_district_7_without_a_stage_picker():
    app_js = (REPO / "ui" / "app.js").read_text(encoding="utf-8")
    boss_rush_data = re.search(r"boss_rush:\s*\{(.*?)\n  \}", app_js, re.S)
    assert boss_rush_data
    assert "'District 7'" in boss_rush_data.group(1)
    assert "stages:" not in boss_rush_data.group(1)
    builder = re.search(r"function renderTaskBuilder\(\).*?\nfunction ", app_js, re.S)
    assert builder
    assert "if (t.mode !== 'boss_rush')" in builder.group(0)
    assert "boss_rush_gates" in builder.group(0)
    assert "boss_rush_card" in builder.group(0)
    assert "boss_rush_boss_macro" in builder.group(0)
    assert all(name in app_js for name in (
        "boss_rush_pick_card", "boss_rush_continue", "boss_rush_fight_boss",
    ))
    resource_html = (REPO / "ui" / "index.html").read_text(encoding="utf-8")
    assert 'id="boss-rush-path-list"' in resource_html
    assert all(f"boss_rush_card_{side}" in resource_html for side in ("left", "middle", "right"))
    assert list((REPO / "Assets" / "ui" / "boss_rush").glob("*.png"))
    assert list((REPO / "Assets" / "ui" / "District 7").glob("*.png"))


def test_boss_rush_entry_confirms_the_district_7_reference(monkeypatch):
    runner = object.__new__(MacroRunner)
    runner._log = lambda _message: None
    runner._set_status = lambda **_kwargs: None
    runner._checkpoint = lambda _stop_event: False
    runner._ensure_lobby = lambda _hwnd, _stop_event: True
    runner._click_play = lambda _hwnd, _stop_event: True
    runner._click_gamemode = lambda *_args, **_kwargs: True
    runner._debug_save = lambda *_args: None
    runner._mouse = object()
    monkeypatch.setattr(runner_module.vision, "find_image", lambda *_args, **_kwargs: None)
    searched = []
    clicks = []

    def wait_for_image(_hwnd, name, **_kwargs):
        searched.append(name)
        return {"score": 0.95} if name == "District 7" else {}

    monkeypatch.setattr(runner_module.vision, "wait_for_image", wait_for_image)
    monkeypatch.setattr(
        runner_module.vision, "click_match",
        lambda _mouse, _hwnd, match: clicks.append(match),
    )

    assert runner._reach_boss_rush_selected(1, threading.Event())
    assert searched == ["District 7", "nav_select_stage"]
    assert len(clicks) == 1


def test_boss_rush_setup_does_not_select_a_stage_and_skips_difficulty():
    runner = object.__new__(MacroRunner)
    reached = []
    entered = []
    logs = []
    runner._checkpoint = lambda _stop_event: False
    runner._reach_boss_rush_selected = lambda _hwnd, _stop_event: reached.append(True) or True
    runner._select_stage = lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("no Boss Rush stage"))
    runner._enter_selected_stage = lambda _hwnd, _stop_event, _task, mode, _coords, _webhook: (
        entered.append(mode) or True
    )
    runner._log = logs.append

    assert runner._run_task_setup(
        1, threading.Event(), {}, "boss_rush", "District 7",
        {}, None, None,
    )
    assert reached == [True]
    assert entered == ["boss_rush"]
    assert any("locked to Hard" in message for message in logs)


def test_boss_rush_entry_waits_between_menu_transitions():
    runner = object.__new__(MacroRunner)
    delays = []
    runner._log = lambda _message: None
    runner._set_status = lambda **_kwargs: None
    runner._checkpoint = lambda _stop_event: False
    runner._dismiss_party_overlay = lambda *_args: True
    runner._find_gamemode_card = lambda *_args: ({"score": 0.99}, "boss_rush")
    runner._debug_save = lambda *_args: None
    runner._click_gamemode_target = lambda *_args: True
    runner._interruptible_sleep = lambda duration, _stop_event: delays.append(duration)

    assert runner._click_gamemode(1, threading.Event(), "boss_rush", wait_for_menu=False)
    assert delays == [runner_module.BOSS_RUSH_TRANSITION_DELAY]


def test_boss_rush_stage_confirmation_waits_before_solo_start():
    runner = object.__new__(MacroRunner)
    delays = []
    runner._checkpoint = lambda _stop_event: False
    runner._click_and_verify_gone = lambda *_args: True
    runner._click_start_and_wait_teleport = lambda *_args: True
    runner._interruptible_sleep = lambda duration, _stop_event: delays.append(duration)
    runner._log = lambda _message: None
    runner._set_status = lambda **_kwargs: None

    assert runner._enter_selected_stage(
        1, threading.Event(), {"play_mode": "solo"}, "boss_rush", {}, None,
    )
    assert delays == [runner_module.BOSS_RUSH_TRANSITION_DELAY] * 2


def test_missing_boss_rush_route_is_reported_once_after_start_game(monkeypatch):
    runner = object.__new__(MacroRunner)
    sequence, logs = [], []
    runner._active_task = None
    runner._active_task_progress = None
    runner._new_boss_rush_state = MacroRunner._new_boss_rush_state
    runner._log = logs.append
    runner._set_status = lambda **_kwargs: None
    runner._start_game_or_reset_via_settings = lambda *_args: True
    runner._checkpoint = lambda _stop_event: False
    runner._run_prestart = lambda *_args, **_kwargs: sequence.append("camera/pre-start") or True
    runner._wait_out_start_game_warning = lambda *_args: None
    start_checks = iter([("nav_start", {"score": 1.0}), (None, None)])
    runner._find_start_game_button = lambda *_args, **_kwargs: next(start_checks)
    runner._debug_save = lambda *_args: None
    runner._mouse = object()
    runner._keyboard = type("Keyboard", (), {"tap": lambda self, _key: None})()
    runner._interruptible_sleep = lambda _seconds, _stop_event: None
    runner._load_battle_blocks = lambda _task: []
    runner._load_loop_blocks = lambda _task: {"loop_a": [], "loop_b": []}
    runner._release_quick_place_shift = lambda: None
    monkeypatch.setattr(runner_module.wm, "activate_window", lambda _hwnd: True)
    monkeypatch.setattr(runner_module.vision, "click_match", lambda *_args: sequence.append("Start Game"))

    result = runner._play_one_match(
        1, threading.Event(), {
            "mode": "boss_rush",
            "boss_rush_gates": 1,
            "boss_rush_walk_paths": {},
        }, {},
        first_repeat=True,
    )
    assert result == "configuration_error"
    assert sequence == ["camera/pre-start", "Start Game"]
    assert sum("Gate 1 has no Spawn" in message for message in logs) == 1


def test_boss_rush_places_units_only_after_start_and_gate_route(monkeypatch):
    runner = object.__new__(MacroRunner)
    sequence = []
    runner._active_task = None
    runner._new_boss_rush_state = MacroRunner._new_boss_rush_state
    runner._log = lambda _message: None
    runner._set_status = lambda **_kwargs: None
    runner._start_game_or_reset_via_settings = lambda *_args: True
    runner._checkpoint = lambda _stop_event: False
    runner._run_prestart = lambda *_args, **kwargs: (
        sequence.append(("camera/loadout", kwargs.get("run_blocks"))) or True
    )
    runner._wait_out_start_game_warning = lambda *_args: None
    start_checks = iter([("nav_start", {"score": 1.0}), (None, None)])
    runner._find_start_game_button = lambda *_args, **_kwargs: next(start_checks)
    runner._debug_save = lambda *_args: None
    runner._mouse = object()
    runner._keyboard = type("Keyboard", (), {"tap": lambda self, _key: None})()
    runner._interruptible_sleep = lambda _seconds, _stop_event: None
    runner._load_battle_blocks = lambda _task: []
    runner._load_loop_blocks = lambda _task: {"loop_a": [], "loop_b": []}
    runner._release_quick_place_shift = lambda: None
    runner._run_boss_rush_gate_route = lambda *_args: sequence.append("gate route") or True
    runner._run_boss_rush_gate_setup = lambda *_args: sequence.append("gate placement and Start Game") or True
    runner._wait_for_match_result = lambda *_args: sequence.append("battle watch") or "win"
    monkeypatch.setattr(runner_module.wm, "activate_window", lambda _hwnd: True)
    monkeypatch.setattr(runner_module.vision, "click_match", lambda *_args: sequence.append("Start Game"))

    result = runner._play_one_match(
        1, threading.Event(), {
            "mode": "boss_rush",
            "boss_rush_gates": 1,
            "boss_rush_walk_paths": {"1": "Spawn to Gate 1"},
        }, {},
        first_repeat=True,
    )

    assert result == "win"
    assert sequence == [
        ("camera/loadout", False),
        "Start Game",
        "gate route",
        "gate placement and Start Game",
        "battle watch",
    ]


def test_boss_rush_deferred_blocks_skip_all_macro_walk_paths(monkeypatch):
    runner = object.__new__(MacroRunner)
    ran_blocks = []
    runner._log = lambda _message: None
    runner._set_status = lambda **_kwargs: None
    runner._checkpoint = lambda _stop_event: False
    runner._release_quick_place_shift = lambda: None
    runner._last_unit_ordinal = 0
    runner._quick_place_shift_down = False
    runner._run_prestart_single_block = lambda _hwnd, _stop, _task, _paths, block, *_args: (
        ran_blocks.append(block["type"])
    )
    monkeypatch.setattr(template_module, "load_template", lambda _name: {
        "blocks": {"prestart": [
            {"type": "walk_path", "mode": "custom", "pathName": "Template walk"},
            {"type": "place_unit", "hotkey": "1"},
        ]}
    })
    monkeypatch.setattr(runner_blocks.wm, "get_window_rect_screen", lambda _hwnd: (0, 0, 100, 100))

    runner._run_prestart_blocks(
        1, threading.Event(), {"macro": "Boss Rush"}, first_repeat=True,
        default_walk_paths={}, skip_walk_paths=True,
    )

    assert ran_blocks == ["place_unit"]


def test_boss_rush_gate_setup_places_before_clicking_gate_start():
    runner = object.__new__(MacroRunner)
    sequence = []
    runner._log = lambda _message: None
    runner._checkpoint = lambda _stop_event: False
    runner._run_prestart_blocks = lambda _hwnd, _stop, _task, **kwargs: sequence.append(
        ("placements", kwargs["skip_walk_paths"])
    )
    runner._click_boss_rush_gate_start = lambda _hwnd, _stop, gate, _state: (
        sequence.append(f"start-gate-{gate}") or True
    )

    assert runner._run_boss_rush_gate_setup(
        1, threading.Event(), {"macro": "Boss Rush"}, 1, {},
    )
    assert sequence == [("placements", True), "start-gate-1"]


def test_boss_rush_gate_start_click_waits_for_button_to_disappear(monkeypatch):
    runner = object.__new__(MacroRunner)
    clicks, sleeps = [], []
    runner._log = lambda _message: None
    runner._checkpoint = lambda _stop_event: False
    runner._wait_out_start_game_warning = lambda *_args: None
    results = iter([("nav_start_game", {"score": 1.0}), (None, None)])
    runner._find_start_game_button = lambda *_args, **_kwargs: next(results)
    runner._debug_save = lambda *_args: None
    runner._keyboard = type("Keyboard", (), {"tap": lambda self, key: clicks.append(("key", key))})()
    runner._mouse = object()
    runner._interruptible_sleep = lambda seconds, _stop_event: sleeps.append(seconds)
    monkeypatch.setattr(runner_module.wm, "activate_window", lambda _hwnd: True)
    monkeypatch.setattr(runner_module.vision, "click_match", lambda *_args: clicks.append("start"))

    state = {"configuration_error": False}
    assert runner._click_boss_rush_gate_start(1, threading.Event(), 2, state)
    assert clicks == [("key", ord("Z")), "start"]
    assert runner_module.START_GAME_CLICK_VERIFY_SETTLE in sleeps
    assert state["configuration_error"] is False


def test_boss_rush_configuration_error_stops_without_lobby_recovery():
    runner = object.__new__(MacroRunner)
    runner._log = lambda _message: None
    runner._set_status = lambda **_kwargs: None
    runner._checkpoint = lambda _stop_event: False
    runner._current_hwnd = None
    runner._skip_first_task_setup = False
    runner._new_boss_rush_state = MacroRunner._new_boss_rush_state
    runner._run_task_setup = lambda *_args: True
    runner._play_one_match = lambda *_args, **_kwargs: "configuration_error"
    runner._recover_to_lobby = lambda *_args: (_ for _ in ()).throw(
        AssertionError("configuration errors must not enter repeated recovery")
    )
    runner._send_progress_webhook = lambda *_args, **_kwargs: None

    assert runner._run_task(
        1, threading.Event(),
        {"mode": "boss_rush", "map": "District 7", "repeat": 1},
        1, 1, {}, None, None, {}, {},
    ) is False


def test_boss_rush_state_validates_gate_count_and_card_side():
    assert MacroRunner._new_boss_rush_state({"boss_rush_gates": "6", "boss_rush_card": "right"}) == {
        "target": 6,
        "card": "right",
        "cleared": 0,
        "awaiting_decision": False,
        "decision_since": 0.0,
        "card_click_attempts": 0,
        "card_last_click_at": 0.0,
        "boss_started": False,
        "configuration_error": False,
        "missing_template_logged": set(),
    }
    assert MacroRunner._new_boss_rush_state({"boss_rush_gates": 7}) is None
    assert MacroRunner._new_boss_rush_state({"boss_rush_gates": True}) is None
    assert MacroRunner._new_boss_rush_state({"boss_rush_card": "center"}) is None


def test_boss_rush_card_and_continue_route_progression(monkeypatch):
    runner = object.__new__(MacroRunner)
    runner._coords = {"boss_rush_card_left_x": 277, "boss_rush_card_left_y": 392}
    runner._mouse = type("Mouse", (), {"click": lambda self, x, y: clicks.append((x, y))})()
    runner._log = lambda _message: None
    clicks = []
    route_gates = []
    matches = {"boss_rush_pick_card": {"score": 0.9}}
    lookups = []

    def find_image(_hwnd, name, **_kwargs):
        lookups.append(name)
        return matches.get(name)

    monkeypatch.setattr(runner_module.vision, "find_image", find_image)
    monkeypatch.setattr(runner_module.vision, "ref_to_screen", lambda _hwnd, x, y: (x + 10, y + 20))
    monkeypatch.setattr(runner_module.vision, "click_match", lambda *_args: None)
    monkeypatch.setattr(runner_module.wm, "activate_window", lambda _hwnd: True)
    runner._interruptible_sleep = lambda *_args: None
    runner._save_debug_screenshot_unconditional = lambda *_args: None

    def click_and_close_card(_self, x, y):
        clicks.append((x, y))
        matches["boss_rush_pick_card"] = None

    runner._mouse = type("Mouse", (), {"click": click_and_close_card})()
    runner._wait_for_boss_rush_decision_gone = lambda *_args: True
    runner._checkpoint = lambda _stop_event: False
    runner._run_boss_rush_gate_route = lambda _hwnd, _stop, _task, gate, _state: route_gates.append(gate) or True
    runner._run_boss_rush_gate_setup = lambda _hwnd, _stop, _task, gate, _state: (
        route_gates.append(f"setup-{gate}") or True
    )
    state = MacroRunner._new_boss_rush_state({"boss_rush_gates": 2, "boss_rush_card": "left"})
    task = {"boss_rush_walk_paths": {"2": "Gate 2"}}

    assert runner._handle_boss_rush_progress(1, threading.Event(), task, state) == "handled"
    assert state["cleared"] == 1
    assert clicks == [(287, 412)]

    matches.update({"boss_rush_pick_card": None})
    assert runner._handle_boss_rush_progress(1, threading.Event(), task, state) == "handled"
    assert route_gates == [2, "setup-2"]
    assert state["awaiting_decision"] is False
    assert "boss_rush_continue" not in lookups


def test_boss_rush_cards_use_dedicated_macro_coordinates():
    assert runner_module.BOSS_RUSH_CARD_COORDS == {
        "left": ("boss_rush_card_left_x", "boss_rush_card_left_y"),
        "middle": ("boss_rush_card_middle_x", "boss_rush_card_middle_y"),
        "right": ("boss_rush_card_right_x", "boss_rush_card_right_y"),
    }


def test_boss_rush_retries_card_click_on_a_later_progress_poll(monkeypatch):
    runner = object.__new__(MacroRunner)
    runner._coords = {"boss_rush_card_right_x": 876, "boss_rush_card_right_y": 392}
    runner._log = lambda _message: None
    attempts = []
    matches = {"boss_rush_pick_card": {"score": 0.9}}
    monkeypatch.setattr(runner_module.vision, "find_image", lambda _hwnd, name: matches.get(name))
    monkeypatch.setattr(runner_module.vision, "ref_to_screen", lambda _hwnd, x, y: (x, y))
    monkeypatch.setattr(runner_module.wm, "activate_window", lambda _hwnd: True)
    clock = [0.0]
    monkeypatch.setattr(runner_module.time, "monotonic", lambda: clock[0])
    runner._checkpoint = lambda _stop_event: False
    runner._interruptible_sleep = lambda seconds, _stop_event: clock.__setitem__(0, clock[0] + seconds)
    runner._save_debug_screenshot_unconditional = lambda *_args: None

    def click_and_register(_self, x, y):
        attempts.append((x, y))
        if len(attempts) == 2:
            matches["boss_rush_pick_card"] = None

    runner._mouse = type("Mouse", (), {"click": click_and_register})()
    state = MacroRunner._new_boss_rush_state({"boss_rush_card": "right"})

    assert runner._click_boss_rush_card(1, threading.Event(), state) is True
    assert runner._click_boss_rush_card(1, threading.Event(), state) is True
    assert attempts == [(876, 392), (876, 392)]
    assert state["card_click_attempts"] == 2


def test_boss_rush_retries_card_failure_without_configuration_error(monkeypatch):
    runner = object.__new__(MacroRunner)
    runner._log = lambda _message: None
    runner._save_debug_screenshot_unconditional = lambda *_args: "card.png"
    clock = [0.0]
    monkeypatch.setattr(runner_module.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(runner_module.vision, "find_image", lambda *_args, **_kwargs: {"score": 0.9})
    runner._checkpoint = lambda _stop_event: False
    runner._interruptible_sleep = lambda seconds, _stop_event: clock.__setitem__(0, clock[0] + seconds)
    runner._coords = {"boss_rush_card_right_x": 876, "boss_rush_card_right_y": 392}
    monkeypatch.setattr(runner_module.vision, "ref_to_screen", lambda _hwnd, x, y: (x, y))
    monkeypatch.setattr(runner_module.wm, "activate_window", lambda _hwnd: True)
    runner._mouse = type("Mouse", (), {"click": lambda *_args: None})()
    state = MacroRunner._new_boss_rush_state({"boss_rush_gates": 2, "boss_rush_card": "right"})
    state.update({
        "cleared": 1,
        "awaiting_decision": True,
        "card_click_attempts": runner_module.BOSS_RUSH_CARD_CLICK_ATTEMPTS,
        "card_last_click_at": clock[0] - runner_module.BOSS_RUSH_CARD_CLICK_RETRY_DELAY,
    })

    result = runner._handle_boss_rush_progress(
        1, threading.Event(), {"boss_rush_walk_paths": {}}, state,
    )

    assert result == "failed"
    assert state["configuration_error"] is False


def test_boss_rush_gate_two_setup_skips_prestart_blocks(monkeypatch):
    runner = object.__new__(MacroRunner)
    runner._log = lambda _message: None
    runner._checkpoint = lambda _stop_event: False
    placement_calls = []
    runner._run_prestart_blocks = lambda *_args, **_kwargs: placement_calls.append(True)
    runner._click_boss_rush_gate_start = lambda *_args: True
    assert runner._run_boss_rush_gate_setup(
        1, threading.Event(), {"macro": "regular"}, 2, {},
    ) is True
    assert placement_calls == []


def test_boss_rush_uses_lower_match_fallback_for_decision_button(monkeypatch):
    runner = object.__new__(MacroRunner)
    runner._coords = {"boss_rush_card_left_x": 277, "boss_rush_card_left_y": 392}
    runner._mouse = type("Mouse", (), {"click": lambda *_args: None})()
    runner._log = lambda _message: None
    clicks = []
    route_gates = []
    lookups = []

    def find_image(_hwnd, name, **kwargs):
        lookups.append((name, kwargs.get("threshold")))
        if name == "boss_rush_continue" and kwargs.get("threshold") == runner_module.BOSS_RUSH_DECISION_FALLBACK_THRESHOLD:
            return {"score": 0.84}
        return None

    monkeypatch.setattr(runner_module.vision, "find_image", find_image)
    monkeypatch.setattr(runner_module.vision, "ref_to_screen", lambda _hwnd, x, y: (x, y))
    monkeypatch.setattr(runner_module.vision, "click_match", lambda *_args: clicks.append(True))
    runner._wait_for_boss_rush_decision_gone = lambda *_args: True
    runner._checkpoint = lambda _stop_event: False
    runner._interruptible_sleep = lambda *_args: None
    runner._run_boss_rush_gate_route = lambda _hwnd, _stop, _task, gate, _state: route_gates.append(gate) or True
    runner._run_boss_rush_gate_setup = lambda _hwnd, _stop, _task, gate, _state: route_gates.append(f"setup-{gate}") or True
    state = MacroRunner._new_boss_rush_state({"boss_rush_gates": 3, "boss_rush_card": "left"})
    state.update({"cleared": 2, "awaiting_decision": True,
                  "decision_since": runner_module.time.time() - 5.0})

    assert runner._handle_boss_rush_progress(
        1, threading.Event(), {"boss_rush_walk_paths": {"3": "Gate 3"}}, state,
    ) == "handled"
    assert ("boss_rush_continue", runner_module.BOSS_RUSH_DECISION_FALLBACK_THRESHOLD) in lookups
    assert clicks == [True]
    assert route_gates == [3, "setup-3"]


def test_boss_rush_handles_continue_while_card_prompt_match_lingers(monkeypatch):
    runner = object.__new__(MacroRunner)
    runner._log = lambda _message: None
    runner._checkpoint = lambda _stop_event: False
    runner._interruptible_sleep = lambda *_args: None
    runner._wait_for_boss_rush_decision_gone = lambda *_args: True
    runner._mouse = object()
    clicked = []
    route_gates = []
    matches = {
        "boss_rush_pick_card": {"score": 0.9},
        "boss_rush_continue": {"score": 0.95},
    }
    monkeypatch.setattr(
        runner_module.vision, "find_image",
        lambda _hwnd, name, **_kwargs: matches.get(name),
    )
    monkeypatch.setattr(
        runner_module.vision, "click_match", lambda *_args: clicked.append(True))
    monkeypatch.setattr(
        runner_module.wm, "activate_window", lambda _hwnd: True)
    runner._run_boss_rush_gate_route = lambda _hwnd, _stop, _task, gate, _state: route_gates.append(gate) or True
    runner._run_boss_rush_gate_setup = lambda _hwnd, _stop, _task, gate, _state: route_gates.append(f"setup-{gate}") or True
    state = MacroRunner._new_boss_rush_state({"boss_rush_gates": 3})
    state.update({"cleared": 2, "awaiting_decision": True, "decision_since": runner_module.time.time()})

    assert runner._handle_boss_rush_progress(
        1, threading.Event(), {"boss_rush_walk_paths": {"3": "Gate 3"}}, state,
    ) == "handled"
    assert clicked == [True]
    assert route_gates == [3, "setup-3"]


def test_boss_rush_retries_continue_click_until_prompt_closes(monkeypatch):
    runner = object.__new__(MacroRunner)
    logs = []
    runner._log = logs.append
    runner._checkpoint = lambda _stop_event: False
    runner._interruptible_sleep = lambda *_args: None
    runner._mouse = object()
    attempts = []
    route_gates = []
    decision_matches = iter([
        {"score": 0.95},
        {"score": 0.94},
    ])

    def find_image(_hwnd, name, **_kwargs):
        if name == "boss_rush_pick_card":
            return None
        if name == "boss_rush_continue":
            return next(decision_matches, None)
        return None

    monkeypatch.setattr(runner_module.vision, "find_image", find_image)
    monkeypatch.setattr(
        runner_module.vision, "click_match", lambda *_args: attempts.append(True))
    monkeypatch.setattr(
        runner_module.wm, "activate_window", lambda _hwnd: True)
    verify_results = iter([False, True])
    runner._wait_for_boss_rush_decision_gone = lambda *_args: next(verify_results)
    runner._run_boss_rush_gate_route = lambda _hwnd, _stop, _task, gate, _state: route_gates.append(gate) or True
    runner._run_boss_rush_gate_setup = lambda _hwnd, _stop, _task, gate, _state: route_gates.append(f"setup-{gate}") or True
    state = MacroRunner._new_boss_rush_state({"boss_rush_gates": 3})
    state.update({"cleared": 2, "awaiting_decision": True, "decision_since": runner_module.time.time() - 5})

    result = runner._handle_boss_rush_progress(
        1, threading.Event(), {"boss_rush_walk_paths": {"3": "Gate 3"}}, state,
    )

    assert result == "handled"
    assert attempts == [True, True]
    assert route_gates == [3, "setup-3"]
    assert any("Retrying \"Continue\" click (2/3)" in message for message in logs)
    assert state["configuration_error"] is False


def test_boss_rush_gate_six_selects_continue_then_starts_boss_setup(monkeypatch):
    runner = object.__new__(MacroRunner)
    logs = []
    runner._log = logs.append
    runner._checkpoint = lambda _stop_event: False
    runner._interruptible_sleep = lambda *_args: None
    runner._wait_for_boss_rush_decision_gone = lambda *_args: True
    runner._mouse = object()
    clicked = []
    boss_setup = []
    matches = {
        "boss_rush_pick_card": None,
        "boss_rush_continue": {"score": 0.95},
        "boss_rush_fight_boss": None,
    }
    monkeypatch.setattr(
        runner_module.vision, "find_image",
        lambda _hwnd, name, **_kwargs: matches.get(name),
    )
    monkeypatch.setattr(
        runner_module.vision, "click_match", lambda *_args: clicked.append(True))
    monkeypatch.setattr(
        runner_module.wm, "activate_window", lambda _hwnd: True)
    runner._start_boss_rush_boss_setup = lambda *_args: boss_setup.append(True) or True
    runner._run_boss_rush_gate_route = lambda *_args: pytest.fail(
        "Gate 6 Continue must proceed to boss setup, not route to Gate 7")
    state = MacroRunner._new_boss_rush_state({"boss_rush_gates": 6})
    state.update({
        "cleared": 6,
        "awaiting_decision": True,
        "decision_since": runner_module.time.time(),
    })

    assert runner._handle_boss_rush_progress(
        1, threading.Event(), {}, state,
    ) == "handled"
    assert clicked == [True]
    assert boss_setup == [True]
    assert state["boss_started"] is True
    assert any('Selecting "Continue" after gate 6.' in line for line in logs)


def test_boss_rush_confirms_decision_closed_with_fallback_match(monkeypatch):
    runner = object.__new__(MacroRunner)
    runner._log = lambda _message: None
    runner._checkpoint = lambda _stop_event: False
    clock = [0.0]
    monkeypatch.setattr(runner_module.time, "monotonic", lambda: clock[0])
    runner._interruptible_sleep = lambda seconds, _stop_event: clock.__setitem__(0, clock[0] + seconds)
    fallback_matches = iter([{"score": 0.84}, None])
    lookups = []

    def find_image(_hwnd, name, **kwargs):
        lookups.append((name, kwargs.get("threshold")))
        if kwargs.get("threshold") == runner_module.BOSS_RUSH_DECISION_FALLBACK_THRESHOLD:
            return next(fallback_matches)
        return None

    monkeypatch.setattr(runner_module.vision, "find_image", find_image)
    state = {"configuration_error": False}

    assert runner._wait_for_boss_rush_decision_gone(
        1, "boss_rush_continue", threading.Event(), state,
    ) is True
    assert lookups.count(
        ("boss_rush_continue", runner_module.BOSS_RUSH_DECISION_FALLBACK_THRESHOLD)
    ) == 2
    assert state["configuration_error"] is False


def test_boss_rush_decision_timeout_is_reported_as_non_retriable(monkeypatch):
    runner = object.__new__(MacroRunner)
    runner._coords = {}
    logs = []
    runner._log = logs.append
    runner._save_debug_screenshot_unconditional = lambda *_args: "decision.png"
    matches = {"boss_rush_pick_card": None, "boss_rush_continue": None}
    monkeypatch.setattr(
        runner_module.vision, "find_image",
        lambda _hwnd, name, **_kwargs: matches.get(name),
    )
    state = MacroRunner._new_boss_rush_state({"boss_rush_gates": 2})
    state["target"] = 3
    state.update({
        "cleared": 2,
        "awaiting_decision": True,
        "decision_since": runner_module.time.time() - runner_module.BOSS_RUSH_DECISION_TIMEOUT - 1,
    })
    runner._checkpoint = lambda _stop_event: False

    result = runner._handle_boss_rush_progress(
        1, threading.Event(), {"boss_rush_walk_paths": {}}, state,
    )

    assert result == "failed"
    assert state["configuration_error"] is True
    assert any("without returning to the lobby" in message for message in logs)
    assert any("decision.png" in message for message in logs)


def _make_boss_rush_result_watcher(state, stop_event, logs, monkeypatch, detected_result):
    runner = object.__new__(MacroRunner)
    runner._log = logs.append
    runner._set_status = lambda **_kwargs: None
    runner._checkpoint = lambda stop: stop.is_set()
    runner._handle_boss_rush_progress = lambda *_args: "idle"
    runner._run_battle_blocks_tick = lambda *_args: None
    runner._tick_loop_phases = lambda *_args: None
    runner._dismiss_afk_chamber = lambda _hwnd, last: last
    runner._battle_leave_requested = False
    runner._debug_save = lambda *_args: None
    monkeypatch.setattr(runner_module, "RECONNECT_IMAGE_NAMES", ())
    monkeypatch.setattr(runner_module.vision, "find_image", lambda _hwnd, name: (
        {"score": 1.0} if name == detected_result else None
    ))
    monkeypatch.setattr(runner_module.time, "sleep", lambda _seconds: stop_event.set())
    return runner


def test_boss_rush_ignores_gate_victory_and_defeat_until_boss_stage(monkeypatch):
    stop_event = threading.Event()
    logs = []
    state = MacroRunner._new_boss_rush_state({"boss_rush_gates": 2})
    runner = _make_boss_rush_result_watcher(
        state, stop_event, logs, monkeypatch, detected_result="victory",
    )

    result = runner._wait_for_match_result(
        1, stop_event, mode="boss_rush", task={"mode": "boss_rush"},
        boss_rush_state=state,
    )

    assert result is None
    assert not any("Battle in progress -- watching for Victory/Defeat" in msg for msg in logs)
    assert not any(msg.startswith("[Macro] Victory!") for msg in logs)


def test_boss_rush_watches_for_result_after_boss_gate_starts(monkeypatch):
    stop_event = threading.Event()
    logs = []
    state = MacroRunner._new_boss_rush_state({"boss_rush_gates": 2})
    state["boss_started"] = True
    runner = _make_boss_rush_result_watcher(
        state, stop_event, logs, monkeypatch, detected_result="victory",
    )

    result = runner._wait_for_match_result(
        1, stop_event, mode="boss_rush", task={"mode": "boss_rush"},
        boss_rush_state=state,
    )

    assert result == "win"
    assert any("Boss battle in progress -- watching for Victory/Defeat" in msg for msg in logs)


def test_boss_rush_fight_boss_runs_the_separate_boss_setup(monkeypatch):
    runner = object.__new__(MacroRunner)
    runner._coords = {"boss_rush_card_left_x": 277, "boss_rush_card_left_y": 392}
    runner._mouse = type("Mouse", (), {"click": lambda *_args: None})()
    runner._log = lambda _message: None
    boss_setup = []
    matches = {"boss_rush_pick_card": {"score": 0.9}, "boss_rush_fight_boss": None}
    monkeypatch.setattr(runner_module.vision, "find_image", lambda _hwnd, name, **_kwargs: matches.get(name))
    monkeypatch.setattr(runner_module.vision, "ref_to_screen", lambda _hwnd, x, y: (x, y))
    monkeypatch.setattr(runner_module.vision, "click_match", lambda *_args: None)
    monkeypatch.setattr(runner_module.wm, "activate_window", lambda _hwnd: True)
    runner._interruptible_sleep = lambda *_args: None
    runner._wait_for_boss_rush_decision_gone = lambda *_args: True
    runner._checkpoint = lambda _stop_event: False
    runner._start_boss_rush_boss_setup = lambda *_args: boss_setup.append(True) or True
    state = MacroRunner._new_boss_rush_state({"boss_rush_gates": 1, "boss_rush_card": "left"})
    task = {"boss_rush_boss_macro": "Boss placement"}
    runner._mouse = type(
        "Mouse", (), {"click": lambda _self, *_args: matches.update({"boss_rush_pick_card": None})})()

    assert runner._handle_boss_rush_progress(1, threading.Event(), task, state) == "handled"
    matches["boss_rush_fight_boss"] = {"score": 0.9}
    assert runner._handle_boss_rush_progress(1, threading.Event(), task, state) == "handled"
    assert boss_setup == [True]
    assert state["boss_started"] is True


def test_boss_rush_walk_paths_are_saved_and_injected_only_for_boss_tasks(monkeypatch):
    import main

    settings = {"tasks": [{"id": 1, "mode": "boss_rush"}, {"id": 2, "mode": "story"}]}
    persisted = []
    monkeypatch.setattr(main.cfg, "load", lambda: settings)
    monkeypatch.setattr(main.cfg, "update", lambda data: persisted.append(data.copy()) or settings.update(data))
    api = main.Api.__new__(main.Api)

    assert api.get_boss_rush_paths()["paths"] == {str(gate): "" for gate in range(1, 7)}
    assert api.set_boss_rush_path(3, "Gate Three")["ok"] is True
    assert api.set_boss_rush_path(7, "Invalid") == {"ok": False, "reason": "invalid_gate"}
    run_tasks = api.get_run_tasks()
    assert run_tasks[0]["boss_rush_walk_paths"]["3"] == "Gate Three"
    assert "boss_rush_walk_paths" not in run_tasks[1]
    assert "boss_rush_walk_paths" not in settings["tasks"][0]
