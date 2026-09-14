# Atelier 1.0.3

Private review candidate. The name and private package identity remain Atelier / `daedalus_atelier`.

- Consolidated visual roles in a generated design contract, with scoped home, planner, authoring, reviewer and native palette adapters. Removed the duplicate home presentation layer.
- Added five authored local scene assets: Storybook Castle, Underworld, Mythic Code, Cabin, and Golden Shore. The original twelve worlds, artwork, fonts, and engine files remain intact. Reworked spacing, compact controls, workspace hierarchy, and panel contrast.
- Added a guarded **Save & next card** action in Card Studio. It saves the local draft, then opens a clean draft carrying the same source page, destination deck, tags, card style, selected note type, field mapping, and occlusion display preference so slide-set authoring stays coherent without copying the previous question, quotation, masks, or media.
- Added **Save & next slide/page** for multi-page sources. It advances to the next source page while retaining the authoring context above, so a deck can be built as an organized sequence without repetitive setup.
- Reorganized the Study desk sidebar into cohesive learning, creation and progress groups, with a visible study-scope card for selecting and starting the exact folder or lecture.
- Added a clear first step for new users and a direct **Study with Pip** action from the current focus. A matching saved plan opens directly; otherwise Exam Studio opens prefilled with the focused parent folders.
- Reworked Card Studio around card sets and a four-step creation path. Slides, PDFs, images, notes and text stay beside an ordered page rail; learners can select the exact source page, choose question, cloze, image or image occlusion, save a draft, and review it before adding it to an Anki deck.
- Added plain-language organization guidance beside Card Studio’s tag field: use tags for cross-class topics while the destination deck remains the card’s home. This follows Anki’s note/tag model without changing existing notes or scheduling.
- Clarified multi-parent exam setup: two or more separate course folders can be selected for one exam, with subdecks included and overlapping branches counted once.
- Added authored vector Pip world accents: soft cat companion treatment for cutesy worlds, botanical leaves for green worlds, tide/orbit/ember/paper motifs for the other worlds. Pip’s growth stages, controls, animation and study behavior remain shared.
- Added whole-stage Fit image / Actual size controls for the exactly recognized stock native image-occlusion template. The base image and original mask canvas transform together. Unknown templates retain native rendering. Fixed late native stage sizing found in actual Anki.
- Preserved whole-folder shuffle, native scheduling and Undo, lecture labels, exam and card engines, source stores, drafts, saved practice, masks, remotes, built-in widgets and original-theme ownership. No database conversion or automatic update service was added.
- Added deterministic cumulative packaging, paired source verification, real screenshot matrices, isolated native probes, a real-interaction walkthrough and staged AnkiWeb information.

Remaining acceptance work is listed in `AUDIT-1.0.3.md`. AnkiWeb identity migration and public rollout wait for a real listing and owner approval. A GitHub push or website update does not update installed Anki add-ons.
