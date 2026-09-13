# AnkiWeb publication handoff — 0.10.1 release candidate

**Prepared, not uploaded or published.** No AnkiWeb account was accessed and no install code has been allocated here. AnkiWeb is the distribution destination; this is a desktop Qt 6 add-on, not an extension running inside the AnkiWeb browser reviewer or mobile apps.

## Files

`Exam_Sprout_0.10.1.ankiaddon` is the complete local installer. It replaces the `exam_sprout` sideloaded folder. Keep Atelier installed. Do not unzip the installer before installation.

The separate **AnkiWeb publication ZIP** contains `UPLOAD_ONLY_Exam_Sprout_0.10.1.ankiaddon`, a listing, privacy/method notes and screenshots. Its code/assets are identical to the tested local installer. Only its manifest adds `conflicts: ["exam_sprout"]`, so the numeric AnkiWeb installation disables the old sideloaded copy. **Do not install the UPLOAD_ONLY archive locally**: its conflict entry targets the sideload package. Use the normal installer to test locally.

Official docs: https://addon-docs.ankiweb.net/sharing.html and https://addon-docs.ankiweb.net/addon-folders.html . AnkiWeb uses its numeric item ID as the installed folder and only uses the conflicts key from the downloaded manifest. All runtime exports resolve their actual installation folder; user data remains profile-local.

## Publication gate

Do not advertise universal/native compatibility from the automated test counts. Current checks exercise Python logic, SQLite fixtures, explicit Anki/Qt test doubles, Chromium UI/WebGL and the exact uploaded Atelier front end. They do NOT execute a real Windows Anki scheduler/Qt process. Target environment: Windows Anki 25.09.5 / Qt 6. Other desktop versions/platforms are not certified. `grade_now` availability is checked at runtime. No maximum-version claim is justified yet.

Before setting a public supported-version range, finish LIVE_ANKI_CHECKLIST.md in an unsynced disposable profile. The new native NEW-card grading path is a **required gate**, not an optional cosmetic check. Confirm import/update, actual Grade Now state/undo behavior, real card templates/media/occlusion, the 46px footer companion, and restart/resume. Save screenshots/results. Only then update the listing from release candidate to release.

The distribution is asset-heavy (matching 3D fallback/native animations). ZIP structure is validated locally, but actual AnkiWeb upload-size acceptance, server scanning, login, description formatting and publication acceptance have NOT been tested. Do not remove required fallback assets or falsely claim server acceptance to fit an unknown size cap. If the server rejects it, use the current server's message to decide a format/asset change, then rerun packaging tests.

## Upload steps

After the native gate, sign into the owner's AnkiWeb account, open shared add-ons, and choose Upload. Supply the UPLOAD_ONLY installer, the reviewed listing text, a genuine support/contact destination the owner monitors, the verified version range, and the included production screenshots (labelled sample data). AnkiWeb assigns the numeric install code. Do not invent an ID or a test-supported range.

Then install through that assigned code in a second disposable profile with the old sideload copy present. Verify the conflict disables the old copy, one controller is active, actual numeric asset paths work, and profile-local plans still load. Test a subsequent update before announcing automatic updates.

For subsequent sideload/numeric duplicates of this version, a main-window singleton prevents double hook registration. Still remove/disable duplicate older copies when not installed through AnkiWeb's conflict mechanism.

Rights and metadata: this bundle includes the original Exam Sprout MIT license and local original Pip renderer/assets; it bundles no Anki/Qt/Chromium binaries and no user card collection. The owner should verify the support destination, author/branding and distribution terms before publishing. No website, release post, source repository or public listing was created by this packaging step.


## Windows replacement test

Follow WINDOWS_UPDATE_RECOVERY.md for the first upgrade from a filename-backed
Pip release. In a disposable native Windows profile, verify install after safe
startup, play/pause native Pip, then verify a subsequent normal update can replace
its artwork without WinError 32. Exit/restart after every update; do not use
partly removed old program files. Confirm stored exams/results remain. This
new native gate has not been checked by the current Linux/double-based tests.
