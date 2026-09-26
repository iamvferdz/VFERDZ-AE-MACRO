"""Serves the map catalog (Assets/map/<Category>/<Map name>.png) to the
Place Unit picker in Creation -- lets a player click a spot on a reference
map image (or a live Roblox snapshot, see main.get_roblox_snapshot) to read
off an X/Y position instead of guessing coordinates blind.
"""
import base64
import os
import re

from . import constants

MAPS_DIR = os.path.join(constants.ASSETS_DIR, "map")
REFERENCE_MAPS_DIR = os.path.join(constants.ASSETS_DIR, "maps")

_IMAGE_EXTS = (".png", ".jpg", ".jpeg")


def list_categories() -> list:
    if not os.path.isdir(MAPS_DIR):
        return []
    return sorted(d for d in os.listdir(MAPS_DIR) if os.path.isdir(os.path.join(MAPS_DIR, d)))


def list_maps(category: str) -> list:
    folder = os.path.join(MAPS_DIR, category)
    if not os.path.isdir(folder):
        return []
    return sorted(
        os.path.splitext(f)[0] for f in os.listdir(folder)
        if f.lower().endswith(_IMAGE_EXTS)
    )


def _category_map_names(category: str) -> set:
    names = set(list_maps(category))
    if category.lower() == "raid":
        names = {
            re.sub(r" Act\s*\d+$", "", name, flags=re.IGNORECASE).strip()
            for name in names
        }
    return names


def list_story_maps() -> list:
    """Return Story map names discoverable from the editable asset folders.

    Assets/map/Story explicitly categorizes full-map images. For the
    folder-per-map name crops in Assets/maps, unknown folders are treated as
    Story maps unless another category identifies them as Raid/Event/etc.
    """
    story_names = set(list_maps("Story"))
    other_category_names = set()
    for category in list_categories():
        if category.lower() != "story":
            other_category_names.update(
                name.casefold() for name in _category_map_names(category))

    if os.path.isdir(REFERENCE_MAPS_DIR):
        story_names.update(
            name for name in os.listdir(REFERENCE_MAPS_DIR)
            if os.path.isdir(os.path.join(REFERENCE_MAPS_DIR, name))
            and name.casefold() not in other_category_names
        )
    return sorted(story_names, key=str.casefold)


def list_raid_maps() -> list:
    """Return Raid map names, normalizing per-act full-map image filenames."""
    return sorted(_category_map_names("Raid"), key=str.casefold)


def map_image_data_uri(category: str, name: str) -> str:
    folder = os.path.join(MAPS_DIR, category)
    if not os.path.isdir(folder):
        return ""
    for filename in os.listdir(folder):
        stem, ext = os.path.splitext(filename)
        if stem != name or ext.lower() not in _IMAGE_EXTS:
            continue
        path = os.path.join(folder, filename)
        if os.path.isfile(path):
            mime = "image/png" if ext.lower() == ".png" else "image/jpeg"
            with open(path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("ascii")
            return f"data:{mime};base64,{b64}"
    return ""
