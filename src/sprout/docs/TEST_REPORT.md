# Exam Sprout 0.10.1 — animation file-lock repair verification

## Scope and identity

Complete replacement installer, package ID `exam_sprout`. Baseline is the actual
attached 0.10.0 installer and matching source, not a reconstructed or mascot-only
build. All baseline files were compared before editing. Runtime differences from
0.10.0 are limited to `companion.py`, the VERSION value in `core.py`, and the human
version in `manifest.json`. All exam/readiness/study/learning/storage code,
JavaScript/CSS, 3D geometry and artwork remain byte-identical.

The immediate defect was reproduced in the user's supplied Windows installer
trace: the old native movie asset was still in use when Anki attempted to remove
the previous add-on folder. Previous releases used QMovie.setFileName.

## What changed

- One owned in-memory QBuffer feeds the native QMovie. The bounded Python file
  read completes and its context closes before the buffer reaches Qt. No runtime
  QMovie filename construction or setFileName remains.
- The compressed payload is capped at 4 MiB. Current tiny animations are under
  1.5 MB each; one selected animation is retained per badge. This is not a total
  process-memory measurement. The existing decoded-frame cache policy is unchanged.
- Action changes detach the decoder before closing/replacing buffer contents.
  Disposing a badge releases its buffer immediately, not just on deferred deletion.
  Late callbacks cannot reopen a disposed badge's files.
- Pause/resume and unchanged-stage updates preserve the current movie/device;
  no added disk read or animation rewind occurs on an ordinary footer remount.
- Missing, invalid, denied, unsupported or oversized animation inputs retain
  still art, stop the return timer and are not repeatedly retried for the same
  stage/action during that badge's lifetime. No error modal is introduced.
- No Anki installer monkeypatch, permission alteration, forced filesystem
  deletion, schema migration or changes to collection scheduling were added.

## Current results

These suites are rerun from a clean extraction of the exact installer by
`tools/verify_release.py`; `Package_Verification.json` records its checksum and
measured outcomes and must exist before delivery.

| Check | Result |
|---|---:|
| Python logic, SQLite and explicit Anki/Qt contract tests | 416 passed |
| New file-handle / buffer / cleanup contract regressions | 33, included above |
| Existing production planner / WebGL checks | 68 passed |
| Existing motion / layout checks | 40 passed |
| Existing assessment / exam / privacy checks | 48 passed |
| Uploaded Atelier front-end checks | 118 passed |
| Browser checks total | 274 passed |
| Animation frames decoded and timing-checked | 2,976 |

The 33 new tests include exact byte/device checks for all twelve native animations,
real Python file-handle closure before decoder handoff, same-device pause/resume,
no re-read across 100 remounts, deletion of a temporary asset copy after loading,
strict detach/close/setData ordering, early cleanup and late callback rejection,
read/decoder/buffer failures, bounded payloads and absence of filename playback.
The removal test exercises Linux filesystem operations with Qt doubles, NOT
Windows sharing semantics. The fixture enforces open/read/close ownership rules
but is not a native Qt animation decoder.

## Limits and publication gate

No Windows COM/send2trash update or real Anki 25.09.5/Qt process ran here. A fresh
PyQt6 6.9.1 installation was attempted but runtime package retrieval failed.
Python tests use Anki/Qt doubles; Chromium renders the actual UI/model with a
synthetic collection bridge. Tests do not certify image-occlusion/audio/template
combinations, FSRS/SM-2 Grade Now learning/undo, or actual hardware frame rate.
The readiness algorithm remains an unvalidated heuristic, not a grade promise.
The supplied Atelier archive is an earlier version than the user's current
0.7.1: 118 browser checks do not certify that new native combination.

The first repair installation must be done after completely closing the old Anki
and restarting in safe mode, because receiving a new installer cannot unlock a
file handle still held by old running code. The failed replacement may have
partially removed old program files; reinstall the complete archive. See
`WINDOWS_UPDATE_RECOVERY.md`. The traceback does not show collection-file damage.

Release candidate. This patch does not clear the existing public-release gate.
AnkiWeb has not been accessed or published; server acceptance is not claimed.

## Reproduce

    python -m pytest -q
    python tools/build.py /path/to/output
    python tools/verify_release.py /path/to/output --atelier /path/to/Atelier.ankiaddon --baseline /path/to/Exam_Sprout_0.10.0.ankiaddon

Primary API references: Qt 6.9 QMovie device playback and QBuffer ownership/open
semantics; Anki's official troubleshooting safe-mode directions. Current source
archive includes the repair, tests and recovery guide. Older reports are historical.
