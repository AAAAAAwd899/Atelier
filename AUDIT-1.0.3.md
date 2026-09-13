# Atelier 1.0.3 — private candidate audit

Status: implementation and acceptance verification in progress. This is not a public-release or production-readiness claim. The owner rejected the first flat Forest render; those earlier captures are not accepted visual evidence.

## Source and scope

The immutable supplied 1.0.2 source archive was hash/CRC checked and extracted. Its 233 runtime entries matched the kit's recorded baseline. The original installer was not independently supplied here; the kit records its earlier source/installer equality. No newer accepted repository existed. The Git baseline preserves that source, with exact current deltas in `patch-103-changes.json` and original hashes in `baseline-1.0.2.json`.

The exam and authoring runtime trees, scheduler/folder-order operation, stores, masks, publication rules, remotes, native widget data model and original-owner logic are preserved. Presentation changes live in canonical palette generation and scoped home/planner/authoring/reviewer adapters. Compatibility exceptions remain scoped in `shared.css`, `review-finish.css` and the established screen sheets.

## Checkpoints

- A: canonical roles, retired duplicate home layer, revised Home/Widgets hierarchy, local landscapes, Midnight/Rose/Forest desktop and compact renders. Initial native captures exposed load timing and insufficient visual quality, leading to revisions. Visual acceptance still requires owner review of final captures.
- B: shared palette adapters reach planner, authoring and native owned surfaces; all twelve stored world IDs remain. Original workflow suites cover source/draft persistence, mask publication, exact routes, saved practice, results, Pip and widget ownership. Actual current receipts and screenshot inspection determine final coverage.
- C: runtime preservation, native IO lifecycle reproduction, deterministic cumulative packaging, paired source, extracted-runtime verification, private repository and staged AnkiWeb/website handoff. Final artifacts and evidence are recorded in build/evidence manifests.

## Evidence boundaries

Only a receipt tied to the final runtime hash is final evidence. The baseline run had two Unix-only DST fixture failures on Windows; the fixtures now use an explicit America/Chicago zone while preserving their 23/25-hour assertions. Intermediate runs passed 1,157 Atelier checks and 460 exam checks before the final scenery refinement. Card Studio passed 208 checks, with its remaining unchanged symlink test blocked by Windows privilege. These are not final cumulative counts.

Native tests use installed Anki 25.09.5 and generated profiles, with sync and single-instance forwarding disabled. They do not open the owner's profile. Home/Widgets rendering and actual native IO grading/Undo have been exercised. The real IO lifecycle exposed late sizing that the first browser stand-in did not reproduce; the correction must pass final native capture assertions.

Display scale comes from measured pixel and logical dimensions. Requests for 100% through Anki's UI-scale setting were clamped by the host; those captures remain 150%. GPU initialization warnings occurred with software rendering; no live GPU claim is made. The initial offscreen run failed and remains failure evidence.

Unperformed/incomplete release gates: macOS/Retina, physical keyboard-mode remotes, Windows 100/125/200% display configurations, native fullscreen/autohide combinations, third-party IO Enhanced/native edit acceptance, every custom media template, full native folder scheduler ordering, 30–60-minute endurance, uncoached newcomer testing, comprehensive composited contrast/accessibility review and the entire visual state matrix. Unsupported IO templates fail closed. Do not describe this candidate as universally compatible.

## Release boundary

Private repository: https://github.com/AAAAAAwd899/Atelier. No AnkiWeb listing or website destination exists. Staged website fields contain no public download or invented code. Future identity/migration, support wording and the exact installer hash require owner approval before public rollout. See the manual and professional review records.
