# Atelier 1.0.3 — Your study space in Anki

Organize your classes, build cards from your sources, prepare for exams, and make Anki feel like your own space. Atelier includes Card Studio, Exam Studio, Pip, and seventeen visual worlds. Onigiri is optional.

## Install or update

Save your work and finish any import or card-adding operation. In an active practice session, choose **Save & close**. Back up your Anki collection and the local Atelier, exam, and source data described below.

In Anki, open **Tools → Add-ons → Install from file**, choose **Atelier-1.0.3.ankiaddon**, and restart Anki completely. Keep the file intact; do not unzip it. Install over your existing Atelier rather than deleting it. Your current appearance, widgets, groups, and saved work are retained.

Keep any separate **Exam Sprout** or **Workshop** add-on disabled. Their features are included here. Do not delete their data. Other add-ons, including Onigiri, can stay installed.

Confirm **Tools → Atelier · 1.0.3**. The cumulative folder-order contract originated against the accepted Anki **26.08.1** target. This candidate has also been exercised in isolated synthetic profiles on Windows desktop Anki **26.05** with the standard editor. Experimental editors, Anki beta releases, macOS, Linux, and specialized add-on combinations are not part of the verified support scope. This desktop add-on does not install on AnkiMobile, AnkiDroid, or AnkiWeb. Cards added to Anki can sync normally; your device still needs to support their card template and media.

## Start with what you need today

**Study desk** is your home. Add cards, Browse, and Sync remain easy to reach. The sidebar groups learning, creation, and progress tools so the next action stays visible. **Continue your work** brings back unfinished drafts, repairs, and saved practice. **Library** contains your Anki decks; **Card sets** contains the documents and drafts you use to build cards.

To study a class, find its folder in Library and set it as an active study. The **STUDY SCOPE** card shows the currently selected folders and due work. Choose **Edit** to select the exact folder or lecture, then **Study this scope** to begin with that material. **Quick study** uses your usual Anki schedule and studies one lecture at a time. Studying a whole parent folder is a separate, clearly labelled action. When a focus is active, **Study with Pip** opens the matching saved Pip plan or starts a prefilled Pip exam setup for those folders. Removing a group removes its shortcut, not its cards or their due dates.

## Build cards with Card Studio

Choose **Add cards**. Create a **card set** for a course, lecture, chapter, or topic, or return to one you already started. A card set keeps source files and drafts together; the destination **deck** is still the Anki deck that receives approved cards.

Add slides, a PDF, images, notes, or pasted text. PowerPoint imports retain slide order, extracted text, speaker notes, and embedded raster figures. When exact page appearance matters for masks, attach the matching PDF. Choose a specific slide or page from the ordered source rail, then create a question, cloze, image card, or image-occlusion mask beside it. This keeps large slide sets organized and makes it clear which source page each draft came from.

Card Studio saves drafts locally. A saved draft is **not yet in Anki**. Choose the destination deck, then **Review & add this draft**. Check the destination, note/card counts, and any duplicate or field-mapping warnings before confirming. **Drafts & approval** is the inbox for unfinished cards from every card set. When making a slide set, **Save & next card** keeps the current source page, destination, tags, card style, selected note type, field mapping, and occlusion display preference while opening a clean draft; it never copies the previous question, quotation, masks, or media.

For an image, use **Mask Studio** to cover the labels or regions you want to recall. Figure previews load as you reach them; masks and attachments use the original image, not the thumbnail. PDF page rendering requires Qt PDF in your Anki installation. PowerPoint and Word imports preserve extracted content and embedded figures; they do not promise an exact slide/page reproduction.

From a deck’s page, **Add cards here** selects that destination for the editor. Specialized note types and editor extensions can use **Tools → Atelier → Card Studio → Add cards in native Anki…**.

## Plan an exam

Open **Exam Studio**, name your exam, choose one or more parent folders or decks, and set your routine. You can combine two separate course folders in the same exam; each parent includes its subdecks and overlapping branches are counted once. The form is saved at its final **Save** step; leaving unfinished setup asks for confirmation. Active study folders are quick links for normal review, while an exam plan also contains the date and practice settings.

**Build exam plan** inside a source project selects its linked notes. Review the exact material before saving. It does not automatically add a plan or expand a document into an entire class.

## Practice without changing normal reviews

**Practice & mocks** uses your existing Anki cards. Choose the question count, time limit, and material, preview the actual selection, then start. Independent practice and self-marking do not change the cards’ Anki schedules.

A simulated exam keeps answers hidden until submission. The question map, flags, confidence, and written responses help you review afterward. **Save & close** stores an unfinished session for resumption. Merely closing a window is not a promise that responses are saved. A timed exam’s deadline continues while it is closed; saving does not pause the clock.

Results summarize your self-marks, not a predicted exam grade. Planning/readiness estimates are guidance, not a validated forecast. Your recorded Anki reviews and independent practice results remain separate.

## Study with Pip

**Pip Study** can use an active study group or a saved exam plan. You do not need to create a duplicate plan for an existing group.

Check the **Introduce new cards** setting before starting. With it off, the session is independent rehearsal. With it enabled, eligible new cards can receive real Anki ratings after you reveal the answer. Previously learned cards remain rehearsal. Pip’s petting and watering are separate from study progress.

## Make the home yours

Choose **Appearance** to select a world, spacing, motion, reviewer context, and supported Anki-window styling. The same world follows you through planning, practice, and card building. Custom interactive cards and occlusion masks retain their original layout. Use **Controls only** or **Original Anki** reviewer styling for a specialist template when needed.

**Widgets → Arrange widgets** adds, removes, reorders, and sizes your widgets. **Show on Study desk** also places a chosen widget on the main home. Choose **Save layout** to keep changes. **My note** saves when you choose **Save note**. Removing its widget does not erase the note.

Widgets work without Onigiri. Compatible installed add-ons can offer optional widgets. **More tools → Onigiri rewards — original page** opens Onigiri’s actual game and widgets when available; the **Atelier widgets** return takes you back to the built-in page. **Original Onigiri / other theme** lets that add-on keep control of its home and reviewer.

## Review progress, export, and sync

**Study progress** shows 7 or 30 Anki study days for your selected material. Answer events can include repeated answers to one card; they are not the same as distinct cards. Again percentage is not retention or mastery. The full Anki Statistics window remains available.

**Export cards** lets you search decks and put active classes first, then opens Anki’s own export options. Choosing a parent includes its subdecks. Selecting a deck does not write a file until you confirm in Anki.

**Sync** uses Anki’s normal synchronization. It does not include all local exam plans, source projects, drafts, widget notes, or Atelier preferences. **Anki tools** keeps Import, Export, note types, collection checks, preferences, profiles, Undo/Redo, and other original tools available.

## Back up all of your work

Anki’s collection backup is important, but it is not a complete Atelier backup. Close Anki before manually copying files. Keep these together:

- Your normal Anki collection and media backup.
- Atelier’s **user_files** folder inside its add-on installation. In **Tools → Add-ons**, select Atelier and choose **View Files**.
- Your Anki profile’s **exam_sprout** folder for exam records, saved sessions, and Pip effort.
- Your Anki profile’s complete **workshop** folder, including its database **and sources**. The database alone is not a complete source backup.

The Anki profile normally lives under `%APPDATA%\Anki2\<profile name>` on Windows. A custom data-folder launch can use another location. Keep backups outside the live profile and verify that they contain the expected files.

## When something is wrong

Use **Tools → Atelier** for original-home/reviewer recovery, widget recovery, and display diagnostics. Diagnostics are not sent automatically; review them before sharing, because error reports can contain file paths. Never include an API key or a private document unless you deliberately intend to share it.

To disable Atelier, use the Add-ons window and restart. Disable rather than delete it so your local preferences remain. To return to separate Sprout/Workshop installations, first disable the combined Atelier and restart; do not run two independent copies against the same data folders.

Before rolling back, save work and back up all stores. This release does not change the existing exam/source storage formats.

## Privacy and optional assistance

There is no telemetry or automatic diagnostic upload. Manual creation, search, and studying need no AI service. Optional provider assistance requires configuration and approval of the outgoing text. Suggestions remain drafts and must be reviewed before being added to Anki. Provider fees and policies apply. See **PRIVACY.md** for the full data and network boundaries.


## Remote controls

Open **Anki tools → Remote controls**, or **Tools → Atelier → Remote controls…**. Pair the remote using your computer’s Bluetooth settings or connect its USB receiver. Use Keyboard / Key mode when your device supports it. Atelier does not pair Bluetooth devices, scan for them in the background, or install a hardware driver.

Remotes sending your existing Anki shortcuts work without custom mappings. **Test remote buttons** receives button presses without showing answers or rating cards. Optional Assign buttons let you map unmodified keys. Choose Save to apply the mapping. Duplicate assignments are rejected. Use original Anki controls turns off Atelier’s custom mapping while retaining your saved assignments.

Custom controls operate only while the scheduled reviewer or its answer bar is focused. They do not take over Card Studio, typed-answer fields, practice windows, dialogs or other applications. Show answer only reveals; rating actions require the answer side. Holding a button does not repeatedly rate cards. The same keys on a regular keyboard share these mappings during review.

A keyboard-mode adapter cannot reliably identify which keyboard sent the key or report the remote’s battery state. Gamepad-only and proprietary remotes need their own supported driver/add-on; this release does not add native gamepad/USB-HID enumeration. Keep Atelier custom mapping off when using another mapping add-on, such as Contanki or the remote maker’s add-on. No controller-specific hardware or Bluetooth connection has been tested here.

## Reviewer spacing and protected cards

The text-card layout reserves the optional Onigiri header gap once, not in both body padding and an extra card margin. Short text answers that fully fit stay within the viewport. Long answers keep their normal scroll path; manual scrolling is not repeatedly reset. The answer bar uses less vertical space while retaining counts and stationary rating buttons.

Geometry-sensitive cards, including legacy image-occlusion templates and positioned mask overlays, do not get the text-card layout. Images and masks are not resized, wrapped or reparented. No masks are edited by this update. Use **Controls only**, or **Use original design for this note type**, when a custom design needs its own presentation. If a mask is already incorrect in the native card, a theme cannot repair that source without inspecting it.

The cumulative candidate has completed isolated native Windows Anki 26.05 tests with synthetic profiles for Home and Widgets, stock image occlusion, folder scheduling, and in-place add-on update behavior. macOS, physical remotes, every display scale, every card/media combination, real user collections, and live GPU Pip remain unverified. Test with sample cards before relying on custom remote mappings.


## Mix lectures when studying a folder

In Library, open the parent folder and choose **Study whole folder**. Leave **Shuffle between lectures** selected, confirm, then use Anki’s **Study Now** button. Eligible new cards and due reviews are shuffled within their normal categories across that folder’s lecture decks. The existing lecture label continues identifying the card’s source when enabled.

The shuffle is a **saved display-order setting** for that parent, not a temporary practice run. Other decks sharing the old preset are protected by a copy assigned only to the parent. Subdeck presets are not changed. Later edits to the original shared preset no longer propagate to that copied parent; manage it through Anki’s Deck options.

Anki still handles learning due times, new/review mixing, limits and sibling burying. Shuffling changes which due reviews appear first; it does not prioritize the oldest due cards. It does not move cards, reset due dates, or shuffle the answers inside a card. A random sequence can contain several cards from the same lecture in a row.

**Keep current Anki order** opens the same folder without modifying options. It does not reverse a shuffle saved earlier. To reverse a fresh change, use Undo before answering cards. Later, change Display Order or reselect the original preset in Deck options. New/learning ratings during normal review still affect scheduling as usual.

A filtered deck keeps its own selection rules. When supported settings cannot be read safely, Atelier shows an error and offers the current-order path rather than replacing the scheduler.
