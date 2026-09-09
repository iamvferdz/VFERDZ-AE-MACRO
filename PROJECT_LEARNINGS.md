# VFERDZ-AE-MACRO — Project Study and Maintenance Notes

This repository is an open-source automation app for the Roblox game Anime Expeditions. It is not a memory-hacking or injection-based bot. Instead, it uses image matching, screen capture, mouse/keyboard input, and a docked game window to automate gameplay.

The project is clearly designed as a user-facing macro tool with a polished dashboard, task queue, macro templates, challenge automation, Discord reporting, and self-updating release support.

## 1. What this project is

From the README and docs:

- It is a free, open-source auto-farm macro for Anime Expeditions.
- It is vision-based: screen capture + image matching + OCR + input simulation.
- It uses a docked Roblox window inside the macro UI on Windows.
- It tries to automate the full Story / Raid / Expedition loop.
- It stores most reference assets in `Assets/` so users can replace or add images without rebuilding the app.

This is a real application built for game automation, not a tiny throwaway script. It has:

- a desktop GUI
- window docking logic for Roblox
- hotkeys and a task queue
- challenge automation
- pre-start and battle phase action blocks
- Discord webhook support
- update checks and release packaging
- tests for logic and structural checks

## 2. High-level architecture

The repo is organized around a few major areas:

- `main.py` — main application entry point and API bridge
- `core/` — automation engine, image matching, input, OCR, windows, runner logic, settings, updater, etc.
- `ui/` — frontend HTML/CSS/JS rendered inside the app
- `Assets/` — reference templates and map images
- `Paths/` — default saved walk paths
- `tools/` — utility scripts for scraping/wiki-related data
- `tests/` — Python unit tests

### Core concepts

1. Vision-driven automation
   - `core/vision.py` is centrally important.
   - It matches reference images against live Roblox screenshots using OpenCV.
   - It supports grayscale matching, scale multipliers, threshold settings, and multiple image variants per target.
   - This allows the macro to recognize UI buttons and labels without hardcoding every pixel or using game-state memory APIs.

2. Fixed coordinate/reference space
   - The code defines a reference game viewport size (for example, 1152x756).
   - All stored coordinates and saved positions are normalized to that frame.
   - Then the code translates them back to actual screen coordinates for the running game window.
   - This helps keep recordings and saved positions portable across window sizes and monitor scaling.

3. Runner loop
   - `core/runner.py` contains the actual macro execution logic.
   - It handles the run cycle: lobby, task selection, pre-start setup, battle loop, victory/defeat handling, retries, challenge logic, and recovery.
   - It is built from multiple modules like:
     - `runner_blocks.py`
     - `runner_challenge.py`
     - `runner_expedition.py`
     - `runner_shop.py`
     - `runner_fuel.py`
     - `runner_bounty.py`
     - `runner_crafting.py`

4. Docking and window management
   - `core/dock.py` and related `window*.py` modules manage embedding or positioning Roblox inside the app window.
   - On Windows, the macro can dock Roblox as a child window inside its own GUI.
   - On macOS, it cannot fully embed another app's window, so it arranges the game beside the app instead.

5. Input abstraction
   - Input is split into mouse and keyboard layers.
   - `core/mouse.py`, `core/keyboard.py`, and `core/_input_win.py` / `_input_mac.py` provide platform-specific automation input.
   - This isolates game input from the rest of the engine.

## 3. Main features and product behavior

The README describes the project as having a fairly advanced macro feature set:

- Task queue for Story / Raid / Expedition tasks
- Repeat farming with automatic recovery
- Pre Start block builder (Macro Manager)
- Walk path recorder and replay
- Record block for complex actions
- Victory/defeat detection and Discord match reports
- Win/loss stats and history
- Global hotkeys
- Daily and regular challenge automation
- Multi-scale image matching
- Overridable asset images for button matching
- Themes and UI settings
- Self-updating launcher

This is more than a simple clicker. It is a full macro management app for a specific game.

## 4. How the macro actually works

### 4.1 Image matching

The project does not rely on direct memory reading. Instead, it detects on-screen states by matching reference images from `Assets/ui` or related folders. Examples from `core/vision.py` show:

- grayscale matching is preferred over color matching because game UI varies in brightness and color gradients
- threshold enforcement is used to avoid false positives
- multiple scales are tried automatically
- each target can have multiple image variants in the same folder

This is a very standard “computer vision automation” approach.

### 4.2 Window and screen normalization

A major project design choice is the “reference space” model. The code tries to keep everything in a consistent viewport size regardless of actual OS DPI, window size, or scaling differences.

This design matters because:

- Roblox can render at slightly different sizes
- the app needs to work across monitor scaling, Windows DPI, and macOS Retina widths
- saved click points and template recordings should remain valid even when the real window shape changes

### 4.3 Macro operations and templates

The UI has a Macro Manager where users can create operations such as:

- Place Unit
- Click / Send Key
- Walk Path
- Record
- Once
- Wait / Wave-based logic

These are saved as templates and assigned to tasks or challenges. This is how the project makes automation reusable instead of hardcoded per map.

### 4.4 Battle loop and recovery

`core/runner.py` is the engine that tracks a run and manages the match. It handles:

- launch flow
- lobby detection
- map/stage selection
- pre-start config and placement
- battle actions
- win/loss detection
- recovery from failures
- retries
- stats reporting

The code comments mention automatic retry and recovery flows. The README also clearly calls out repeated stage farming and automatic recovery when a battle gets stuck or a click is missed.

### 4.5 Discord and stats reporting

The project includes optional Discord webhooks and result screenshots. It has:

- webhook integration
- screenshot capture of match results
- win/loss cards
- session and all-time stats

This means the app is designed to be “operationally complete,” not just a simple auto-farm utility.

## 5. Project conventions and maintainership patterns

### Asset-first design

The README says the `Assets/` folder is deliberately kept outside the executable so users can edit it safely. This is key for maintainability:

- custom image replacement without a rebuild
- user-supplied crops and variants
- update-safe behavior where new assets are added without overwriting custom ones

This is a good pattern for any automation tool built around image matching.

### Update mechanisms

The app supports self-updating via GitHub release checks. It can:

- detect a newer version automatically
- show release notes
- offer update and restart inside the app
- preserve `settings.json`, templates, walk paths, and custom `Assets/` changes

This is likely important because the creator may be absent; the repo needs to keep working as a self-maintaining tool.

### Release and CI structure

`CONTRIBUTING.md` states that:

- GitHub Actions handles release builds on annotated semantic-version tags (`vX.Y.Z`)
- local checks include:
  - `python -m pytest tests/`
  - `node --check ui/app.js`
- the project expects Python 3.10+ and Node.js for validation

This indicates a relatively mature release discipline for an open-source project.

## 6. Running and developing the project

### Local execution

From the docs and README:

- Windows source install:
  - clone repo
  - create venv
  - install `requirements.txt`
  - run `python main.py`
- CLI diagnostics mode:
  - `python main.py --test`

### Important environment requirements

- Python 3.10+
- Microsoft Edge WebView2 Runtime (Windows)
- Tesseract OCR for stats/reward reading
- Roblox + Anime Expeditions

The project also explicitly notes that some features require the Roblox window to be intact and visible, with no overlaying windows moving it during automation.

### Testing signals

The repo has a large `tests/` directory with many focused test files such as:

- `test_runner_*`
- `test_vision.py`
- `test_ocr.py`
- `test_window_win.py`
- `test_updater.py`
- `test_macro_coords.py`
- `test_detect.py`

This shows the project is trying to validate logic and automation behavior in a modular, test-driven way.

## 7. Important caveats and risks

This project is operating in a grey area from a game-policy and automation perspective. The docs are honest about it:

- It is an unofficial automation tool.
- Game updates can break button detection or UI flow.
- It may violate Roblox/game rules depending on the game’s policy and how it is used.
- It should be tested with short runs before unattended farming.
- Never share sensitive secrets such as webhook URLs or `settings.json`.

From a maintenance perspective, these caveats matter because any update to the game can quickly break the macro.

## 8. Main technical takeaways

The project is built around several patterns that matter if someone wants to continue or modernize it:

1. Use image matching, not memory reading
   - This is the project’s core identity.
   - It is intentionally not hooking into the game process.

2. Normalize coordinate systems aggressively
   - The app is designed around fixed reference dimensions and runtime scaling.
   - This makes recordings and saved positions portable.

3. Keep assets external and editable
   - This is a maintainability feature, not an afterthought.
   - It reduces the need for rebuilds whenever a UI asset needs updating.

4. Separate logic into runner modules
   - The codebase is already modularized around match phases and task types.
   - That makes it easier to extend behavior or fix game-specific UI changes.

5. Use release-oriented workflows
   - The repo expects GitHub release tagging and CI validation.
   - Good for long-term maintenance by a community.

## 9. Recommended maintenance direction for an inactive upstream

If the original creator is no longer active, the most reasonable continuation strategy is:

- keep the app as a release-driven open-source project
- preserve the `Assets/` editability model
- maintain compatibility with the latest Roblox UI changes by updating image templates and detection logic
- keep tests running for pure logic modules
- validate the app with small live test runs before trust-based automation
- document any game update breakage in one place, along with new asset replacements

A practical maintainer checklist:

- Check GitHub issues and pull requests regularly
- Update templates when Anime Expeditions UI changes
- Validate `requirements.txt` and any OS-specific dependencies
- Rebuild or verify release artifacts after significant changes
- Keep `VERSION` and tags consistent for release updates
- Document any new challenge map or macro behavior in the user guide

## 10. Short conclusion

This repository is a serious, real-world automation project rather than a simple script. It blends:

- GUI engineering
- computer vision
- automation input
- game-state recognition via screenshots
- release packaging
- optional reporting and metrics
- user-configurable macro flows

The project architecture is sound for its purpose, and its maintainability is helped by the asset system, modular runner design, and release workflow. If this repo needs fresh updates, the right path is to treat it as a live automation app that must adapt to game UI changes, not just as a static script dump.

## 11. Helpful entry files to read next

If you want to keep digging, these are the best next reads:

- `README.md` — product overview and release/install story
- `docs/USER_GUIDE.md` — day-to-day usage and practical automation advice
- `main.py` — app bootstrap, hotkeys, and main UI wiring
- `core/vision.py` — recognition and template matching infrastructure
- `core/runner.py` — actual macro execution loop and battle automation
- `core/dock.py` — Roblox window embedding/docking behavior
- `CONTRIBUTING.md` — dev workflow and contribution expectations
- `tests/` — validation patterns and edge-case detection

This file is meant to be a reference note for future maintainers and contributors working on the project.
