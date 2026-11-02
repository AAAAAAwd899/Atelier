# Atelier 1.0.10 audit

Local Anki desktop add-on; cumulative upgrade of verified 1.0.9 and the protected 1.0.2 baseline. Shared Daedalus standards and consumer directives apply. BRIEF-1.0.10.md records the scoped audience, wording and visual review.

Direct Set exam actions use the existing exam engine. Arrange order stores optional bounded profile metadata, separately for each parent. Exact immediate membership is checked again by the backend before saving. Invalid IDs, duplicates, cross-parent lists and stale membership are rejected. Existing profiles require no migration. Cancelling leaves preferences unchanged. Reset only removes the selected parent's display order. No card, note, media or scheduling changes are performed.

Current Python and headless Chromium suite results are bound to the runtime hash in verification/verified.json. The actual installed Anki 26.09.3 backend is tested against a disposable synthetic collection in output/native-folder-order-110/results.json: preference roundtrips, independent reset, unchanged cards/notes/decks/history, stale membership rejection and database integrity. No owner collection is accessed. No desktop Anki window is opened for this release. Historical native GUI and offscreen 1.0.9 evidence remains separately labelled in AUDIT-1.0.9.md and is not counted as fresh 1.0.10 native UI evidence.

Rendered desktop, compact and narrow screens are in screenshots/folder-order-110. The shipped installer is extracted and its new UI exercised independently; packaging checks byte equality, safe ZIP contents, CRC and deterministic rebuilds. Preserve the accepted artwork and full engines by cumulative baseline hash checks. The retained trailing blank line in worlds-home.css is benign; whitespace checking disables only blank-at-EOF warnings.

No universal add-on coexistence, macOS/Linux, physical remote, live GPU or uncoached usability acceptance is claimed. AnkiWeb remains unpublished. Only source may be pushed to the previously approved GitHub destination; public binary publication and website deployment are outside this update. Owner acceptance remains distinct from technical checks.
