# Atelier 1.0.3 — private candidate audit

Status: implemented and packaged for owner review, with the automated verification recorded below. This is not public-release approval or universal compatibility acceptance. The owner rejected the first flat Forest render. Final captures use the revised runtime; earlier renders remain historical failure evidence.

## Current candidate delta

The runtime source for this private candidate is commit `bca7bd1abcc38fddd16ac41574ff99bb5903fa74` with runtime fingerprint `b3feb7b956196c58f598ab4ebc0a4588bd36b2afae7cdd245f722f5c4cc69f46`. It adds authored, scalable Pip world emblems around the existing animated/3D sculpture: a soft cat treatment for cutesy worlds, botanical leaves for green worlds, and tide, orbit, ember, or paper treatments for the remaining worlds. It makes selecting two separate parent folders for one exam explicit and explains overlap handling. The sidebar, scope card, workflow inbox, focus panel, exam sections and deck cards now use layered world-aware surfaces, depth, and clearer navigation grouping. A focused study can open a matching Pip plan directly or start a prefilled plan; the no-focus desk exposes a clear Set your focus step. Growth stages, Pip actions, card engines, scheduling, masks, remotes, widgets, saved work and original-theme compatibility are unchanged.
Card Studio also has guarded **Save & next card** and **Save & next slide/page** actions for slide-set authoring. The first saves the current local draft and carries only the source page, destination deck, tags, card style, selected note type, field mapping, and occlusion display preference into a clean draft. The second additionally advances to the next page of a multi-page source. Neither action copies the previous question, masks, media, or source quotation.

The installer is `dist/Atelier-1.0.3.ankiaddon` with SHA-256 `77795e5423f38872c77e6c89e233ab7c701ed0cc274fad842942eec36b680e18`; the matching source archive digest is recorded in `dist/Atelier-1.0.3-build.json`. Both are rebuilt from this fingerprint and marked `full_automated_verification: false`. The browser, native, performance, memory and endurance receipts described later are retained historical evidence for prior fingerprints and must be rerun before a production-ready claim. Local browser escalation is currently unavailable; no stale receipt is relabeled as current.

## Source and checkpoints

The supplied 1.0.2 source archive was checked and extracted. Its 233 runtime entries matched the recorded baseline. The original installer itself was not supplied for independent rechecking; the kit records its earlier source/installer equality. No newer accepted build existed. Git main preserves the baseline.

The current candidate delta contains 31 changed files, 15 added files and 0 removed files: 258 runtime files total. Original exam and authoring runtime trees, stores, scheduling/folder-order operation, remotes, mask publication and widget data logic remain byte-identical. The generated palette contract and scoped presentation adapters contain the upgrade; source images and stored mask coordinates are not converted.

- A: canonical roles, retired duplicate home layer, compact Home/Widgets hierarchy and seventeen local landscapes. Midnight, Rose and Forest were rendered in actual Anki. The original Forest screenshot was superseded after inspection.
- B: existing world IDs retained across Home, Library list/grid, Card Studio, Mask Studio, Exam setup, Practice builder, reviewer question/answer, Results, Pip, Widgets, Progress and Tools. Captures include all seventeen worlds at 1440×900, 1280×720, 1024×768, 800×600 and browser-only 390×720. There are 900 default captures, including 60 additional generic-Library captures; these are repeated palette/viewport cases, not 900 independent integrations.
- C: preserved-engine verification, exact stock IO native lifecycle tests, actual folder scheduler checks, cumulative installer, matching source, repeat-build equality, extracted-payload checks, real recording and private GitHub handoff. Owner visual acceptance and the unavailable host/hardware gates remain open.

## Current automated evidence

Current Python verification: 1,223 Atelier checks, 460 Sprout checks and 209 Workshop checks passed with zero failures/skips (1,892 total) after updating preservation contracts for the approved 1.0.3 presentation files. The runtime-bound receipt is `verification/python-current.json`. Browser verification was attempted but could not start Playwright on this Windows host (`WinError 5: Access is denied` while creating its subprocess pipes); no browser receipt is relabeled as current. The historical receipt below records 27 browser suites with 2,127 checks and zero reported page errors for an earlier fingerprint. Pure logic/model/storage tests and browser native-API doubles are identified in the individual receipts. Native tests are separate below. The full verification gate is `verify_release.py`; deterministic packaging additionally checks syntax, manifest, ZIP CRC, preserved engine hashes, forbidden/private files, exact source/installer bytes and repeat builds.

The complete CI run is https://github.com/AAAAAAwd899/Atelier/actions/runs/34750594169, runtime source commit `0bd95a6bf9d4751e79fcfaa04a7e7206d4dc5e78`. The combined Card Studio launcher checks, including repeated mount, narrow layouts, theme-specific materials and original-theme round trips, are included in the full-verifier total above.

All 900 default captures reported no horizontal page overflow or uncaught page errors. Contact sheets for every captured screen were inspected at 1440×900 and 390×720 across all seventeen worlds. The unpublished add-on information page was also rendered at desktop and phone widths with its real interface images loaded, no horizontal overflow and no page errors. Nine scoped axe scans (Midnight/Rose/Forest × Home/Widgets/Tools) found zero violations; incomplete axe checks are retained. The conservative 78%-canvas composited backdrop probe passes normal-text 4.5:1 for the seventeen worlds, with a minimum measured 4.653:1. These probes are not a complete accessibility certification or a claim that every possible user template was checked.

The extracted installer ran 16 unit checks and the designated 1.0.3 IO, 1.0.1 reviewer/remote-focus and 1.0.2 folder/browser checks. Their separate logs bind execution to the extracted files, whose runtime bytes equal the delivered source. Initial extracted 1.0.1 testing exposed a fixed 40 ms test race; the harness now waits for the measured long-content layout before testing user scrolling, retaining the scroll assertion.

Windows original authoring tests passed 208 of 209; the unchanged filesystem symlink test requires Windows privilege 1314. The complete Linux verifier passed all 209 authoring cases. Windows DST fixtures now use explicit America/Chicago transitions with their original 23/25-hour assertions. Older world font assertions were corrected to check every computed heading against the existing catalog; the original catalog had two font stacks, not three. Panel-radius regression and insufficient muted-text contrast found during rendering were fixed. CI Pip timeouts led to explicit loaded-screen waits and sequential browser execution; assertions were retained.

The project development environment dependency scan initially reported vulnerable pip/setuptools versions. Updating those project-local packaging tools produced a clean rescan. Both scan receipts are included. This covers the scanned development environment, not Anki's own Python/Qt distribution or a guarantee against unknown vulnerabilities.

## Actual native evidence

Windows, installed Anki 26.05 build e64c6b1a; disposable synthetic profiles only, no owner profile or sync. Payload bytes are checked against the installer source before loading. Rendering tests copy the extracted payload into the QA add-on folder. A separate real AddonManager installer test exercises the ZIP update path; the GUI file picker was not automated.

- Six real main-window captures: Home and fully loaded built-in Widgets in Midnight, Rose and Forest. Measured logical window 1283×700, screenshot 1925×1050, device pixel ratio 1.5. No fabricated title bars or substituted statistics.
- Stock native IO: real question/answer canvases, fitted whole image/mask registration, Actual size, original note/media preservation, native rating/revlog and native Undo. Nine checks pass. A known landmark is visibly occluded on question and revealed on answer. Fit support is restricted to the documented exact stock-template fingerprint; unknown/custom templates fail closed.
- Actual Anki folder backend: eight checks pass for parent preset isolation, unchanged lecture/unrelated presets, preserved global options, native Undo, no repeated preset clone, exact scope and a native queue containing all three synthetic lecture decks. The recorded order does not promise strict alternation or override Anki limits/learning rules.
- Actual Anki AddonManager: eight checks pass for baseline installation, cumulative update, payload equality, retained preferences, retained `user_files`, untouched profile-local saved-file sentinels, private package identity and no conflicting installs. The native compatible flag is true on this host. Saved-file sentinels test update preservation, while semantic store operations are covered by the separate original engine suites. A test-profile lock collision was resolved with a fresh unique QA profile for each native IO run.

Input was scripted API/JavaScript, not a physical remote. Native GPU initialization warnings occurred and rendering used the software path; no live GPU claim. Requested 100% scaling was clamped by the host, so those attempts are not independent 100/125/200% tests. Initial offscreen/late-sizing/blank-canvas failures are retained separately; final screenshots wait for actual canvas painting. Native QA shutdown can block in collection close after completed receipts; the harness bounds shutdown for its disposable profile.

Final gallery inspection also caught stale native compositor frames in two Home/Widgets captures despite ready browser diagnostics. The capture harness now checks the requested world and route, allows the native compositor to settle, and the six-screen set was retaken and inspected. The rejected frames remain explicitly labelled capture failures, not final passing screenshots.

## Performance evidence

Same local Windows host, baseline source and candidate fixtures. Baseline measurements were run from the untouched Git baseline during final verification, not recorded before development began. Other task processes were active. Values are median / p95 milliseconds.

| Probe | Samples each | Baseline 1.0.2 | Candidate 1.0.3 |
|---|---:|---:|---:|
| open | 5 | 1139.5 / 3091.3 | 955.3 / 1098.6 |
| navigation | 30 | 198.1 / 356.9 | 149.6 / 181.2 |
| search_5000 | 10 | 385.3 / 452.0 | 356.5 / 509.6 |

Open means HTML through controls, fonts and two frames, not disk-cold scenery or native Anki startup. Navigation includes automation and two frames; 5,000-deck search includes production debounce and paint. The table records both median and p95 so the observed search-tail variance remains visible; this is not an isolated-host speed claim.

The browser endurance probe completed 1808.7 seconds and 180 route/theme cycles with no page errors. After the first complete palette rotation, retained nodes stayed at 2670, listeners at 62 and documents at 2. Forced-GC JavaScript heap rose from 2.98 MiB at cycle 18 to 3.36 MiB at the last sample. This small rise remains an observation, not a no-leak guarantee. Decoded scenery/GPU memory, native 30–60-minute review endurance and isolated source/figure-load timing remain unmeasured.

An additional 288-cycle accelerated investigation captured actual V8 heap snapshots after warmup. DOM/listener/document counts remained unchanged. Between cycles 48 and 288, snapshot `code` entries grew by 315920 bytes, while closure self-size was unchanged and object self-size grew by only 240 bytes. The observed growth was dominated by V8 code entries rather than retained page nodes/handlers. Embedder heap use fell from 6010600 to 5098872 bytes across those samples. This investigation does not measure total decoded-image or GPU RAM.

## Visual scorecard and open gates

Composition: richer local scenery, tighter hierarchy and world-specific shapes; actual captures support the change. Readability: composited palette and scoped axe checks pass; arbitrary card content remains outside that claim. Consistency: catalog font/shape and theme-switch assertions pass. Task clarity: preserved actual workflows and default/empty/error/long/dirty-form browser cases are in the evidence; an uncoached newcomer study is still needed. Native integration: limited Windows Home/Widgets/IO and folder backend checks pass.

Representative full-size screens were inspected and failures corrected. This does not claim a human inspected every one of the 900 files or every possible visual state. Owner acceptance of the five scorecard dimensions remains pending. The recording shows actual browser interactions using explicitly synthetic data; generated landscapes have separate provenance and are never presented as UI test evidence.

Unperformed release gates: macOS/Retina, physical keyboard-mode remotes, native Windows 100/125/200% configurations, native fullscreen/autohide combinations, third-party IO Enhanced edit acceptance, every custom/media template, full native workflow integration, decoded-image memory, native endurance, 200% text enlargement across every surface, complete manual visual-state/accessibility review and uncoached newcomer tests. These require additional work and/or an available host/device; do not call the candidate production ready.

## Release boundary

Private repository: https://github.com/AAAAAAwd899/Atelier. Source branch `atelier-1.0.3`; no public visibility change, AnkiWeb listing or website deployment. `site/` contains unpublished add-on information with no invented numeric code, public download or approval flag. A GitHub push/site change cannot update installed copies. A future numeric AnkiWeb listing requires a verified one-time migration from private `daedalus_atelier`; subsequent approved updates must use that same listing. Account eligibility and the date it changes have not been verified.

Before public rollout, approve the exact installer hash, support statement, real listing and website destination. See MANUAL_ACTIONS_REQUIRED.md, PROFESSIONAL_REVIEW_REQUIRED.md and INSTALL-1.0.3.md. Historical marketing/acceptance files retained from the source kit do not grant current approval. The shared Daedalus standards were consulted; no Atelier-specific shared dashboard report existed, so this repository audit is the current project report.
