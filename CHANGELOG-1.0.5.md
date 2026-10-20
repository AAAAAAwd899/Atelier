# Atelier 1.0.5

- Adds a first-run, optional guided tour of the real Study desk, library, study scope, Card Studio, Anki editor, multi-folder exams, practice, Pip, progress, tools, widgets and appearance.
- Highlights the relevant control, adapts to compact windows, supports Back, Escape and keyboard focus, and offers useful first tasks at the end. Replay it from the footer, Anki tools or Tools → Atelier → Guided tour.
- Saves only a profile-local help marker. Touring does not add, move, merge, publish or grade cards, and does not change settings or provider consent.
- Declares Anki 25.09.5 as the minimum desktop version and updates the native configuration schema to include all 17 existing worlds.
- Adds a read-only installer format/license-notice gate. Retains the complete 1.0.4 layout, recent-study ordering, engines, artwork and saved-work behavior.
- Updates the namespaced PDF parser from pypdf 5.9.0 to pinned 6.21.1 for published resource-limit fixes. Changes to upstream code are limited to relative imports for isolation; four obsolete private parser modules are retired. The source importer, publishers, mask logic, stores and exam engine are preserved.

This is an independent desktop add-on. AnkiWeb publication and automatic listing updates still need the owner's actual listing and approval.
