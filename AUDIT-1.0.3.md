# Atelier 1.0.3 — private candidate audit

Status: implemented and verified for private owner review. This is not public-release approval, an AnkiWeb upload, or universal compatibility acceptance. Atelier is a local desktop application with no server accounts, payments, telemetry, or production database. The staged `site/` is an unpublished informational site.

## Current candidate

The current runtime fingerprint is `d804f65f15a74502cba8debdc862a3aaa37409c564b83f40dd661aceea8d3ca5`. The cumulative installer and matching source archive are built from the committed source and their exact commit and SHA-256 values are recorded in `dist/Atelier-1.0.3-Build.json` and `dist/Atelier-1.0.3-SHA256.txt`.

Atelier remains Atelier and advances only to version 1.0.3. The accepted catalogue now contains seventeen worlds. Moonlit Castle, Underworld, Mythic, Lakeside Cabin, and Sunset Cove use original high-resolution raster scenes generated for this release, accessible semantic palettes, and distinct materials. Six authored local companion families now match those worlds: a moon-crowned cat, leaf-cloaked Pip, tide otter, constellation owl, ember fox, and folded-paper crane. The rejected flat castle illustration is not shipped. The wordmark uses an original transparent gold architectural emblem rather than the temporary circled letter.

The workspace shell now fills the actual viewport through fixed edge constraints instead of a percentage width plus forced CSS zoom. A final 1915×1000 render fills all 1915 pixels; the same source has zero horizontal overflow at 1280×800 and 390×720. The production finish now spans every screen family: Home, Library, Widgets, Tools, Card Studio, Mask Studio, Exam Studio, Practice Builder, Pip, Results, Progress, and reviewer question/answer. Panels use each world's own scene, tint, material, edge light, pattern, and elevation rather than a common flat-card treatment. Card Studio's four-step workflow stays in a single desktop grid with the editor visible below it, and the shell loads the shipped high-resolution Atelier emblem.

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

The supplied verified 1.0.2 source was used because no newer accepted build existed. Its 233 runtime entries matched the recorded baseline. The 1.0.3 runtime manifest records 33 changed files, 27 added files, and zero removed files, for 260 runtime files. Preserved-engine hashes and the baseline/patch declarations are checked during packaging. The original installer was not supplied for a new independent baseline extraction; the kit retains its earlier source/installer equality evidence.

Checkpoint A established semantic roles, navigation hierarchy, study scope, theme scenes, the emblem, and world-specific materials. Checkpoint B carried all seventeen worlds through Home, Library, Card Studio, Mask Studio, Exam Studio, Practice, reviewer question/answer, Results, Pip, Widgets, Progress, and Tools while preserving node identity and saved values during theme changes. Checkpoint C runs the cumulative source, browser, preservation, packaging, extracted-payload, and deterministic-build gates.

## Current automated evidence

The final `verify_release.py` run completed on 2026-09-19 against the fingerprint above:

| Evidence | Passed | Failed | Skipped/errors |
|---|---:|---:|---:|
| Atelier integration and preservation | 1,233 | 0 | 0 |
| Exam engine and quiet review | 460 | 0 | 0 |
| Card Studio importers, publishers, and routes | 209 | 0 | 0 |
| 28 browser suites | 2,630 | 0 | 0 page errors |
| **Total** | **4,532** | **0** | **0** |

The browser total includes whole-folder shuffle, cumulative reviewer behavior, widget routing, ownership boundaries, assessment fallback, all-world switching, accessibility-oriented UI checks, Home and session polish, guided card sets, exam/Pip groups, Card Studio, advanced authoring, first-run guidance, Mask Studio, and the 1.0.3 image-occlusion view checks. Pure model/storage tests and browser native-API doubles are identified in their receipts; they are not relabeled as native Anki tests.

The expanded world-finish suite passes 266 checks. It verifies all seventeen world materials and chooser previews, light/dark filters, keyboard focus, reduced motion, forced-color focus, failed-save alerts, planner value preservation, stable grading targets, and exact workspace width at 320, 390, 620, 820, 1040, 1440, 1725, and 1915 pixels. Current receipts are in `verification/verified.json`, `verification/python-current.json`, and the suite-specific verification folders.

## Rendered interface evidence

The final shipping source was rendered in Chromium with explicitly fictional data in a complete 1,275-render matrix: seventeen worlds, fifteen screen families, and five viewport sizes. Every capture completed without a page error or horizontal-overflow failure. The delivery bundle includes all 510 desktop and phone renders, the six companion panels, five all-screen review boards, and the full machine-readable matrix receipts. Representative inspection boards are:

- `output/playwright/visual-review-boards/forest-1440x900-all-screens.png`
- `output/playwright/visual-review-boards/forest-390x720-all-screens.png`
- `output/playwright/visual-review-boards/sunset-beach-1440x900-all-screens.png`
- `output/playwright/visual-review-boards/castle-1440x900-all-screens.png`
- `output/playwright/visual-review-boards/linen-1440x900-all-screens.png`
- `output/playwright/companion-family/cutesy-rose.png`
- `output/playwright/companion-family/green-forest.png`
- `output/playwright/companion-family/water-tidal.png`
- `output/playwright/companion-family/orbit-midnight.png`
- `output/playwright/companion-family/ember-ember.png`
- `output/playwright/companion-family/linen-linen.png`

`output/playwright/final-matrix/results.json`, `final-home-workflows/results.json`, `final-planner/results.json`, and `final-card/results.json` record each file, world, screen, viewport, image hash, overflow result, and page errors. `output/playwright/companion-family/results.json` records the shipped portrait file, themed stage language, portrait renderer, image hash, zero page errors, and measured text contrast for each companion family; the lowest explanatory-text result is 6.89:1. These are real browser renders of the shipped source, not native Anki screenshots.

Earlier rejected, flat-art, or stale-compositor frames remain failure evidence and are not cited as final screenshots.

## Native and performance evidence boundaries

The final installer passed the actual Anki 26.05 AddonManager API in a fresh disposable Windows profile against the current runtime fingerprint. The check installed the verified 1.0.2 baseline, wrote synthetic preference and saved-work markers, installed the cumulative 1.0.3 add-on, and confirmed byte-equal runtime files, preserved preferences and saved work, the private add-on identity, no conflicts, and Anki's compatible flag. It did not access the owner's profile or automate the GUI file picker. The receipt is `verification/native-install-current.json`.

Earlier native visual evidence used disposable synthetic profiles and payload equality checks. It covered six Home/Widgets captures in Midnight, Rose, and Forest; stock image-occlusion question/answer canvases and mask registration; and folder scheduling and Undo. Those visual tests did not run against the final five scenes or final emblem and are not presented as current native visual acceptance.

Physical remote input, macOS/Retina, independent 100/125/200% native scale configurations, native fullscreen/autohide combinations, arbitrary custom templates, third-party IO Enhanced editing, live GPU Pip, decoded-image/GPU memory, native endurance, complete 200% text review, and uncoached newcomer testing remain unperformed. The browser Pip evidence uses the shipped local portrait renderer; the preserved fallback path remains covered, and no live WebGL claim is made.

The retained performance/endurance receipts are historical measurements from an earlier 1.0.3 fingerprint. They are useful regression context but are not relabeled as measurements of the final artwork bytes. Current functional/browser verification is complete; a new isolated-host performance run would be required for a final performance claim.

## Release boundary

No repository was made public, no Pages/site deployment was performed, and no AnkiWeb listing was created or updated. A GitHub push cannot update installed Anki copies. Future automatic updates require the owner's real numeric AnkiWeb listing, a verified migration from the private `daedalus_atelier` identity, and approval of the exact installer hash, support statement, listing, and website destination.

The shared Daedalus production standard, owner directive, and operating dashboard were consulted. The dashboard's existing “Daedalus Atelier” report concerns a different local website-editor project at `apps/atelier`; no shared project report existed for this Anki add-on, so this repository audit is the current project record. External publication, account eligibility, platform rules, support/contact wording, and commercial/legal decisions remain in `MANUAL_ACTIONS_REQUIRED.md` and `PROFESSIONAL_REVIEW_REQUIRED.md`.
