# Atelier 1.0.8 folder reorganization audit

Classification: local Anki desktop add-on, cumulative upgrade of accepted 1.0.7 and verified 1.0.2. Shared Daedalus production/owner standards apply. This is the current project report. Scope is folder organization, not a visual redesign or new scheduling engine.

The Move dialog now searches the complete normal-deck hierarchy, browses one level at a time, exposes root/breadcrumb navigation and shows exact From/To paths. It blocks unchanged destinations and naming conflicts. Backend validation still rechecks current IDs, names, filtered decks, cycles and collisions in Anki's serialized CollectionOp. Only native reparent changes deck structure; native Undo reverses it. The source snapshot is retained from dialog open for stale-name validation. Search Enter focuses a result rather than submitting a move.

Actual native testing found that CollectionOp redraw can replace the frontend before its success reply navigates. The success callback now records the destination in the same profile's ephemeral navigation before redraw. It does not write collection data or persist a new store schema. Native UI confirmation, destination display, card-field preservation and Undo are verified together in the generated example profile.

All existing source/card/mask/exam stores, whole-folder shuffle, remotes, widgets, original appearance ownership and authored artwork remain. No other add-on is installed/imported by this change. Native menu-provider tests use synthetic providers, not an installed Ankimon or other named add-on certification.

Verification is bound to the exact runtime in verification/verified.json and the installer/source hashes in dist/Atelier-1.0.8-Build.json. Counts are taken from final receipts, not historical reports. Native evidence uses Windows Anki 26.09.3 and generated unsynced profiles. Browser evidence uses shipped scripts with synthetic collections and is labelled separately. No macOS/Linux, physical remote, live GPU or uncoached novice claim is made.

Storage budget: under 4 GiB peak incremental QA/package allocation against more than 140 GiB free at the start of this pass, above the shared 50 GiB target. Existing 1.0.7 installer/source and private owner backup stay protected. Successful disposable profiles are closed gracefully, hashed into cleanup receipts and reclaimed within the verified project QA paths; no owner collection or Windows process is modified.

Publication: source updates only to the exact previously approved public AAAAAAwd899/Atelier repository. No AnkiWeb upload, website deployment or public binary release is performed. Owner visual acceptance, listing eligibility, numeric identity migration and untested-platform evidence remain separate gates in MANUAL_ACTIONS_REQUIRED.md.

The initial sequential browser run began before the final source freeze. `verification/browser-cutover-108.json` records the final digest and the in-flight suite boundary. Every suite through that boundary is rerun on final bytes; later jobs began after the freeze. Complete aggregation still requires all suites to pass. No old-release browser receipt is used as a new pass.
