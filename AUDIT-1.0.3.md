# Atelier 1.0.3 — private candidate audit

Status: implemented and verified for private owner review. This is not public-release approval, an AnkiWeb upload, or universal compatibility acceptance. Atelier is a local desktop application with no server accounts, payments, telemetry, or production database. The staged `site/` is an unpublished informational site.

## Current candidate

The current runtime fingerprint is `7b4195e784e751051e5f13d01bd21f2cf731fe8db588eeaaed7ab3c32f1eb3fa`. The cumulative installer and matching source archive are built from the committed source and their exact commit and SHA-256 values are recorded in `dist/Atelier-1.0.3-Build.json` and `dist/Atelier-1.0.3-SHA256.txt`.

Atelier remains Atelier and advances only to version 1.0.3. The accepted catalogue now contains seventeen worlds. Moonlit Castle, Underworld, Mythic, Lakeside Cabin, and Sunset Cove use original high-resolution raster scenes generated for this release, accessible semantic palettes, distinct materials, and theme-specific Pip companion accents. The rejected flat castle illustration is not shipped. The wordmark now uses an original transparent gold architectural emblem rather than the temporary circled letter.

The workspace shell now fills the actual viewport through fixed edge constraints instead of a percentage width plus forced CSS zoom. A final 1915×1000 render fills all 1915 pixels; the same source has zero horizontal overflow at 1280×800 and 390×720. Sunset Cove received an authored coastal sidebar, stronger selected navigation, layered translucent workflow and study surfaces, warm edge light, distinct repair and lecture materials, deeper elevation, and restrained coral accents. Other themes keep their own scene, shape, type, surface, and Card Studio treatment.

The functional upgrade preserves and extends the accepted 1.0.2 behavior:

- whole-folder shuffle and native Anki scheduling remain intact;
- one exam can explicitly include multiple parent folders, with overlapping descendants de-duplicated;
- a focused class or folder is available from Home, Pip, and Exam Studio;
- Pip keeps the shared growth/study behavior while its companion treatment changes by world;
- Card Studio retains local source projects, drafts, field mapping, approval, duplicate checks, publishing, and slide/page provenance;
- guarded **Save & next card** and **Save & next slide/page** actions carry only source/destination/mapping preferences into a clean draft;
- image-backed pages can open Mask Studio or hand the rendered image to Anki's supported native Image Occlusion editor;
- exact note selections can open in Anki's Browser, and folder/deck menus expose scoped native export/share actions;
- masks, remotes, native widgets, saved work, source images, exam sessions, original themes, and optional Onigiri boundaries remain preserved.

## Source and checkpoints

The supplied verified 1.0.2 source was used because no newer accepted build existed. Its 233 runtime entries matched the recorded baseline. The 1.0.3 runtime manifest records 31 changed files, 21 added files, and zero removed files, for 254 runtime files. Preserved-engine hashes and the baseline/patch declarations are checked during packaging. The original installer was not supplied for a new independent baseline extraction; the kit retains its earlier source/installer equality evidence.

Checkpoint A established semantic roles, navigation hierarchy, study scope, theme scenes, the emblem, and world-specific materials. Checkpoint B carried all seventeen worlds through Home, Library, Card Studio, Mask Studio, Exam Studio, Practice, reviewer question/answer, Results, Pip, Widgets, Progress, and Tools while preserving node identity and saved values during theme changes. Checkpoint C runs the cumulative source, browser, preservation, packaging, extracted-payload, and deterministic-build gates.

## Current automated evidence

The final `verify_release.py` run completed on 2026-09-19 against the fingerprint above:

| Evidence | Passed | Failed | Skipped/errors |
|---|---:|---:|---:|
| Atelier integration and preservation | 1,233 | 0 | 0 |
| Exam engine and quiet review | 460 | 0 | 0 |
| Card Studio importers, publishers, and routes | 209 | 0 | 0 |
| 28 browser suites | 2,628 | 0 | 0 page errors |
| **Total** | **4,530** | **0** | **0** |

The browser total includes whole-folder shuffle, cumulative reviewer behavior, widget routing, ownership boundaries, assessment fallback, all-world switching, accessibility-oriented UI checks, Home and session polish, guided card sets, exam/Pip groups, Card Studio, advanced authoring, first-run guidance, Mask Studio, and the 1.0.3 image-occlusion view checks. Pure model/storage tests and browser native-API doubles are identified in their receipts; they are not relabeled as native Anki tests.

The expanded world-finish suite passes 266 checks. It verifies all seventeen world materials and chooser previews, light/dark filters, keyboard focus, reduced motion, forced-color focus, failed-save alerts, planner value preservation, stable grading targets, and exact workspace width at 320, 390, 620, 820, 1040, 1440, 1725, and 1915 pixels. Current receipts are in `verification/verified.json`, `verification/python-current.json`, and the suite-specific verification folders.

## Rendered interface evidence

The final shipping source was rendered in Chromium with explicitly fictional data and visually inspected at fullscreen, desktop, and phone widths:

- `output/playwright/current-art/sunset-beach-home-fullscreen-1915x1000.png`
- `output/playwright/current-art/sunset-beach-home-final-1280x800.png`
- `output/playwright/current-art/sunset-beach-home-final-390x720.png`
- `output/playwright/current-art/world-chooser-new-worlds-1024x768.png`
- `output/playwright/current-art/new-worlds-contact-sheet.png`

`output/playwright/current-art/final-responsive-evidence.json` records exact host/layout widths, equal main `scrollWidth`/`clientWidth`, and zero page errors for the three final Sunset Cove captures. These are real browser renders of the shipped source, not native Anki screenshots.

The earlier 360-capture matrix remains historical evidence for the original twelve worlds and five viewport sizes. It is not claimed as a final native render of the five added worlds. Earlier rejected or stale-compositor frames remain failure evidence and are not cited as final screenshots.

## Native and performance evidence boundaries

The final installer passed the actual Anki 26.05 AddonManager API in a fresh disposable Windows profile against the current runtime fingerprint. The check installed the verified 1.0.2 baseline, wrote synthetic preference and saved-work markers, installed the cumulative 1.0.3 add-on, and confirmed byte-equal runtime files, preserved preferences and saved work, the private add-on identity, no conflicts, and Anki's compatible flag. It did not access the owner's profile or automate the GUI file picker. The receipt is `verification/native-install-current.json`.

Earlier native visual evidence used disposable synthetic profiles and payload equality checks. It covered six Home/Widgets captures in Midnight, Rose, and Forest; stock image-occlusion question/answer canvases and mask registration; and folder scheduling and Undo. Those visual tests did not run against the final five scenes or final emblem and are not presented as current native visual acceptance.

Physical remote input, macOS/Retina, independent 100/125/200% native scale configurations, native fullscreen/autohide combinations, arbitrary custom templates, third-party IO Enhanced editing, live GPU Pip, decoded-image/GPU memory, native endurance, complete 200% text review, and uncoached newcomer testing remain unperformed. The browser Pip evidence uses the shipped animated fallback and makes no live WebGL claim.

The retained performance/endurance receipts are historical measurements from an earlier 1.0.3 fingerprint. They are useful regression context but are not relabeled as measurements of the final artwork bytes. Current functional/browser verification is complete; a new isolated-host performance run would be required for a final performance claim.

## Release boundary

No repository was made public, no Pages/site deployment was performed, and no AnkiWeb listing was created or updated. A GitHub push cannot update installed Anki copies. Future automatic updates require the owner's real numeric AnkiWeb listing, a verified migration from the private `daedalus_atelier` identity, and approval of the exact installer hash, support statement, listing, and website destination.

The shared Daedalus production standard, owner directive, and operating dashboard were consulted. The dashboard's existing “Daedalus Atelier” report concerns a different local website-editor project at `apps/atelier`; no shared project report existed for this Anki add-on, so this repository audit is the current project record. External publication, account eligibility, platform rules, support/contact wording, and commercial/legal decisions remain in `MANUAL_ACTIONS_REQUIRED.md` and `PROFESSIONAL_REVIEW_REQUIRED.md`.
