"""Guards for the Story-map lists used by challenge and bounty automation."""
from pathlib import Path

import main
from core import bounty
from core import runner_constants as rc

REPO = Path(__file__).resolve().parent.parent
APP_JS = REPO / "ui" / "app.js"


def test_resource_map_setup_uses_backend_map_settings():
    """Challenge and Bounty rows follow the maps returned by their APIs."""
    src = APP_JS.read_text(encoding="utf-8")
    challenge_render = src.split("function renderChallengeScreen()", 1)[1].split(
        "async function toggleChallengeEnabled", 1)[0]
    assert "Object.keys(s.maps || {}).map(map =>" in challenge_render
    bounty_render = src.split("function renderBountyScreen()", 1)[1].split(
        "async function toggleBountyEnabled", 1)[0]
    assert "Object.keys(s.maps || {}).map(map =>" in bounty_render


def test_bounty_shares_the_same_story_map_list():
    """core.bounty.STORY_MAPS is what read_destination_map matches an OCRed
    bounty destination against; BOUNTY_STORY_MAPS is what the Bounty Story Map
    Setup offers. A destination readable but not assignable means the same
    unit-less battle Challenge hits."""
    assert sorted(bounty.STORY_MAPS) == sorted(main.BOUNTY_STORY_MAPS)


def test_every_default_challenge_map_has_a_reference_crop():
    """_detect_current_challenge_map searches Assets/ui/<map> for each name.
    A name with no crop raises TemplateNotFound and drops the whole search to
    the OCR fallback, so the map is effectively unrecognizable."""
    for name in rc.CHALLENGE_STORY_MAPS:
        direct = REPO / "Assets" / "ui" / f"{name}.png"
        folder = REPO / "Assets" / "ui" / name
        variants = sorted(folder.glob("*.png")) if folder.is_dir() else []
        assert direct.is_file() or variants, f"{name} has no crop under Assets/ui"


def test_daily_challenge_ocr_aliases_cover_every_map():
    """The Daily Challenge map label is too small for the image search, so
    _detect_challenge_map_ocr reads it instead and needs one alias per map.
    A missing alias means that map is never named by the fallback."""
    assert sorted(rc.CHALLENGE_MAP_OCR_ALIASES) == sorted(rc.CHALLENGE_STORY_MAPS)
    assert all(alias.isalpha() and alias.islower()
               for alias in rc.CHALLENGE_MAP_OCR_ALIASES.values())


def test_ocr_aliases_are_distinct_and_not_dropped_as_boilerplate():
    """Two maps sharing an alias, or an alias that the stopword filter strips
    before scoring, both leave a map that can never win the match."""
    aliases = list(rc.CHALLENGE_MAP_OCR_ALIASES.values())
    assert len(set(aliases)) == len(aliases), "two maps share an OCR alias"
    assert not set(aliases) & set(rc.CHALLENGE_MAP_OCR_STOPWORDS)
