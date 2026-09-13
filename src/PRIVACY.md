# Atelier — Privacy and your data

Atelier does not include telemetry, advertising, or automatic diagnostic uploads. It does not need an account to organize, create, or study your cards. Anki Sync, Anki updates, external links, your card templates, and other installed add-ons may use the network independently; Atelier does not block or sandbox them.

## What stays on this computer

Anki keeps your approved notes, cards, copied media, schedules, and review history. Atelier keeps its own supporting records in your Anki profile and add-on data folders:

| Data | Location and saving behavior |
|---|---|
| Focus folders, favorites, widget layouts, widget notes, and recovery copies | Atelier's per-profile `user_files`. Layouts and widget notes save only when confirmed. Appearance settings use the add-on configuration. |
| Exam plans, results, Pip effort, and saved practice | The profile's `exam_sprout` folder. Unfinished practice saves through **Save & close**, including written responses, question order, flags, and timing. Timed deadlines continue while closed. Completed-response retention is optional. |
| Source documents, images, projects, drafts, versions, repair items, and note links | The profile's `workshop` folder, including `workshop.sqlite3` and `sources`. Card drafts keep their existing local autosave. Adding or changing Anki notes requires review and approval. |

**Anki Sync does not include all of these local records.** A collection backup alone is not a complete Atelier backup. Back up the whole `exam_sprout` and `workshop` folders and Atelier's `user_files` as well as the collection. Atelier's local files are **not encrypted** by the add-on; operating-system/device protections are separate.

## Optional AI assistance

Manual creation, search, source import, and study work without a provider. Optional chat and embedding assistance uses a compatible endpoint that you configure. No provider request is made merely by installing Atelier, importing a source, or saving a draft.

Each request asks permission for the outgoing text. Check the destination and content before approving it. Use only material you have permission to share. The **API key** is held for the session rather than intentionally stored in Atelier's project or exam files. Service fees, data retention, and provider policies are outside Atelier's control. Returned suggestions remain unapproved drafts, not verified facts.

## Diagnostics, exports, and other add-ons

Diagnostics are copied or exported only when requested. Display diagnostics avoid card text and deck names, but error details can include file paths or command context. Review reports before sharing. Source archives, practice exports, and saved sessions can contain private material.

Compatible installed add-ons can register optional home widgets. They appear after you add them. Visual isolation is not a security sandbox: another add-on's own data, code, and network behavior remain its responsibility. Atelier's widget API does not install providers or import arbitrary website embeds.

Onigiri rewards, specialist editing tools, and shared-deck services remain separate products. Choosing their original appearance does not authorize Atelier to overwrite their saved settings or reward records. Approved cards subsequently belong to the normal Anki collection and can be handled by those other products according to their own behavior.

## Scheduling and learning information

Normal Anki review changes scheduling. Independent rehearsal, mocks, and original-card result review do not. Pip's explicitly enabled **Introduce new cards** workflow may submit real Anki ratings for eligible new cards after reveal. Self-marks and planning/readiness indicators are not validated predictions of an exam grade.

Your source text, images, teaching material, and AI suggestions are not automatically fact-checked. Keep only material you are authorized to copy and distribute.
