# Atelier 1.0.5

Private review candidate. Version 1.0.5 adds an optional guided tour, declares the minimum Anki host, and updates the isolated PDF parser with resource-limit fixes. It retains the 1.0.4 Onigiri layout and recent-study ordering and the full visual and workflow upgrade. Read the [current changelog](CHANGELOG-1.0.5.md), [installation guide](INSTALL-1.0.5.md), [current audit](AUDIT-1.0.5.md), [asset provenance](ASSET-PROVENANCE-1.0.3.md) and [owner release actions](MANUAL_ACTIONS_REQUIRED.md). Historical reports are not current acceptance evidence.

Organize, create, and study in Anki. Atelier includes a focused library, Card Studio, Exam Studio, customizable home widgets, seventeen visual worlds, six world-matched companion families, and a quieter reviewer.

Card Studio organizes source material into card sets for a course, lecture, chapter, or topic. Import slides, PDFs, images, notes, or text; choose the exact slide or page from the ordered rail; build questions, clozes, image cards, or image-occlusion masks beside the source; then review drafts before adding them to a selected Anki deck. The Study desk shows the current study scope and lets a learner edit or start that exact folder selection. Exam Studio accepts multiple parent folders in one exam, including two separate courses, while preserving each deck’s cards and schedule.

## Preserved from 1.0.2

**Study whole folder → Shuffle between lectures** uses Anki's native display-order options to mix eligible cards across the selected folder's lecture decks. The card's lecture context remains available. A shared parent preset is copied before changing its three ordering fields; unrelated decks and individual-lecture presets are left alone.

This is a **saved, undoable native ordering change**—not an independent mock or a temporary queue. New/review mixing, limits, learning timing and sibling burying still apply. Normal review ratings affect scheduling. Read `INSTALL-1.0.2.md` before relying on the new order.

## Install

Use the paired `Atelier-1.0.5.ankiaddon` in **Tools → Add-ons → Install from file**, then restart. Do not delete an existing Atelier installation before updating. Keep standalone Sprout and Workshop disabled; their engines are bundled. Back up your collection, Atelier's `user_files`, and the complete profile-local `exam_sprout` and `workshop` folders.

## Compatibility

Current Windows tests used Anki 26.09.3: actual AddonManager update/preservation, all tour steps, native folder scheduling/Undo and stock image-occlusion rendering/grading/Undo in isolated synthetic profiles. These bounded checks do not establish universal add-on compatibility, macOS support, physical remotes or live GPU Pip. See the current audit for exact coverage and display/capture limitations.

## Development and verification

This source kit includes the exact runtime, original separately hardened assessment/authoring tests, current tests, packaging scripts, baseline hashes and verification evidence. `src/` is the add-on root. Do not install the entire repository as the add-on folder.

```sh
python verify_release.py
python tools/generate_design.py --check
python package_105.py
```

Install `requirements-dev.txt` and Playwright Chromium; set `PYTHONPATH` to this repository's `test_support` directory. `ATELIER_TEST_BROWSER` can select an installed Chromium executable. The portable adapter resolves fixture scenery locally. Keep a temporary directory supporting fsync. Original native-interface tests use explicit stand-ins; separately labelled native tools run only isolated generated profiles. Screenshots contain synthetic records.

Current results and limitations: `AUDIT-1.0.5.md`. Installer verification and hashes: `dist/Atelier-1.0.5-Build.json`, `dist/Atelier-1.0.5-Files.json`, and the paired checksum record. Use the version-matched build receipt for current counts; earlier release reports remain historical.

## Privacy and licenses

No telemetry or automatic publication. Optional authoring-provider requests require their existing explicit setup/consent. Anki Sync does not synchronize all local exam/source records or widgets; keep separate backups. Retain `src/LICENSE`, all bundled component licenses and asset notices. No font files are distributed.

## GitHub and publishing

The owner-authorized private repository is https://github.com/AAAAAAwd899/Atelier. No AnkiWeb listing exists. `site/` contains unpublished information with no invented code or public download. GitHub verification cannot publish a website, release or AnkiWeb update. The future numeric listing identity and migration require verification and exact owner approval.
