# Required native release gate — 0.10.1

Use a backed-up, unsynced disposable profile in the target Anki 25.09.5 installation. Install the full normal `.ankiaddon`, retain Atelier, and fully restart. Do not interpret automated doubles as completion of these checks.

## Critical scheduling boundary

Create one NEW basic card, one active learned card, one suspended card, one buried card and one card in a filtered deck. Record their card-info state and native review histories before testing.

In Pip Study, explicitly enable Introduce new cards. Reveal the NEW card and use an Anki rating. Check that exactly that card gains one real native rating and joins the appropriate learning/review state. Double-clicking must not add a second rating. Remaining learning steps should appear in normal Anki review. Confirm native Undo reverses the native change. Test Again and Good at minimum, with both SM-2 and FSRS if support for both is advertised.

Rehearse the learned card through Pip Study, Focus, an exam, and mistake review. No native intervals/reps/queues/revlog entries should change. Suspended/buried/filtered cards must never become writable new-learning items. Change/move a displayed new card in another window: the stale rating must be refused without advancing. A Grade Now unavailable/error message must not create success history.

## Exam flow

Run 25- and 200-question mocks with representative and targeted blueprints. Check weighted allocation, one-note deduplication, cold-only exclusions and disclosed shortfalls. Answer some orally with Mark answered, some in writing, assign confidence, flag/jump/back. Submit early with unanswered items. It must lock responses, prevent post-reveal credit on previously unanswered items, and show correct partial-credit totals/error categories. Review original misses and all originals; written responses must correspond to the right card.

Save & close a timed mock. Restart Anki and resume: order, answers/flags/confidence remain; timer keeps counting while closed. Resume an expired timed mock: it opens the grading phase without an extra answering interval. Discard deletes only the explicit saved draft. Test an ungraded interrupted session and a partially graded saved session. Export result JSON and confirm it excludes written prose.

## Templates and isolation

Test basic, reversed, cloze, built-in image occlusion, the user's third-party occlusion template, typed answers, audio and MathJax. Fit card must scale images and masks together. The written pane starts closed. A template failure should permit skip/close and must not count as a successful mark or native learning rating. Reviewer-only third-party hooks may differ in preview-based practice; do not claim automatic typed-answer difference grading.

## Presentation and lifetime

Readiness (F−…A+ / S / unknown) is visibly separate from Pip's effort meter and includes the no-guarantee warning. Switching exams changes readiness, not lifetime Pip growth. New study effort counts even when wrong; petting/watering do not.

Normal review retains the 46px footer Pip and no sidebar/over-card drawing. Test high DPI, narrow windows and crowded controls: Pip hides instead of overlapping. Verify idle/pet/water, reduced motion, hide/restore, multiple exams, light/dark/Atelier themes, and repeated opening/closing. Confirm profile switching and full sync cannot leak answers into another profile or leave stale native writes.

Finally test the assigned numeric AnkiWeb install/update and conflict behavior before declaring AnkiWeb distribution verified. Record Anki/Python/Qt/OS/add-on versions and actual results. Any failure blocks an unqualified public release.


## Windows replacement test

Follow WINDOWS_UPDATE_RECOVERY.md for the first upgrade from a filename-backed
Pip release. In a disposable native Windows profile, verify install after safe
startup, play/pause native Pip, then verify a subsequent normal update can replace
its artwork without WinError 32. Exit/restart after every update; do not use
partly removed old program files. Confirm stored exams/results remain. This
new native gate has not been checked by the current Linux/double-based tests.
