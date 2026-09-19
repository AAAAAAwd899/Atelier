# Atelier 1.0.3

Private review candidate. A shared design contract generates seventeen-world web/native palette adapters. Home and Widgets use more compact layouts, near-solid work panels and locally packaged landscapes. Five new premium raster worlds add Moonlit Castle, Underworld, Mythic, Lakeside Cabin, and Sunset Cove. Saved work and the existing engine routes remain intact.

The Study desk now groups learning, creation and progress tools and shows the exact selected study scope. Its no-focus state leads with **Set your focus** so a new learner chooses the folders they intend to study before browsing deeper, while Browse library remains immediately available beside it. Its atmosphere control is a small, world-aware scenic tile so the sidebar has a visual anchor without competing with navigation. Card Studio presents source projects as card sets and guides learners from slides, PDFs, images, notes or text through exact page selection, question/cloze/image/image-occlusion creation, saved drafts and final deck approval. Its **Save & next card** action carries the current source page, destination, tags, card style, selected note type, field mapping, and occlusion display preference into a clean draft for efficient slide-set authoring without copying the previous question, quotation, masks, or media. Multi-page sources also expose **Save & next slide/page**, which advances the source page while preserving that same authoring context. The source rail marks pages with saved drafts and can jump to the next unwritten page. The Drafts & approval inbox can be filtered by project or source, ordered by recently edited, source order, or destination deck, and can organize selected drafts’ destination, added tags, and exact tags to remove in one guarded step before approval.

Each project can also remember a **Default destination deck** for new and split-note drafts. A card’s destination remains visible and editable before approval; the preference is local to Card Studio and does not change Anki scheduling.
The project header repeats that destination so the next-card home is visible while you work.

On compact Card Studio windows, the bottom navigation keeps short text labels beside its icons so Create, Import, Sets, Drafts, Find, Repairs, Media, and Settings remain understandable without relying on icon recognition.

Library folder and deck menus now include a scoped **Export / share** action. Choose a parent folder to include its subdecks or one deck for a focused handoff; Anki’s normal exporter still owns format, media, destination, and final confirmation. The Card Studio guide also names compare, sequence, application, cloze, image, and image occlusion card types up front, while the existing Mask Studio and native occlusion routes remain unchanged.

Image-backed source pages also expose **Native mask editor** directly beside Mask Studio. It hands the original rendered page image to Anki’s supported Image Occlusion editor, so rectangle, ellipse, polygon, and native hide-mode choices remain available without first creating a separate attachment.
When you find exact notes in Card Studio, **Open selected in Anki** carries that selection into the native Browser so Anki’s familiar export/share controls are one step away.
The selection tray explains those choices in place, including when to compare, link, or export the exact notes you selected.
Project pages use the same exact-note handoff with **Open linked cards to export**, followed by Anki’s native **Notes → Export** command.

Recognized stock native image-occlusion cards gain Fit image / Actual size. The whole image-and-canvas stage scales together after rendering, including late native sizing. Source images, mask coordinates and card templates are not rewritten. Unknown templates retain native rendering.

The verified 1.0.2 whole-folder shuffle, exam/card engines, stores, publication approval, Undo, masks, remotes and original-theme mode are cumulative. Read the accompanying audit for tested hosts and unperformed acceptance checks. This installer does not publish itself or update an AnkiWeb listing.

---

Earlier release notes are historical:

# Atelier 1.0.2

## Mixed-lecture folder study

Study whole folder now offers **Shuffle between lectures**, selected by default, or **Keep current Anki order**. Confirming Shuffle saves the selected parent’s native new-card gather order, new-card sort order, and review sort order. When its preset is shared, a copy is assigned only to that parent.

Individual-lecture study, card destinations, due dates, learning-step timing, daily limits, sibling burying and new/review mixing settings are retained. The existing lecture label follows each card’s own deck. Shuffle does not guarantee alternating lectures, nor a new random seed on every reopening.

This is a saved Anki setting, not a temporary mock. Random review order stops prioritizing the oldest due cards first. Use Undo before reviewing to reverse the change, or use Deck options to change order/reselect the original preset. Keep current makes no changes; it does not restore an earlier preset.

No exam, source, card-publishing, masking, remote or widget engine was replaced. No provider request, data migration, public upload or GitHub repository creation is performed by this release.

---

## Earlier release notes (historical)

# Atelier 1.0.1

- Correct duplicate reviewer header spacing and fit short text cards after Anki renders them.
- Preserve long-card scrolling and stronger image-occlusion/positioned-template boundaries.
- Keep custom card animations and mask pseudo-elements under their original template.
- Add optional keyboard-mode Remote controls with a safe button test, learning/assignment, duplicate checks, and foreground reviewer guards. No new reviewer overlay.
- Preserve all bundled exam and authoring engines, templates, data formats, imagery and styles outside the specified reviewer patch.
- Native hardware and Windows/macOS acceptance are separate from automated checks.

## Earlier release

# Atelier 1.0.0

**A complete study space for Anki: organize, create, prepare, and review.**

Atelier 1.0 brings the integrated study, organization, and card-building tools into one release. It keeps the layout and primary workflows accepted in 0.9.0-rc6. The final pass updates version information and user-facing explanations, not the assessment, card-building, or storage algorithms.

## Included

Seventeen visual worlds; a complete home with Add cards, Browse, and Sync; a searchable library with natural sorting and active study groups; independent customizable widgets; study progress and active-first export selection; Card Studio with sources, drafts, image masks and approval; Exam Studio with planning, practice, written responses, saved sessions and results; and Pip with clearly labelled rehearsal or new-card learning. Exam plans can combine multiple parent folders, and Pip’s companion accents adapt to each world while preserving the shared growth and study behavior.

Original Anki tools remain available. Onigiri is optional and has its own explicit original-page route. Specialized card designs retain their appropriate rendering and editing paths.

## What changed from 0.9.0-rc6

- Atelier now identifies itself as **1.0.0** in its installation metadata, menus, and interface.
- Appearance, widget, progress, export, and card-building explanations use clearer everyday language.
- Exam Studio no longer calls the integrated release a preview or exposes development wording as product instructions.
- Updated user guide, installation/recovery instructions, privacy details, and release documentation.
- Accepted layouts, icons, world artwork, defaults, store locations, and primary action routes are unchanged.

## Install or update

Save and close work and wait for imports/card adding to finish. Back up the collection, Atelier's `user_files`, and the profile-local `exam_sprout` and complete `workshop` folders. Keep standalone Sprout and Workshop disabled.

Use **Tools → Add-ons → Install from file**, select **Atelier-1.0.0.ankiaddon**, and restart Anki completely. Do not unzip the file or delete the existing Atelier installation. Confirm **Tools → Atelier · 1.0.0**. Existing records, preferences, and widget layouts are reused without a new migration.

## Good to know

**Windows desktop Anki 26.08.1** is the release target. The user reported visual and primary-workflow testing passed before this final text-only pass. Automated regression and packaging evidence are in the accompanying release report; this is not a claim that every third-party combination or native feature was independently tested.

Ordinary review affects scheduling. Independent practice does not. Pip's **Introduce new cards** option can apply real Anki ratings after reveal. Timed practice deadlines continue while closed. **Save & close** is required to retain unfinished practice.

Anki Sync and its collection backup do not include all local Atelier data. Optional AI assistance requires its own service configuration and explicit approval. Source images and note content are not automatically fact-checked. See **USER-GUIDE.md** and **PRIVACY.md**.

Atelier has not been uploaded to AnkiWeb by this release process. The supplied installer updates the existing `daedalus_atelier` installation directly.

- Added a clear-selection action to the draft inbox for safer batch organization across filtered pages.
