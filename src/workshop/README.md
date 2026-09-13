# Workshop · Living Library & Card Studio

Version 1.0.0-rc.1 · desktop Anki add-on · Daedalus Works

**An installable engineering candidate, not a native-Windows-certified public release.**
The complete authoring/repair application is included. It is not a prototype that
only displays sample projects. The installer starts with your own empty local library.
Test screenshots are labelled sample data and are not an installed Anki screenshot.

## Install

Back up your Anki collection and use an unsynced test profile for initial acceptance.
Tools → Add-ons → Install from file… → Workshop_1.0.0-rc.1.ankiaddon.
Keep the extension unchanged and restart Anki. Open Tools → Workshop → Open Living
Library, the Workshop top-navigation entry, or Ctrl+Alt+W. Keep Exam Sprout and
Atelier installed; this is a separate package named daedalus_workshop.

## Begin with one source

1. Create a project and choose one of six original book bindings.
2. Import a PDF/image/text/document or paste a source passage.
3. Open the source in Card Studio. Select the supporting text and choose Use selected passage.
4. Write a question, cloze, image-based question, comparison, sequence, or application prompt.
5. Use Find existing cards first. Link an existing note or deliberately create a different one.
6. Save the local draft. Select it in the draft tray, Review & add, inspect the actual
   note count, possible duplicates, source, destination and workload assumptions, and approve.

A project becoming prepared means cards are ready, NOT that the material is mastered.
The learning scheduler and all normal review history remain in Anki.

## Included product surfaces

- Living Library: six original illustrated/engraved bindings, dimensional shelf,
  list view, archive, source/draft/note counts, useful preparation milestones.
- Card Studio: source beside the draft, pages and editions, selection/crop,
  source provenance, drafts/autosave, six authoring styles, field mapping,
  attachments, native image-occlusion handoff, preflight/approval, undo.
- Find: word ranking, full Anki search syntax, deck limits, complete pagination,
  source passage retrieval, existing-note links, original native Preview/Browser.
- Improve: reviewer context-menu/shortcut capture, technical/design checks,
  repair queue, actual before/after edits, literal batch edits/tags, splitting,
  2–3-note comparisons, source-change queue and manual reference rechecking.
- Media: read-only image/audio catalog, exact note references, additive reuse.
- Optional assistance: user-selected compatible chat and embeddings endpoints,
  exact-text consent, unapproved source-linked drafts and visible-match reranking.
- Settings: four appearances, motion/reduced-motion support, field protections,
  lifetime-session-only API key, first-pass planning assumptions, library export/import.
- Integrations: additive Atelier entry, exact-note-scope Sprout clipboard handoff,
  native Add/Browser/Preview/Sync/Check Media, specialist audio/editor entry,
  a small versioned API. No second pet, scheduler, or competing reviewer.

## Important boundaries

PDF text extraction is bundled. Visual PDF page rendering/cropping requires the
Qt PDF module supplied by some Anki installations; otherwise use extracted text
and Open original. Word/PowerPoint import extracts text, not a faithful page layout:
export those sources to PDF for visual pages. No OCR or automatic medical fact
verification occurs. Only keep/share source material you have permission to use.

Sources/drafts live at <Anki profile>/workshop/, separately from collection.anki2.
AnkiWeb does not synchronize this private database. Approved notes and their copied
media are ordinary Anki content. Export the local library separately to back it up.
Portable imports deliberately detach foreign note IDs and reset draft destinations.

AI is off by default. No key, remote service, embedding model, or funded provider
account is supplied. Semantic assistance reranks up to 30 visible candidates; it
is not a hidden whole-collection semantic index. Provider fees/policies apply.

Native image occlusion uses Anki's own mask editor and Add approval. Existing
occlusion/managed notes go to their own editor, not Workshop's simple field repair.
HyperTTS/Contanki/shared-deck services are not bundled or invoked through private APIs.
Sprout receives a clipboard search filter, not automatic private-plan writes.

## Verification and public-release gate

See docs/TEST_REPORT.md and Package_Verification.json. Python contracts use explicit
Anki/Qt doubles with real local SQLite fixtures. Browser tests execute production
JS/CSS, the actual Python bridge, and the supplied Atelier front end. These are NOT
real Windows Anki/Qt/FSRS/SM-2 tests. Optional-provider transport is mocked, with no
external service called. No public listing, download code, or universal compatibility
claim has been created. Run docs/NATIVE_ACCEPTANCE.md before public distribution.

## Developer reproduction

Python 3.13, pytest, Playwright with Chromium; Pillow/reportlab for test fixtures.
The runtime add-on requires no extra pip installation. Qt PDF is optional.

    python -m pytest -q --junitxml=docs/unit-results.xml
    python tools/test_ui.py
    python tools/test_advanced_ui.py
    python tools/test_home.py /path/to/Atelier.ankiaddon
    python tools/build.py /path/to/output
    python tools/verify_release.py /path/to/output --atelier /path/to/Atelier.ankiaddon

Run tests on extracted source, not inside your real collection. Fake native APIs
exist only in tests/ and tools/. The installed add-on contains neither tests nor
sample projects. The exact-archive verifier runs the tests against its own clean
installer extraction before issuing a successful receipt.
