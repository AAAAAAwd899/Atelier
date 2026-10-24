# Atelier 1.0.8

Version 1.0.8 adds a searchable folder destination browser, From/To confirmation, a direct Move menu action, and reliable navigation to the destination after Anki refreshes. It retains searchable access to original add-on menu commands. It retains the world-matched countdown/stopwatch, 13-step tour, Getting started guide and prepared AnkiWeb listing kit. Read the [changelog](CHANGELOG-1.0.8.md), [installation guide](INSTALL-1.0.8.md), [audit](AUDIT-1.0.8.md), [asset provenance](ASSET-PROVENANCE-1.0.3.md) and [remaining publication actions](MANUAL_ACTIONS_REQUIRED.md). Historical reports are not current acceptance evidence.

Organize, create, and study in Anki. Atelier includes a focused library, Card Studio, Exam Studio, customizable home widgets, seventeen visual worlds, six world-matched companion families, and a quieter reviewer.

Card Studio organizes source material into card sets for a course, lecture, chapter, or topic. Import slides, PDFs, images, notes, or text; choose the exact slide or page from the ordered rail; build questions, clozes, image cards, or image-occlusion masks beside the source; then review drafts before adding them to a selected Anki deck. The Study desk shows the current study scope and lets a learner edit or start that exact folder selection. Exam Studio accepts multiple parent folders in one exam, including two separate courses, while preserving each deck’s cards and schedule.

## Preserved from 1.0.2

**Study whole folder → Shuffle between lectures** uses Anki's native display-order options to mix eligible cards across the selected folder's lecture decks. The card's lecture context remains available. A shared parent preset is copied before changing its three ordering fields; unrelated decks and individual-lecture presets are left alone.

This is a **saved, undoable native ordering change**—not an independent mock or a temporary queue. New/review mixing, limits, learning timing and sibling burying still apply. Normal review ratings affect scheduling. Read `INSTALL-1.0.2.md` before relying on the new order.

## Install

Use the paired `Atelier-1.0.8.ankiaddon` in **Tools → Add-ons → Install from file**, then restart. Do not delete an existing Atelier installation before updating. Keep standalone Sprout and Workshop disabled; their engines are bundled. Back up your collection, Atelier's `user_files`, and the complete profile-local `exam_sprout` and `workshop` folders.

## Compatibility

Current Windows tests used Anki 26.09.3: actual AddonManager update/preservation, all tour steps, native folder scheduling/Undo and stock image-occlusion rendering/grading/Undo in isolated synthetic profiles. These bounded checks do not establish universal add-on compatibility, macOS support, physical remotes or live GPU Pip. See the current audit for exact coverage and display/capture limitations.

## Development and verification

This source kit includes the exact runtime, original separately hardened assessment/authoring tests, current tests, packaging scripts, baseline hashes and verification evidence. `src/` is the add-on root. Do not install the entire repository as the add-on folder.

```sh
python verify_release.py
python tools/generate_design.py --check
python package_107.py
```

Install `requirements-dev.txt` and Playwright Chromium; set `PYTHONPATH` to this repository's `test_support` directory. `ATELIER_TEST_BROWSER` can select an installed Chromium executable. The portable adapter resolves fixture scenery locally. Keep a temporary directory supporting fsync. Original native-interface tests use explicit stand-ins; separately labelled native tools run only isolated generated profiles. Screenshots contain synthetic records.

Current results and limitations: `AUDIT-1.0.8.md`. Installer verification and hashes: `dist/Atelier-1.0.8-Build.json`, `dist/Atelier-1.0.8-Files.json`, and the paired checksum record. Use the version-matched build receipt for current counts; earlier release reports remain historical.

## Privacy and licenses

No telemetry or automatic publication. Optional authoring-provider requests require their existing explicit setup/consent. Anki Sync does not synchronize all local exam/source records or widgets; keep separate backups. Retain `src/LICENSE`, all bundled component licenses and asset notices. No font files are distributed.

## GitHub and publishing

Source and support: https://github.com/AAAAAAwd899/Atelier. The owner authorized public source visibility for support. Use [GitHub Issues](https://github.com/AAAAAAwd899/Atelier/issues/new/choose) without attaching private collections or source material. There is no AnkiWeb listing or numeric code yet. [Prepared listing material](listing/ankiweb-1.0.8/START-HERE.md) includes real screenshots, ready-to-paste descriptions and compatibility fields. The distributable installer is supplied separately in the owner handoff; do not install this repository as an add-on. No website deployment or public binary release is performed by these source changes. Future listing migration requires the real identity and verification.
