# Atelier 1.0.2

Organize, create, and study in Anki. Atelier includes a focused library, Card Studio, Exam Studio, customizable home widgets, twelve visual worlds, and a quieter reviewer.

## This update

**Study whole folder → Shuffle between lectures** uses Anki's native display-order options to mix eligible cards across the selected folder's lecture decks. The card's lecture context remains available. A shared parent preset is copied before changing its three ordering fields; unrelated decks and individual-lecture presets are left alone.

This is a **saved, undoable native ordering change**—not an independent mock or a temporary queue. New/review mixing, limits, learning timing and sibling burying still apply. Normal review ratings affect scheduling. Read `INSTALL-1.0.2.md` before relying on the new order.

## Install

Use the paired `Atelier-1.0.2.ankiaddon` in **Tools → Add-ons → Install from file**, then restart. Do not delete an existing Atelier installation before updating. Keep standalone Sprout and Workshop disabled; their engines are bundled. Back up your collection, Atelier's `user_files`, and the complete profile-local `exam_sprout` and `workshop` folders.

## Compatibility

Inspected API target: Windows desktop Anki 26.08.1 with its standard editor. The original release had user-reported visual/primary acceptance; this changed update still needs native Windows acceptance. macOS is an unverified trial target. Physical remotes, the native Rust scheduling transaction, full card/media/IO compatibility and GPU Pip were not executed in this build environment. Do not convert automated tests into a universal compatibility claim.

## Development and verification

This source kit includes the exact runtime, original separately hardened assessment/authoring tests, current tests, packaging scripts, baseline hashes and verification evidence. `src/` is the add-on root. Do not install the entire repository as the add-on folder.

```sh
python verify_release.py
python tests/render_102.py
python tests/build_promo_102.py
python package_102.py
```

Requires Python, pytest, Playwright, Pillow, BeautifulSoup, protobuf, Node.js and Chromium. The harness defaults to `/usr/bin/chromium`. Use a temporary directory supporting fsync; the build environment used `TMPDIR=/dev/shm/atelier-102-tests`. Test fixtures do not open your real Anki profile. Original native-interface contracts use explicit stand-ins. The screenshot renderer uses sample records, not your collection.

Current results and limitations: `AUDIT-1.0.2.md`. Installer verification and hashes: `dist/Atelier-1.0.2-Build.json`, `dist/Atelier-1.0.2-Files.json`, and checksum record. Historical reports in this kit are not the current verification.

## Privacy and licenses

No telemetry or automatic publication. Optional authoring-provider requests require their existing explicit setup/consent. Anki Sync does not synchronize all local exam/source records or widgets; keep separate backups. Retain `src/LICENSE`, all bundled component licenses and asset notices. No font files are distributed.

## GitHub and publishing

No GitHub repository or AnkiWeb listing was created by this task. The connected GitHub account exposes no repositories at present. `CODEX-GITHUB-HANDOFF.md` describes the authenticated repository/release workflow once the owner supplies the destination and visibility. Do not invent a support URL or installation code, or overwrite unrelated repository content.
