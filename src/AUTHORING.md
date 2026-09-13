# Atelier 0.9.0-rc1 — integrated Card Studio

This is the full Atelier update: the accepted rc4 quiet reviewer, original exam
engine and Pip assets, plus embedded Workshop/Card Studio 1.1.0-rc.1. It is not a
separate patch and does not require a separate Workshop installer.

## Upgrade safely

Finish or explicitly save an open exam; close editors. Back up the collection,
Atelier user_files, and the profile-local workshop and exam_sprout folders. Disable
standalone Workshop and standalone Exam Sprout, including numeric-ID copies, then
fully restart Anki before installing this package through Tools > Add-ons > Install
from file. Do not delete the old data folders. Fully restart again after installation.
Keep Image Occlusion Enhanced or other format-owner add-ons enabled for their cards.

The package identity remains daedalus_atelier. The embedded modules deliberately
use the existing profile-local data paths; there is no copied second exam/library
database. Standard conflict metadata plus a runtime duplicate guard prevent two
known controllers writing to the same stores. Unusual older copies still need to
be disabled explicitly. Startup rollback removes only registrations owned by this
suite. Hold Shift at Anki startup to recover without loading add-ons if needed.

## Main actions

* Add cards in Atelier, the native top Add action and the native A shortcut open
  Card Studio. Unknown foreign shortcut handlers are not disconnected. Existing
  native Add buffers are not overwritten. An explicit native Add entry remains
  under Tools > Atelier > Card Studio.
* The ordinary bottom-left Edit button retains Anki's EditCurrent route. Native
  Image Occlusion opens its existing mask editor. Recognized Image Occlusion
  Enhanced notes invoke the already-installed owner's I/O editor after its normal
  save step. Ordinary/custom fields retain their native editor. No conversion is
  attempted; PDF Occlusion and other unknown formats keep their owning tools.
* Creating during scheduled review opens a modal Studio so typing cannot grade the
  card behind it. Active independent exams/practice must be saved or finished first.
* Studio opens on deliberate actions only: there is no new reviewer panel/overlay.

## Fast masking for new cards

Select an image, PDF page or embedded presentation figure, then Mask. Draw a box
and use Stamp to repeat its size. Separate questions gives each new mask its own
question; Same question groups masks until Next question. Select/Shift-select,
move, resize, duplicate, nudge, undo and redo remain local draft edits. Table mode
places a grid inside a manually selected answer region; adjust rows/columns and
choose per-cell, row, column or grouped questions. It does not infer table meaning.

Preview one question at a time and choose independently whether other answers are
covered. Save masks to a draft, then Review & add for explicit deck/card-count
approval. Published notes use Anki's stock Image Occlusion template/format. No
collection notes are added until approval. New question groups are new unlearned
cards. This fast composer is for new drafts: existing occlusion notes are edited
by Anki or their installed owner, not silently imported into a different format.

## Documents and fidelity

PDF text extraction is bundled; page images/masking require Qt PDF. Scanned pages
stay images; there is no OCR. PPTX uses presentation slide order, preserving speaker
notes, table text, hidden-slide status and supported embedded raster figures. It
is a source extraction, not a reconstructed slide. Use Attach PDF layout to pair a
matching slide-export PDF (same page count) with the original presentation; notes,
figures and original bytes remain. Verify the first/last slide: matching counts do
not establish that the two files are the same presentation.

DOCX includes paragraph/table text and embedded raster figures; it has logical
text sections, not original printed pagination. ODT/ODP, UTF-8 text/Markdown/HTML,
PNG/JPEG/WebP and CSV/TSV source tables are accepted. CSV/TSV imports make readable
source sections, not automatically approved flashcards. Legacy .ppt/.doc, macros,
OLE objects, charts/vector graphics or encrypted material are not silently rendered.
Export those to PDF or an image in the originating application. Remote relationships
are not fetched. Malformed/oversized archives are refused.

## Privacy, history and release boundary

Local projects, originals, drafts and optional exam responses are not covered by
AnkiWeb Sync; approved note/media content follows ordinary Anki synchronization.
AI remains off by default with explicit per-request consent. PDF exports and project
archives may contain sensitive/copyrighted material; inspect before sharing.

This authoring update does not change the rc4 engine, readiness coefficients,
learning/scheduler paths, result stores, quiet reviewer or Pip bytes. No native
Windows Anki 25.09.5 / Qt process ran here. IO editor focus/save/undo, actual card
generation, Qt PDF, source clipboard, sync, native startup/update and the complete
installed-add-on combination remain native acceptance gates. IO Enhanced's own
update/return behavior remains its responsibility; same-card return is not certified
for all formats. This is a native-acceptance candidate, not a published stable release.
