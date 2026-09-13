# Atelier 1.0.0 — what stayed intact

The baseline is the **delivered 0.9.0-rc6 installer**, compared byte-for-byte with its source before editing. Version 1 contains **59 reviewed version/copy substitutions across nine existing runtime files**. It adds a user guide and support document and updates release/configuration/privacy documentation. The design accepted by the project owner is preserved.

## Exact boundaries

`release-1-baseline.json` records every input file. `release-copy-changes.json` records the old text, replacement text, and expected occurrence count. `release_copy.py` starts from the exact accepted source text, applies the complete reviewed list, and requires byte-for-byte equality with the release. It does not strip arbitrary changes until a test passes.

All **CSS, icons, scenery, images, widget layout code, mask logic, configuration defaults, storage formats/paths, assessment algorithms, native learning safeguards, provider consent, and publishing code** remain unchanged from rc6. The normal reviewer layout and original-provider boundaries are unchanged. No experimental renderer, new motion dependency, or data migration is introduced.

| Component | rc6 files | Unchanged bytes | Changed file |
|---|---:|---:|---|
| Bundled Sprout | 72 | 71 | `sprout/web/app.js`: reviewed user-facing explanations and integrated About wording only |
| Bundled Card Studio / Workshop | 80 | 79 | `workshop/web/app.js`: reviewed labels, accessibility names, and user-facing help only |

After applying the exact reviewed substitutions to their recorded baselines, every embedded runtime byte matches. Original provenance versions remain Exam Sprout 0.10.1 and Workshop 1.1.0-rc.1. Against the originally uploaded components, the existing integration boundary remains four modified Sprout files and two modified Workshop files; version 1 does not enlarge that boundary.

## Controls and saving remain meaningful

Add cards, Browse, Sync, exports, project/draft approval, exact project-to-plan handoff, active-group Pip, practice answer locking, saved-session resumption, card-local keyboard behavior, and independent built-in Widgets retain their existing routes. Original Onigiri is still a separate, optional destination rather than the built-in Widgets page.

Card draft autosave is not replaced with a new format. Practice still requires Save & close for durable resumption. Exam setup still saves at its final step. Timed saved sessions retain their deadlines. Independent practice remains separate from scheduled review, while explicit eligible-new-card learning retains native-rating authorization. Source originals are still used for masking and publication, not thumbnails.

## Evidence and scope

The current release verifier and packager enforce these boundaries, not just this document. They also check version identity, syntax, archive integrity, source equality, private-file/font exclusion, and reproducible packaging. User-reported visual/primary acceptance is recorded separately from automated execution and unperformed independent native Windows testing.
