# Atelier 1.0.0 — final release verification

**Decision: direct-install 1.0.0 release of the owner-accepted rc6 design and workflows. No AnkiWeb upload performed.**

## Acceptance and exact starting point

The project owner reported that visual and primary testing had passed and requested the version 1 release with consumer-facing language. This is recorded as **user-reported acceptance**, not an independently witnessed or exhaustive native Windows test matrix. `RELEASE-ACCEPTANCE.json` preserves that distinction.

The actual delivered rc6 installer was extracted and compared against its distributed source: every input entry matched. `release-1-baseline.json` binds the starting bytes. No older 0.8/0.9 branch was substituted. The direct-install package identity remains `daedalus_atelier`.

## Final polish, not another redesign

The release includes **59 exact copy/version substitutions across 9 runtime files**. It replaces development-facing help with practical instructions, removes Preview release and engineering-candidate wording from the integrated studios, clarifies local backups and explicit saving, aligns Card Studio's accessible navigation name, and uses normal Close/error wording for the installed app's missing-component path instead of calling it a preview. The handler still refuses the unavailable tool and changes no user data.

The same controls, menu commands, defaults, CSS, icon/art assets, source/mask geometry, visual-owner choices, storage formats/paths, scheduler/assessment algorithms, and source-publishing safeguards are retained. No feature or experimental renderer was added. User guides, release/support material, and privacy text were refreshed separately from code.

## Current cumulative execution

Completed UTC: **2026-09-12T22:46:27.498435+00:00**. Runtime SHA-256:

`d45fc4d13de5d17cbbfad134724c0e69aafc83e2b54d8fe3b66cf6af9b5547b7`

| Python suite | Passed |
|---|---:|
| suite integration and preservation | 1008 |
| exam engine and quiet review | 460 |
| card studio importers publishers and routes | 209 |
| **Total** | **1677** |

| Browser suite | Recorded checks |
|---|---:|
| assessment-fallback | 49 |
| atelier-browser | 98 |
| boundary-browser | 19 |
| card-advanced | 21 |
| card-first-run | 15 |
| card-studio | 63 |
| complete-browser | 78 |
| complete-home | 57 |
| home-polish | 166 |
| mask-studio | 42 |
| native-widgets | 104 |
| pip-groups | 8 |
| plan-handoff | 6 |
| quiet-keys | 24 |
| release-finish | 72 |
| release-one | 54 |
| release-one-card | 9 |
| session-polish | 179 |
| studio-polish | 215 |
| ui-audit | 104 |
| usability-audit | 129 |
| widget-routing | 88 |
| world-finish | 194 |
| world-suite | 123 |
| **Total** | **1917** |

No failed/skipped Python tests or uncaught page errors occurred in this completed run. Counts contain repeated themes, sizes, and preservation cases, not independent native integrations. Earlier runs and repeat checks are not added to the total. The runtime fingerprint was unchanged through the final verifier.

The final release adds **19 Python freeze/documentation checks**, **54 home/planner/error-copy browser checks**, and **9 Card Studio wording/reflow/consent checks** beyond the retained rc6 suites. The home tests cover the actual displayed release version, unchanged three-action Widgets toolbar, exact native tool command IDs, all twelve worlds, four window sizes, local-save/sync disclosures, and ordinary installed-app failure wording. Card Studio retains its single authoring route and provider-consent disclosure; tested text fits 1440, 940, and 390 CSS-pixel documents.

These tests execute the shipped frontends, real Python/SQLite models, and explicit fake collection/Anki/Qt interfaces. No production profile, provider request, synchronization, or publication is performed. The card authoring and assessment harnesses run in separate processes because both historical harnesses use a test-only `addon` package name; that is not the production namespace arrangement.

## Preservation evidence

Of rc6's **72 Sprout files, 71 remain byte-identical**; of its **80 Workshop files, 79 remain byte-identical**. The only further changed embedded file in each is `web/app.js`, with reviewed wording/accessibility-label changes. The original supplied Sprout/Workshop comparison still has the same four/two integrated files as rc6. Native engine versions and retained upstream licenses/provenance remain accurate.

`release_copy.py` reconstructs accepted code from an exact baseline plus the complete allowed substitution list. All bytes must match. This avoids broadly excluding a frontend from preservation merely because its text changed. Tests and packaging enforce unchanged CSS, images, icons, configuration defaults, data schemas, algorithms, and every non-copy runtime file.

## Visual evidence

Current screenshot renderers capture the accepted twelve worlds across ten application views and a separate built-in Widgets/arrangement set. `Atelier-Visual-Evidence.json` binds the 120 full-workflow screenshots to the current runtime, with per-image dimensions/hashes. Current release-copy screenshots cover Widgets and both integrated settings pages.

These are actual Chromium renders with labelled fictional or synthetic records, not generated concepts, independent Windows captures, or real Onigiri reward measurements. The layout/style files are unchanged from the accepted baseline, and additional wording was checked for wrapping/containment. Pip uses the shipped animated fallback in this browser environment; live GPU verification is not claimed.

## Test-harness corrections during this pass

An exploratory copy test initially looked for the version in the Widgets heading, although the accepted product displays it in the sidebar brand. The corrected check reads the actual visible brand and the runtime version. A synthetic missing-engine trigger was initially placed outside the viewport by the test; it was repositioned within the fixture and clicked normally. The assertion still verifies the same error path. No forced click or removed outcome assertion was used.

One exploratory combined frontend test encountered the historical harness namespace collision described above. Its Card Studio portion now runs in a separate process. The first full verifier ran before the two new browser suites were registered; the final clean run above includes both. Stopped/incomplete runs are not counted as successful evidence.

## Packaging and reproducibility

`package_release.py` requires the current successful verifier, exact reviewed copy boundary, unchanged protected assets, current screenshots, recursive Python/JavaScript syntax, fixed installation identity, no private records/caches/font files, ZIP integrity, per-file equality, and a byte-identical repeat installer. The source kit contains the same runtime, tests, raw evidence, reviewed substitution list, license notices, and reproduction scripts. SHA-256 checksums establish integrity, not a cryptographic publisher signature.

The installer is a direct-file distribution. A separate public AnkiWeb listing requires its real numeric ID, verified migration, actual support destination, and authorized upload; no such identity or upload is invented. Source and installer packages do not include fonts or private profiles.

## Bounded support and unperformed independent checks

The release target is **Windows desktop Anki 26.08.1 with its standard editor**, matching the project context. The owner reported visual/primary acceptance. Independent native Windows/Qt execution was not performed here. There is no claim of full native coverage for 100–200% Windows scaling, real PDF/image codecs, every IO/IOE/custom template, publishing/Undo, timed resume/native learning, Sync/profile lifecycle, Onigiri rewards, or GPU Pip. Other OSes, beta Anki versions, and experimental editors are not advertised as verified targets.

The consumer guide preserves those relevant compatibility boundaries without calling the release a prototype. `RELEASE-GATES.md` separates direct-file release readiness from public listing administration. No automatic telemetry, provider use, data reset, or publication occurs.

## Reproduce

```sh
python verify_release.py
python tests/render_studio_release.py
python tests/render_suite_gallery.py
python tests/render_world_finish.py
python tests/render_native_widgets.py
python package_release.py
```

The test harness requires pytest, Playwright, Node.js, and Chromium (default `/usr/bin/chromium`), plus a temporary filesystem supporting `fsync`. This execution used `TMPDIR=/dev/shm/atelier-v1-tests`; production atomic-write/fsync safeguards were not removed.

## Full exact-installer confirmation

After packaging, the **distributed source kit** was extracted into a clean directory and its src replaced by the actual 1.0.0 installer bytes. The entire verifier passed again: **1677 Python tests and 1917 browser checks**, completed **2026-09-12T22:51:25.597301+00:00**, with the same runtime fingerprint. This is repeat confirmation, not additional checks added to the totals. Native test boundaries are unchanged.

Exact installer SHA-256: `2cc7ee5001e9522f706d9d61bbb9140c621b6ef4dcbf2765cfe9b318a675a2cd`. Evidence: `verification/exact-installer.json` and the fresh `verification/exact-installer/` logs/XML/JSON.

Both packaged screenshot galleries were decoded separately (120 complete-workflow images and 16 built-in-widget/arrangement images), with their controls exercised at desktop and 390px widths. They requested no external assets and produced no page exceptions. The browser environment blocks direct file-URL navigation, so this check loaded the exact HTML bytes through Playwright's document-content interface; it is not a claim about every end user's local-file policy.
