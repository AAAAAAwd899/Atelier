# Atelier 1.0.3

- Places the optional live Onigiri rewards room directly on Atelier’s Study desk while preserving its node identity, artwork, progress, controls, handlers, and original-page recovery path.
- Removes the large blank dashboard rows that Onigiri's full-page grid could retain after being embedded. Restaurant progress, four metrics, favorites, activity, and third-party widgets now pack into responsive natural-height rows from 320 to 1,725 pixels, while the original Onigiri page restores its exact markup and geometry when opened.
- Compacts the sidebar folder index to single-line rows with full-path tooltips and a direct **Open library** link. On short windows, Today and study scope fold into an accessible shortcut control to give folders room; expanding it restores every shortcut. The full scenic Library remains available for detailed organization.
- Keeps the live Onigiri rewards on the Study desk but collapses their large dashboard by default. **Show rewards** expands the original live widgets in place, preserving their node identity, input, handlers and settings route across navigation.

Private review candidate. The name and private package identity remain Atelier / `daedalus_atelier`.

- Consolidated visual roles in a generated design contract, with scoped home, planner, authoring, reviewer and native palette adapters. Removed the duplicate home presentation layer.
- Expanded the accepted catalogue from twelve to seventeen worlds with premium raster scenes for Moonlit Castle, Underworld, Mythic, Lakeside Cabin, and Sunset Cove. Each new world has its own accessible role palette, materials, type treatment, atmosphere, and matching Pip emblem family.
- Added a guarded **Save & next card** action in Card Studio. It saves the local draft, then opens a clean draft carrying the same source page, destination deck, tags, card style, selected note type, field mapping, and occlusion display preference so slide-set authoring stays coherent without copying the previous question, quotation, masks, or media.
- Added **Save & next slide/page** for multi-page sources. It advances to the next source page while retaining the authoring context above, so a deck can be built as an organized sequence without repetitive setup.
- Added Drafts & approval ordering by recently edited, source order, or destination deck so larger card sets remain easy to review.
- Added Project and Source filters to Drafts & approval, with source/page metadata on each row so slide-set drafts remain traceable.
- Added a guarded **Organize selected** action for unapproved drafts to change a destination deck and add shared tags without touching card content or Anki scheduling.
- Added a per-project **Default destination deck** choice. New drafts and split-note drafts start in the chosen deck, while individual cards remain editable before approval. The preference is kept locally by Card Studio and does not alter Anki scheduling.
- The project header now shows the active default destination at a glance, so a learner can verify where the next cards will go without reopening project settings.
- Added source coverage markers and a next unwritten slide/page shortcut, making it clear which source material still needs cards.
- Reorganized the Study desk sidebar into cohesive learning, creation and progress groups, with a visible study-scope card for selecting and starting the exact folder or lecture.
- Added a clear first step for new users and a direct **Study with Pip** action from the current focus. A matching saved plan opens directly; otherwise Exam Studio opens prefilled with the focused parent folders.
- Reworked Card Studio around card sets and a four-step creation path. Slides, PDFs, images, notes and text stay beside an ordered page rail; learners can select the exact source page, choose question, cloze, image or image occlusion, save a draft, and review it before adding it to an Anki deck.
- Added plain-language organization guidance beside Card Studio’s tag field: use tags for cross-class topics while the destination deck remains the card’s home. This follows Anki’s note/tag model without changing existing notes or scheduling.
- Clarified multi-parent exam setup: two or more separate course folders can be selected for one exam, with subdecks included and overlapping branches counted once.
- Added six authored raster companion families: a moon-crowned cat for cutesy worlds, leaf-cloaked Pip for green worlds, a tide otter, constellation owl, ember fox, and folded-paper crane. Each family has matching stage language and interaction copy; Pip’s effort model, study actions, saved settings, and tiny native reviewer behavior remain shared.
- Added whole-stage Fit image / Actual size controls for the exactly recognized stock native image-occlusion template. The base image and original mask canvas transform together. Unknown templates retain native rendering. Fixed late native stage sizing found in actual Anki.
- Preserved whole-folder shuffle, native scheduling and Undo, lecture labels, exam and card engines, source stores, drafts, saved practice, masks, remotes, built-in widgets and original-theme ownership. No database conversion or automatic update service was added.
- Added deterministic cumulative packaging, paired source verification, real screenshot matrices, isolated native probes, a real-interaction walkthrough and staged AnkiWeb information.

Remaining acceptance work is listed in `AUDIT-1.0.3.md`. AnkiWeb identity migration and public rollout wait for a real listing and owner approval. A GitHub push or website update does not update installed Anki add-ons.

- Added a clear-selection action to the draft inbox for safer batch organization across filtered pages.
- Added **Select all filtered** to the Drafts & approval inbox, with a filter-scoped clear toggle so multi-page lecture sets can be organized without repeating page selection.
- Kept compact Card Studio navigation legible with short labels beside its icons, so the mobile-sized bar remains understandable for new users.
- Added scoped **Export / share** actions to each library folder/deck menu. A parent folder can include its subdecks, while a single deck gives a focused handoff; Anki still owns the final format, media, and destination confirmation.
- Made project sharing explicit: **Open linked cards to export** opens the exact linked notes in Anki’s Browser and tells the learner to choose **Notes → Export**.
- Made specialized Card Studio types visible in the guided workflow: compare, sequence, apply, cloze, image, and image occlusion remain available in the same editor, with a plain-language prompt for opening Mask Studio after attaching or opening an image.
- Added a direct **Native mask editor** action beside source-page Mask Studio. It hands the original rendered page image to Anki’s supported Image Occlusion editor, preserving native rectangle, ellipse, polygon, and hide-mode choices.
- Added **Open selected in Anki** to exact note search selections, handing the selected note IDs to Anki’s native Browser for familiar export/share controls.
- Clarified the selected-note action tray so its compare, link, and export paths are visible before a user takes action.
- Added an explicit source-context notice when the viewed slide/page differs from the active draft, with **Start draft from this page** preserving the existing draft, carrying the current deck/tags/note setup into the new draft, and linking it to its exact source location.
- Updated the unpublished add-on information page so its inventory matches the seventeen-world packaged catalogue.

