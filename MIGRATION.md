# Installation identity and preserving existing work

## Existing direct-file installations

Atelier 1.0.0 keeps `manifest.json` package **daedalus_atelier**. Install it over the earlier Atelier package; do not delete the old installation. Version 1 does not add a store conversion or reset any saved appearance/owner settings. The existing widget-route migration remains as implemented in rc6 and is not a new 1.0 migration.

Back up the collection/media, the add-on's `user_files` and customized configuration, the profile's complete `exam_sprout` folder, and the complete `workshop` folder including source blobs. Close Anki before manually copying files. Do not enable separate Sprout/Workshop writers alongside the integrated version.

Anki's documented direct-install manifest selects the add-on folder, while `user_files` is preserved during ordinary add-on upgrades. References: https://addon-docs.ankiweb.net/sharing.html and https://addon-docs.ankiweb.net/addon-config.html .

## Eventual AnkiWeb numeric identity

No numeric ID has been assigned or tested in this pass. AnkiWeb uses a numeric add-on folder, not this direct-file package name. The following is a release-maintainer procedure to test after an ID exists, not an already implemented migration tool:

- Start with a backup copy/spare profile. Save/close work, then disable the old direct-file package and restart before loading the numeric package. Keep the old files for recovery.
- Transfer Atelier's `user_files` and its customized config values through a reviewed process. Do not blindly copy `meta.json` wholesale: its installation/update metadata belongs to the new identity.
- The profile-local `exam_sprout` and `workshop` stores already have stable paths; do not duplicate or convert them. Verify saved sessions, drafts, sources, widgets, owner/world, and linked notes in the new installation.
- Confirm exactly one Atelier/controller runtime is active, including after restart/profile switching. Verify the disable/rollback path before recommending migration to existing users.

Do not ship a manifest conflict entry for a guessed numeric ID. Do not delete the direct-file copy until its data is backed up and the transition is verified. `package_release.py` intentionally refuses an unreviewed change away from `daedalus_atelier`.
