# Install and recover Atelier 1.0.3

This is a private review candidate. See AUDIT-1.0.3.md for the exact tests and open acceptance gates.

1. Finish or save your current work, then back up your Anki collection and media. Separately copy Atelier's add-on `user_files` and the profile-local `exam_sprout` and `workshop` folders while Anki is closed. Anki Sync does not back up these local stores.
2. Open Anki → Tools → Add-ons → Install from file. Select `Atelier-1.0.3.ankiaddon` and restart Anki. Keep the existing `daedalus_atelier` installation identity; do not delete it to update.
3. Keep the independent Exam Sprout and Workshop add-ons disabled when using Atelier's bundled engines. Choose Atelier as the visual owner when prompted. Appearance remains reversible, including original-theme mode.
4. Inspect your existing decks, drafts, source projects, masks and saved practice before continuing. No store conversion is part of this upgrade.

Normal Anki review changes scheduling. Folder shuffle saves native ordering options after its explicit confirmation; it is not a temporary queue. Practice and authorized Pip new-card learning retain their existing distinct behavior.

For problems, disable Atelier in Tools → Add-ons and restart to use the original Anki interface. Preserve the local stores. To roll back, reinstall the verified 1.0.2 installer over the same package identity, then restart. Restore a backup only after identifying which data needs recovery; replacing a collection can lose newer study activity.

The image view control supports only the exactly recognized stock native IO template documented in the evidence. Actual size restores the native view. Other templates keep their native layout; source images and stored masks are not rewritten.

## Eventual AnkiWeb installation

There is no AnkiWeb code yet. A private `daedalus_atelier` installation does not automatically become a future numeric AnkiWeb installation. Before public rollout, back up and test migration of the local add-on preferences and stores in a disposable profile, then document the one-time switch. Do not run both identities together. Once the numeric listing exists, approved releases must update that same listing; a website or GitHub push alone does not update installed copies.

Anki's [official packaging guide](https://addon-docs.ankiweb.net/sharing.html) distinguishes private package manifests from AnkiWeb downloads. This installer is flattened correctly and retains the private identity. Account eligibility, current upload limits and the real numeric listing must be checked when publishing becomes possible.
