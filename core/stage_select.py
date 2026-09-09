"""Picks a Story map card by image-matching a small reference crop of its
name label -- OCR was tried first but was too slow in practice (a multi-
mask/multi-psm Tesseract sweep per card, repeated on every scroll nudge,
added up fast). Each map gets its own reference image instead
(Assets/maps/<map name>.png, named to match a Task's `map` field exactly --
this folder covers Raid maps too, e.g. "Spirit City", not just Story ones)
and is found the same way nav_play/nav_back are: grayscale template
matching against a live capture (see core.vision).
"""
import time

from . import vision
from . import window as wm

# Map-name labels are searched over the FULL window, same as every other
# UI search -- there used to be a thin fixed "name band" region here as a
# speed optimization, but real matched frames in debug/ show the label row
# rendering at two different heights ~115px apart (carousel state
# dependent), and the 30px band could only ever see one of them -- it even
# clipped the taller label crops entirely (matchTemplate needs template <=
# haystack), which read as "map search just doesn't work". Full-window
# costs a few extra ms per check and can't be blindsided by the row
# moving again.

MATCH_THRESHOLD = 0.78

SCROLL_CENTER = (576, 390)        # middle of the card row -- where the wheel-scroll is aimed
DEFAULT_SCROLL_POWER = 3          # multiplier on one wheel notch -- the carousel barely moved at 1x
SCROLL_NUDGES_PER_PASS = 8        # how many forward nudges before giving up on this pass and resetting
SCROLL_RESET_NOTCHES = 20         # scrolled back this many (power-scaled) notches -- far more than any real list needs, to guarantee hitting the start
SETTLE_DELAY = 0.35               # lets the carousel's scroll animation actually finish before the next capture
MAX_PASSES = 3

STORY_EVENT_IMAGES = {
    "Eclipsed Infinite": "story_eclipsed_infinite",
    "Golden Hour": "story_golden_hour",
}


def _hover_wiggle(mouse) -> None:
    """Makes the carousel actually own the cursor before the wheel fires.

    An absolute move_to() jump doesn't reliably read as a real
    cursor-over-the-carousel hover on every machine, and even the single
    1px nudge() that used to follow it wasn't always enough -- reported
    (and reproduced) as the cursor just sitting at the scroll spot while
    every wheel event gets silently dropped. A short multi-step wiggle
    (net displacement zero, so the aim point is unchanged) plus a longer
    settle gives Roblox unambiguous relative motion to register the hover
    from before the first scroll notch arrives."""
    for dx, dy in ((3, 2), (-2, 1), (-1, -3)):
        mouse.nudge(dx, dy)
        time.sleep(0.02)
    time.sleep(0.1)


def find_and_click_map(mouse, hwnd, map_name: str, log, stop_event=None, scroll_power: int = DEFAULT_SCROLL_POWER,
                        scroll_nudges: int = SCROLL_NUDGES_PER_PASS, debug_screenshots: bool = False) -> bool:
    """Scans the Story map carousel for map_name (image-matched against
    Assets/maps/<map_name>.png over the whole name-label band) and
    clicks it once found.

    If it's not among the 3 currently-visible cards, nudges the carousel
    forward with the scroll wheel and re-checks -- up to `scroll_nudges`
    times -- before scrolling all the way back to the start and running the
    whole pass again, up to MAX_PASSES times total. Resetting to a known
    position (the very start) rather than just scrolling further is what
    makes a pass recoverable if a nudge ever lands mid-animation and a check
    gets missed -- forever scrolling forward has no way to correct for that.
    """
    scroll_step = -120 * max(1, scroll_power)
    scroll_nudges = max(0, scroll_nudges)
    left, top, _, _ = wm.get_window_rect_screen(hwnd)

    def to_screen(pt):
        return left + pt[0], top + pt[1]

    for attempt in range(1, MAX_PASSES + 1):
        if stop_event is not None and stop_event.is_set():
            return False
        log(f'[Macro] Looking for map "{map_name}" (pass {attempt}/{MAX_PASSES}, up to {scroll_nudges} scrolls)...')
        mouse.move_to(*to_screen(SCROLL_CENTER))
        _hover_wiggle(mouse)
        for nudge in range(scroll_nudges + 1):
            if stop_event is not None and stop_event.is_set():
                return False
            # Every reference crop for this map (the original AND any
            # "<map name> 2.png"-style extras) lives in Assets/maps/
            # <map name>/ and gets tried automatically as a variant of the
            # one map name (see vision.template_variant_paths) -- no more
            # separately-searched " 2" name.
            try:
                match, found_name = vision.find_image_any(
                    hwnd, (map_name,), threshold=MATCH_THRESHOLD,
                    template_dir=vision.MAPS_DIR)
            except vision.TemplateNotFound as exc:
                log(f"[Macro] {exc}")
                return False
            if match is not None:
                debug_path = vision.save_match_debug(
                    hwnd, found_name, match, log=log) if debug_screenshots else None
                suffix = f" Debug: {debug_path}" if debug_path else ""
                log(f'[Macro] Found "{found_name}" (score {match["score"]:.2f}) -- clicking it.{suffix}')
                vision.click_match(mouse, hwnd, match)
                return True
            if nudge < scroll_nudges:
                mouse.scroll(scroll_step)
                time.sleep(SETTLE_DELAY)
        log("[Macro] Not found in this pass -- scrolling back to the start.")
        mouse.move_to(*to_screen(SCROLL_CENTER))
        _hover_wiggle(mouse)
        for _ in range(SCROLL_RESET_NOTCHES):
            mouse.scroll(-scroll_step)
        time.sleep(SETTLE_DELAY)

    log(f'[Macro] Map name "{map_name}" never matched in the carousel after {MAX_PASSES} full passes -- '
        f'stopping. If its card was visibly scrolling by, the name-label crop isn\'t matching your setup '
        f'-- add your own via Settings > General > Image Manager (Map Names tab).')
    return False


def find_and_click_story_event(mouse, hwnd, event_name: str, log, stop_event=None,
                               scroll_power: int = DEFAULT_SCROLL_POWER,
                               scroll_nudges: int = SCROLL_NUDGES_PER_PASS,
                               debug_screenshots: bool = False) -> bool:
    """Scan the Story carousel for an event badge and select its map card."""
    image_name = STORY_EVENT_IMAGES.get(event_name)
    if not image_name:
        log(f'[Macro] Unknown Story Event "{event_name}".')
        return False
    scroll_step = -120 * max(1, scroll_power)
    scroll_nudges = max(0, scroll_nudges)
    left, top, _, _ = wm.get_window_rect_screen(hwnd)

    def to_screen(pt):
        return left + pt[0], top + pt[1]

    for attempt in range(1, MAX_PASSES + 1):
        if stop_event is not None and stop_event.is_set():
            return False
        log(f'[Macro] Looking for Story Event "{event_name}" (pass {attempt}/{MAX_PASSES}, '
            f'up to {scroll_nudges} scrolls)...')
        mouse.move_to(*to_screen(SCROLL_CENTER))
        _hover_wiggle(mouse)
        for nudge in range(scroll_nudges + 1):
            if stop_event is not None and stop_event.is_set():
                return False
            try:
                match, found_name = vision.find_image_any(
                    hwnd, (image_name,), threshold=MATCH_THRESHOLD,
                    template_dir=vision.UI_ASSETS_DIR)
            except vision.TemplateNotFound as exc:
                log(f"[Macro] {exc} Add the event crop through Settings > General > Image Manager.")
                return False
            if match is not None:
                debug_path = vision.save_match_debug(
                    hwnd, found_name, match, log=log) if debug_screenshots else None
                suffix = f" Debug: {debug_path}" if debug_path else ""
                selected_map = None
                nearest_distance = None
                for map_name in _story_map_names():
                    try:
                        map_matches = vision.find_image_all(
                            hwnd, map_name, threshold=MATCH_THRESHOLD,
                            template_dir=vision.MAPS_DIR, max_results=5)
                    except vision.TemplateNotFound:
                        continue
                    for map_match in map_matches:
                        distance = ((map_match["cx"] - match["cx"]) ** 2
                                    + (map_match["cy"] - match["cy"]) ** 2)
                        if nearest_distance is None or distance < nearest_distance:
                            nearest_distance = distance
                            selected_map = map_name
                log(f'[Macro] Found Story Event "{found_name}" (score {match["score"]:.2f}) '
                    f'-- clicking its map card.{suffix}')
                vision.click_match(mouse, hwnd, match)
                return selected_map or True
            if nudge < scroll_nudges:
                mouse.scroll(scroll_step)
                time.sleep(SETTLE_DELAY)
        log("[Macro] Story Event not found in this pass -- scrolling back to the start.")
        mouse.move_to(*to_screen(SCROLL_CENTER))
        _hover_wiggle(mouse)
        for _ in range(SCROLL_RESET_NOTCHES):
            mouse.scroll(-scroll_step)
        time.sleep(SETTLE_DELAY)

    log(f'[Macro] Story Event "{event_name}" was not found after {MAX_PASSES} full carousel passes.')
    return False


def _story_map_names():
    """Return configured Story map names without duplicating the UI list."""
    from .runner_constants import CHALLENGE_STORY_MAPS
    return CHALLENGE_STORY_MAPS
