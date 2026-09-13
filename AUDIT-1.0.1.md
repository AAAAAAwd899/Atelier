# Atelier 1.0.1 — Reviewer and remote-controls verification

**Decision:** cumulative installable maintenance update for controlled native verification. The original 1.0.0 user acceptance is not a claim that this changed build or any physical remote has been accepted. Nothing has been published to AnkiWeb.

## Baseline and scope

The source began as an exact extraction of the delivered Atelier 1.0.0 installer. Every original installer entry matched before changes. `baseline-1.0.0.json` binds those bytes; `patch-101-changes.json` binds the reviewed modifications/additions. No older development branch was substituted. The installation identity remains `daedalus_atelier` and the product name is Atelier.

The user's latest message contained only an ImageDisplayed marker, not an accessible screenshot. The missing target was requested again. This patch therefore does **not** claim to diagnose that unseen image or repair an incorrectly authored source mask. It corrects independently reproduced spacing behavior and conservative rendering boundaries.

## Findings and implementation

| Area | Evidence and change |
|---|---|
| Duplicate top spacing | The baseline fixture applied a 78px Onigiri header offset both through body padding and an inline important card margin. At a 1100×430 viewport the document extended to 459px. The patch owns the eligible reading card's top margin reversibly and reserves the header offset once. Current medium-question checks fit at the same viewport in all twelve palettes. |
| Render lifecycle | Eligible native-review text cards register presentation callbacks after card insertion and after showing, using Anki's documented card/reviewer hooks. Long answers retain native answer-anchor behavior. No preview/IO template injection, stored template edits, card replacement or scheduler hook changes. |
| Short/long transitions | Measure content with ResizeObserver and animation-frame coalescing. Fit short content; leave genuinely long content scrollable. Reset next-question scroll once. User wheel/touch/scroll-key/pointer interaction stops subsequent short-card corrections. A bounded settling window avoids continuously pulling the page back. |
| Custom/mask boundaries | Expanded recognition of legacy IO IDs/fields, positioned overlays, viewport-height/overflow-sensitive templates and explicit protection. Reduced-motion rules no longer cancel arbitrary card animations; media pseudo-elements are no longer removed. Images, masks and canvases retain markup/relative geometry; no automatic zoom, rescaling, wrapping or conversion. |
| Answer controls | Modestly reduce owned footer padding and button minimum height while keeping the original button elements and handlers. Native count labels remain; no moving rating hitboxes. |
| Remote setup access | A native Remote controls dialog from Tools → Atelier and Anki tools, with matching search results. No new reviewer banner, floating controller panel or startup prompt. |
| Connection scope | Keyboard/HID-mode remotes only: the OS pairs Bluetooth or accepts the USB receiver. Native Anki shortcuts remain available. No Bluetooth stack, raw gamepad polling, background device enumeration or claimed hardware identification/battery data. |
| Safe test and assignment | Test button presses only inside the open foreground setup dialog. No card actions there. Assignment is staged, unique, unmodified-key-only, and saved explicitly. Cancel preserves settings. Custom mapping defaults off. |
| Foreground review dispatch | Require the actual main reviewer or native answer bar to have focus, no modal/popup, positive DOM editing permission and a stable card/stage/profile/token. Recheck after asynchronous permission. Existing reveal/rating/replay functions are used; unavailable native ratings are not substituted. No custom reveal-and-grade action. |
| Repeats and editing | Ignore held/autorepeated signals and a 220ms bounce window. Modified system shortcuts, typed-answer/contenteditable fields, practice/editor/other windows and unmapped keys keep their original handling. Closing the dialog removes its filter and deletes its native widget. |

## Fresh cumulative results

Completed UTC: **2026-09-13T03:26:56.534831+00:00**.
Runtime SHA-256: `f6ad381362ece096d6b3264dbd0f204d37dffc066ac250e25e3b5ca7a6ce5f6b`.

| Suite | Passed |
|---|---:|
| Atelier integration, model and preservation | 1087 |
| Original exam engine and quiet-review contracts | 460 |
| Card Studio import/publish/routes | 209 |
| **Python total** | **1756** |
| **Recorded Chromium checks** | **2001** |

No Python failures/errors/skips or uncaught browser page errors occurred in this complete run. Totals include repeated world/viewport/preservation cases, not independent native integrations. The runtime fingerprint was unchanged during the verifier. The 1.0.1 additions are **79 Python checks and 84 browser checks**; previous release totals were not simply carried forward.

New tests exercise duplicate margin reproduction across twelve palettes, short reveal, long scrolling, next-card reset, card-only centering, IO markup/geometry, legacy mask classification/restoration, remote keyboard mapping/duplicates/defaults, native action eligibility, stale replies, profile changes, focus/modifiers/held presses, safe test/cancel/save behavior and cleanup. A separate renderer checks actual Anki tools access and searching for Remote controls.

Native UI tests use explicit Qt stand-ins. Browser tests render the actual current assets with synthetic cards and native-shaped footer controls. Real Windows/macOS, a real Anki collection, physical remotes, Bluetooth pairing and GPU devices were not used. Pip remains on its shipped animated fallback in this environment.

## Test-harness maintenance

Historical freeze checks originally permitted only the 1.0.0 copy/version pass. They now reconstruct exact stored 1.0.0 bytes for their historical comparisons and fail on an undeclared patch hash; new tests exercise the changed behavior and full exact baseline boundaries. No protected engine file is exempted. Version and registration-count assertions account for 1.0.1 and its one new opt-in application filter. The first full browser run stopped on a stale version comment used by an old fixture selector; the current source version was corrected and the **entire verifier was rerun cleanly**. Earlier failures/interruptions are retained and are not counted as passes.

## Visual evidence

Three fresh screenshots bind to this runtime: the short-card reviewer, the actual Remote controls entry in Anki tools and its search result. The reviewer preview uses the real shipped CSS/JS in browser frames with clearly labelled synthetic controls. No image of a native setup dialog or paired remote was fabricated. Unchanged historical 120-world galleries are **not** republished as new screenshots for this patch.

## Preservation and packaging

Every bundled Sprout and Workshop file is byte-identical to the delivered 1.0.0 release, including assessment, masks, source images, publication, saved sessions and Pip. The patch does not modify exam/source data schemas or move data. Only a disabled-by-default `remote` configuration field is added to existing add-on preferences.

`package_101.py` requires matching fresh suite results, exact reviewed patch hashes, current visual evidence, Python parsing, JavaScript syntax, same package identity, no private profile/cache/font files, ZIP CRC and per-file equality. A second archive build must be byte-identical. The extracted installer's runtime fingerprint must match the verifier. Build.json and SHA256 contain output-specific facts. A repeat targeted test against the actual extracted installer is reported separately and not added to these totals.

## Remaining native checks

Test in the user's actual Windows/macOS Anki: short and long questions/answers, legacy/native IO and selected custom templates, Onigiri header offset, footer/autohide/Retina/DPI, typed answers, hardware press/release behavior, remote after clicking Show Answer, mapping while an editor/modal is open, native undo/learning and all original integrations. Test keyboard mode before relying on custom controls. A gamepad-only/proprietary device may require its own adapter; this build does not claim direct support for every remote. macOS remains an unverified trial target.

The missing screenshot must be resent to assess the user's exact visual anomaly. An already-authored misplaced mask is not corrected by a theme-only change.

## Reproduce

```sh
TMPDIR=/dev/shm python verify_release.py
python tests/render_101.py
python package_101.py
```

The default browser executable is `/usr/bin/chromium`. The source kit includes all tests and original engine fixtures. No reproduction command accesses a production profile or publishes anything.

## Host references

- Anki reviewer JavaScript hooks: https://addon-docs.ankiweb.net/reviewer-javascript.html
- Anki 26.08.1 reviewer implementation: https://github.com/ankitects/anki/blob/26.08.1/qt/aqt/reviewer.py
- Anki 26.08.1 review DOM lifecycle: https://github.com/ankitects/anki/blob/26.08.1/ts/reviewer/index.ts
- 8BitDo Micro keyboard-mode FAQ (manufacturer compatibility, not this add-on's hardware verification): https://support.8bitdo.com/faq/micro.html

## Exact-installer repeat check

The distributed source kit was extracted into a fresh directory and its source replaced with the actual installer contents. **158 targeted tests passed**, with no failure or skip, using the new 1.0.1 checks and retained release/lifecycle checks. Installer SHA-256 `fc4b4e0feb13445117f9c5bc3ad966719447e7a901a237941252b0a2744fb8ad` and runtime digest match the complete verifier. These are repeat checks, not added to the cumulative totals and not a second full verifier. See verification/1.0.1/exact-targeted.json and XML/log.
