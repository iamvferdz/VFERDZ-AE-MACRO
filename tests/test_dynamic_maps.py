import main
from core import maps


def _make_asset_dirs(root, monkeypatch):
    assets = root / "Assets"
    (assets / "map" / "Story").mkdir(parents=True)
    (assets / "map" / "Raid").mkdir()
    (assets / "maps").mkdir()
    monkeypatch.setattr(maps, "MAPS_DIR", str(assets / "map"))
    monkeypatch.setattr(maps, "REFERENCE_MAPS_DIR", str(assets / "maps"))


def test_story_and_raid_map_names_are_discovered_from_asset_folders(tmp_path, monkeypatch):
    _make_asset_dirs(tmp_path, monkeypatch)
    assets = tmp_path / "Assets"
    (assets / "map" / "Story" / "New Story.png").write_bytes(b"story")
    (assets / "map" / "Raid" / "New Raid Act 1.PNG").write_bytes(b"raid")
    (assets / "maps" / "New Story").mkdir()
    (assets / "maps" / "New Raid").mkdir()
    (assets / "maps" / "Another Story").mkdir()

    assert maps.list_story_maps() == ["Another Story", "New Story"]
    assert maps.list_raid_maps() == ["New Raid"]


def test_task_map_catalog_includes_new_maps_without_dropping_defaults(tmp_path, monkeypatch):
    _make_asset_dirs(tmp_path, monkeypatch)
    assets = tmp_path / "Assets"
    (assets / "map" / "Story" / "New Story.png").write_bytes(b"story")
    (assets / "map" / "Raid" / "New Raid Act 1.png").write_bytes(b"raid")

    catalog = main.Api.__new__(main.Api).list_task_map_catalog()

    assert "New Story" in catalog["story"]
    assert "School Grounds" in catalog["story"]
    assert "New Raid" in catalog["raid"]
    assert "Snowy Castle" in catalog["raid"]


def test_global_story_settings_and_assignment_include_new_story_map(tmp_path, monkeypatch):
    _make_asset_dirs(tmp_path, monkeypatch)
    (tmp_path / "Assets" / "map" / "Story" / "New Story.png").write_bytes(b"story")
    state = {"global_story": {"maps": {}}}
    monkeypatch.setattr(main.cfg, "load", lambda: state)
    monkeypatch.setattr(main.cfg, "update", lambda patch: state.update(patch))
    monkeypatch.setattr(main.tpl, "template_exists", lambda _name: True)
    monkeypatch.setattr(
        main.tpl, "load_template",
        lambda _name: {"blocks": {"prestart": [], "battle": []}})
    api = main.Api.__new__(main.Api)

    settings = api.get_global_story_settings()
    saved = api.set_global_story_map_macro("New Story", "New Story Farm")

    assert "New Story" in settings["maps"]
    assert "New Story" in settings["missing_maps"]
    assert saved["ok"] is True
    assert state["global_story"]["maps"]["New Story"]["macro"] == "New Story Farm"


def test_map_picker_loads_uppercase_image_extensions(tmp_path, monkeypatch):
    _make_asset_dirs(tmp_path, monkeypatch)
    image_path = tmp_path / "Assets" / "map" / "Story" / "New Story.PNG"
    image_path.write_bytes(b"image")

    assert maps.list_maps("Story") == ["New Story"]
    assert maps.map_image_data_uri("Story", "New Story").startswith("data:image/png;base64,")
