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

The guided tour saves only its version and offered, skipped or completed state in these profile-local preferences. This marker does not leave your computer or authorize any provider request.

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


The voluntary study clock stores its mode, selected duration, elapsed seconds and optional sound/pin choices in a profile-scoped local `user_files/clock-*.json` file. It does not record the cards you view, send timing data, alter Anki’s statistics or start itself after an Anki restart.


## Optional Friends and shared folders

The Friends client ships **unconfigured**. Installing Atelier, opening its window, using the local companion journey or exporting an offline package makes no Friends request. Connecting the optional prepared service is a separate administrator/owner decision. Online sharing uses a configured HTTPS Auth/PostgreSQL/private-object service; the operator must publish its actual privacy/retention terms before activation. No hosted project, accounts or email delivery were created by this release work.

After connection, your explicitly requested sign-in sends the invited email/code to that service. It is separate from AnkiWeb and never asks for your AnkiWeb password. Access tokens stay in native memory for that profile session, not JavaScript or intentionally on disk; sign in again after restarting Anki. Display names, friend connections, hashed one-use invitation codes, recipient selections, version metadata and published packages are stored by the service. The operator can access them; private storage is **not end-to-end encryption**. Infrastructure providers can also process connection/account metadata according to their policies.

Publishing sends selected native course/deck content, note types, tags and referenced media, without scheduling or review history. **Automatic publishing** separately authorizes future content changes within the attached parents while signed in. Check those folders and recipients before opting in. Original source documents/projects, saved practice answers, local journal reflections and companion history are not part of these Anki deck packages. Source material embedded in the approved cards is still shared card content.

Recipients explicitly download and review a native import. A downloaded package and its later copies are outside revocation's control. Removing a friend, changing recipients or stopping a share blocks future authorized downloads; it cannot erase saved packages, backups or bytes already in flight. No public directory, contact upload, chat or automatic message to a friend is implemented. The prepared service's operator/security/backup/deletion requirements are in the matching source's `services/friends` documentation. The installer does not claim that these hosted obligations are already fulfilled.

Companion keepsakes, the chosen scene and private reflection are local profile preferences. Real native study activity is read to determine optional local eligibility; it is not uploaded for a leaderboard or used to manipulate ratings or scheduling. No competitive anti-cheat or permanent online activity record is claimed.
