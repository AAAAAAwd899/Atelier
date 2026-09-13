# Atelier 1.0.2 — whole-folder shuffle verification

## Decision

Actual cumulative installer for controlled native acceptance. The new parent-order behavior is implemented and tested against the inspected Anki interface contract. The native Anki/Rust scheduler was not installed or executed here. No GitHub or AnkiWeb publication occurred.

## Starting point and modifications

Every source runtime byte matched the delivered 1.0.1 installer before editing. `baseline-1.0.1.json` binds the starting files. `patch-102-changes.json` permits only the exact new changes: folder_study.py; its guarded integration route; the whole-folder confirmation UI; version labels and consumer guide/release notes. No file was removed.

All **72 bundled Sprout files and 80 bundled Workshop files remain byte-identical to 1.0.1**. The remote engine, reviewer layout/CSS and mask classifier remain unchanged. A reviewer version string changed, not geometry or grading behavior.

## Native order contract

The explicit parent confirmation chooses Shuffle by default or Keep current. Shuffle sets only:

- `new_card_gather_priority = NEW_CARD_GATHER_PRIORITY_RANDOM_CARDS`;
- `new_card_sort_order = NEW_CARD_SORT_ORDER_RANDOM_CARD`;
- `review_order = REVIEW_CARD_ORDER_RANDOM`.

It reads a fresh `get_deck_configs_for_update` snapshot and builds a native `UpdateDeckConfigsRequest`. A shared current preset is deep-copied with ID 0, and the native backend assigns it only to the selected parent. A unique preset retains its ID. Already-random order returns without another options write or copy. No APPLY_TO_CHILDREN, deleted configs, filtered deck, queue interception, card repositioning, SQL mutation or rescheduling request is used.

Every other selected-preset field, protobuf unknown field, opaque addon data, FSRS/custom-scheduling/global flag and per-deck limit is copied from the snapshot. Inactive today-only limits are cleared in the request so the native endpoint cannot reactivate a stale limit. Active zero values remain present. Card positions, note content, due dates and intervals are not edited.

The saved options update and deck selection use Anki's native CollectionOp and custom undo grouping. Current-order selection makes no option changes. A write failure does not open review; a rare later selection or undo-group failure accurately says that the order was already saved. There is no attempt to undo unrelated work automatically.

Display order is persistent, not a session-only random queue. New and review categories retain their configured interleaving; learning timing and sibling rules remain native. Native randomness can show repeated lectures or a stable same-day order. Random reviews no longer prioritize oldest-due cards. A copied preset no longer follows later edits to the old shared preset; this is disclosed in the guide.

## Fresh cumulative execution

Completed UTC: **2026-09-13T04:17:13.097157+00:00**.

Runtime SHA-256: `d0b4a2ed5f5999454fe21311b54afda4ef5dbfd0e743e9f56596446e90871f1c`.

| Suite | Passed |
|---|---:|
| Atelier / integration / preservation | 1141 |
| Original exam engine and quiet review | 460 |
| Card Studio import/publish/routes | 209 |
| **Python total** | **1810** |
| **Recorded Chromium checks** | **2098** |

Zero failed/skipped Python tests and zero uncaught browser page errors in the complete run. Fresh addition: **54 Python cases and 97 browser checks**. Counts include repeated palettes/viewports; they are not independent native integrations. Runtime fingerprint stayed unchanged through the verifier.

### What the new tests execute

Python tests use real google.protobuf serialization with a contract schema and explicit native-manager/Qt doubles. They check shared/unique presets, partial/repeated settings, unknown data, inactive/active/zero limit presence, all copied global flags, no mutation of the source snapshot, clone-name collisions, missing/filtered/renamed/leaf rejection, missing native capability, current-order no-write, undo grouping, late failures and the actual guarded controller dispatch. Two sample review cards verify that `card_info` reads each card's own deck rather than the selected parent.

Browser checks execute the shipped frontend, actual buttons and a controlled bridge: twelve worlds, default choice, no write on opening/cancel, both order payloads, visible persistent-setting explanation, error retention/retry, pending-click protection, original individual-lecture route, five small/wide viewport sizes, real mouse-wheel scrolling and footer center hit-testing. No test runs a physical remote, native queue, live collection or external provider.

### Bugs found during development

The first browser run checked the text inside a collapsed disclosure as if it were visible; the test now opens the actual disclosure. A second assertion used “Session 5” instead of the fixture's original “Section 5”; the expected exact ID/path was corrected, without changing production data. The next run exposed a genuine new UI bug: the successful reply attempted to close the confirmation while its own busy guard was still active. Successful same-dialog completion now uses the existing guarded force-close path, and delayed/error cases still keep the interface safe. A complete cumulative verification followed those corrections.

Historical freeze tests now reconstruct the same original 1.0.0 baseline from exact declared current hashes, rather than broadly excluding changed files. Separate 1.0.2 hashes bind the new change scope against 1.0.1. Protected embedded code is still byte-checked.

## Current visual evidence

Six fresh raw screenshots and six designed portfolio boards show **Forest, Rose Quartz, Glacier, Tidal, Midnight and Ember** across the actual home, authoring, new folder confirmation, practice, widgets and reviewer. The board surrounds the screenshot; it does not generate or redraw its UI. A contact sheet and an interactive portfolio HTML include full-screenshot views. The source renderer and screenshot hashes are included. These are browser captures with fictional/sample records—not native Windows/macOS evidence and not a GPU performance test.

A portfolio helper initially replaced color-token strings after inserting a base64 image, inadvertently corrupting the image URI. It was corrected to insert image bytes last; all final images are decoded and gallery controls tested before packaging. This was an asset-generation issue, not a runtime change.

## Native/publication limits

Still test inside actual Anki 26.08.1: native preset creation/update/Undo, resulting review sequences, learning timing, parent limits, renamed/deleted folders, sync to other clients and existing reviewer/IO/remote behavior. macOS remains a controlled trial. No new card-rendering or physical-device compatibility claims are made.

The connected GitHub account is `AAAAAAwd899`; a fresh full accessible-repository list returned empty. No source upload, branch, release, repository visibility change or AnkiWeb action occurred. A repository destination/access and publication intent must be supplied before publishing. Source and Codex handoff are included.

## Source references for the contract

- Anki 26.08.1 `pylib/anki/decks.py`: native deck config update API.
- Anki 26.08.1 `proto/anki/deck_config.proto`: random order enums and request/limit/global fields.
- Anki 26.08.1 `rslib/src/deckconfig/update.rs`: target-only assignment and transaction/limit behavior.
- Anki 26.08.1 `pylib/anki/collection.py`: custom undo and merge operations.
- Official Anki manual, Deck Options: shared presets; selected-parent display order; gather/sort/learning and burying behavior.

These establish the API design, not empirical native execution in this environment.

## Exact-installer repeat and gallery checks

After the first package build, the distributed source kit was extracted to a clean directory and its `src` replaced with a new extraction of the actual installer. **212 targeted tests passed**, with zero failures or skips, and the same runtime fingerprint. These repeat checks are not added to the cumulative 1,810/2,098 totals. Exact runtime and installer hashes are in `verification/1.0.2/exact-targeted.json`.

The final portfolio HTML decoded all twelve raw/poster images through its real controls and passed a 390px horizontal-containment check: 13 separate gallery checks, not part of the application regression total. All six boards and their contact sheet were visually inspected. They intentionally show six different themes instead of the previous Forest-only generated layouts.
