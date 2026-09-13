# Atelier 1.0.3

Private review candidate. The visual upgrade introduces canonical web/native palette roles, local landscape scenery, more compact workspace layouts and whole-stage fitting for exactly recognized native image-occlusion templates. Read the [changelog](CHANGELOG-1.0.3.md), [installation and recovery](INSTALL-1.0.3.md), [current audit](AUDIT-1.0.3.md), [asset provenance](ASSET-PROVENANCE-1.0.3.md) and [owner release actions](MANUAL_ACTIONS_REQUIRED.md). Historical reports are not current acceptance evidence.

Organize, create, and study in Anki. Atelier includes a focused library, Card Studio, Exam Studio, customizable home widgets, twelve visual worlds, and a quieter reviewer.

## Preserved from 1.0.2

**Study whole folder → Shuffle between lectures** uses Anki's native display-order options to mix eligible cards across the selected folder's lecture decks. The card's lecture context remains available. A shared parent preset is copied before changing its three ordering fields; unrelated decks and individual-lecture presets are left alone.

This is a **saved, undoable native ordering change**—not an independent mock or a temporary queue. New/review mixing, limits, learning timing and sibling burying still apply. Normal review ratings affect scheduling. Read `INSTALL-1.0.2.md` before relying on the new order.

## Install

Use the paired `Atelier-1.0.3.ankiaddon` in **Tools → Add-ons → Install from file**, then restart. Do not delete an existing Atelier installation before updating. Keep standalone Sprout and Workshop disabled; their engines are bundled. Back up your collection, Atelier's `user_files`, and the complete profile-local `exam_sprout` and `workshop` folders.

## Compatibility

The preserved folder-order contract targets Anki 26.08.1. This candidate has actual Windows Anki 26.05 Home/Widgets, stock image-occlusion, native folder scheduling and AddonManager update tests in isolated synthetic profiles. These limited tests are not full host acceptance. macOS, physical remotes, every card/media template and live GPU Pip remain unverified. See the current audit for the exact coverage and display-scale limitations.

## Development and verification

This source kit includes the exact runtime, original separately hardened assessment/authoring tests, current tests, packaging scripts, baseline hashes and verification evidence. `src/` is the add-on root. Do not install the entire repository as the add-on folder.

```sh
python verify_release.py
python tools/generate_design.py --check
python package_103.py
python tools/bundle_evidence.py --proof-dir verification
```

Install `requirements-dev.txt` and Playwright Chromium; set `PYTHONPATH` to this repository's `test_support` directory. `ATELIER_TEST_BROWSER` can select an installed Chromium executable. The portable adapter resolves fixture scenery locally. Keep a temporary directory supporting fsync. Original native-interface tests use explicit stand-ins; separately labelled native tools run only isolated generated profiles. Screenshots contain synthetic records.

Current results and limitations: `AUDIT-1.0.3.md`. Installer verification and hashes: `dist/Atelier-1.0.3-Build.json`, `dist/Atelier-1.0.3-Files.json`, and the paired checksum record. Historical reports in this kit are not current verification.

## Privacy and licenses

No telemetry or automatic publication. Optional authoring-provider requests require their existing explicit setup/consent. Anki Sync does not synchronize all local exam/source records or widgets; keep separate backups. Retain `src/LICENSE`, all bundled component licenses and asset notices. No font files are distributed.

## GitHub and publishing

The owner-authorized private repository is https://github.com/AAAAAAwd899/Atelier. No AnkiWeb listing exists. `site/` contains unpublished information with no invented code or public download. GitHub verification cannot publish a website, release or AnkiWeb update. The future numeric listing identity and migration require verification and exact owner approval.
