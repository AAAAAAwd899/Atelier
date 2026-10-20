# Atelier 1.0.6 release evidence

Class: Daedalus-managed local Anki desktop add-on, cumulative upgrade to the verified 1.0.2 baseline. Source publication is owner-authorized; AnkiWeb and website publication remain separate future actions. Shared production/owner standards and dashboard were consulted. This is the current project report; older acceptance records apply to their own versions.

Runtime SHA-256: `a49b1386014503a4ab56e7fa2f061ec4a185b08b0cba755f3e918ceabbadf980`.

## Automated checks

The current runtime passed **1,940 Python tests** (1,271 integration/preservation, 460 assessment/quiet-review, 209 authoring/import/publish/route) with zero failures or skips, and **2,893 browser checks in 30 suites**, with zero reported browser errors. The gate includes baseline preservation, native-route stand-ins, card/mask drafts and publishing, folder ordering, stored work, scoped CSS, 17 worlds, accessibility-oriented interactions, tour, exact scope and optional providers. `verification/verified.json` binds these results to the runtime digest. Build packaging additionally checks generated design tokens, all JavaScript syntax, installer format/paths/licenses, ZIP integrity, exact source/installer equality and repeatable builds. Historical test counts are not added to these totals.

## Actual Windows Anki 26.09.3

Native checks use disposable, unsynced generated profiles and the final installer, never the owner's collection:

- AddonManager update/preservation: 10 checks.
- First-run offer, all 13 tour steps, replay/skip, collection preservation, graceful shutdown and SQLite integrity: 26 checks. Geometry evidence is not a screenshot claim.
- Clock, profile lifecycle, 17 theme palettes/scenery, task guide and collection preservation: 47 checks. Native Qt clock screenshots were inspected. Physical alarm audio was not verified.
- Native folder ordering, preset isolation, review and Undo: 8 checks.
- Stock image-occlusion rendering, original image/note preservation, grade and Undo: 10 checks.

Software Qt rendering reports GPU-context fallbacks; there is no live GPU/Pip WebGL or hardware performance claim. Native listing captures use localhost-only Qt CDP and genuine add-on interfaces. Seven screenshots show generated example courses and an original landscape used as an occlusion exercise. They exclude outer Anki chrome and are not promotional mockups. Restaurant art from Onigiri is not included or claimed as native verification this release.

## Consumer review and bounded claims

The shared brief is `listing/ankiweb-1.0.6/BRIEF.md`. Listing screenshots were rendered and inspected; the local description preview was checked at 1440px and 390px, including lower content, loaded images and horizontal overflow. Version-specific review receipts accompany the evidence. The 13-step tour orients users; ten task recipes provide follow-up instructions. No uncoached novice usability study, formal accessibility certification or universal add-on compatibility is claimed.

The clock is local and theme scoped, has no collection writes or scheduler hooks, restores paused, and preserves corrupt/external edits. Optional finish sound defaults off. Existing artwork and runtime layout are retained; no replacement canvas/SVG concept art was introduced. Licensing/provenance and provider-consent boundaries remain documented. Current Anki official add-on sharing documentation and AnkiWeb terms were reviewed; technical packaging is not Anki endorsement or guaranteed upload approval.

## Remaining external gates

AnkiWeb account eligibility, actual form acceptance, real numeric listing identity and private-to-listing migration require owner-side validation. macOS/Linux, physical remotes, physical audio, all third-party add-ons and uncoached usability remain unverified. Do not promise automatic updates until the real listing is published and its download/update path is tested. Source publication does not deploy the website or publish a binary release. See `MANUAL_ACTIONS_REQUIRED.md` and `PROFESSIONAL_REVIEW_REQUIRED.md`.
