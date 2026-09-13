# Exam Sprout 0.10.1

Complete Anki desktop add-on: exam countdown, study plan, experimental readiness tiers, up to 500-card mock exams, targeted Pip Study, original-card mistake review and the integrated living Pip companion.

## Install

Tools → Add-ons → Install from file… → select `Exam_Sprout_0.10.1.ankiaddon` → fully restart Anki. Do not unzip it. Keep Atelier installed; this is the complete Exam Sprout replacement under the same `exam_sprout` identifier. Back up your collection and start in an unsynced test profile. The separate UPLOAD_ONLY archive is for the AnkiWeb server, not local installation.

## Windows update repair in 0.10.1

Pip plays native animations from a retained memory buffer rather than an open file.
No art, exam, readiness, storage or scheduling behavior was changed. If installation
fails with WinError 32 on a Pip image, fully quit Anki and hold Shift while starting
it; install the complete file in safe mode, then restart normally. See
[Windows recovery instructions](docs/WINDOWS_UPDATE_RECOVERY.md). Do not delete your
profile data or reinstall Anki itself for this error.

## Included features from 0.10.0

Projected readiness has its own F−…A+ / S scale and evidence label, separate from lifetime Pip effort. It uses observed native/self-marked correctness, recency, cold retrieval and card-variant/topic coverage. Sparse/missing evidence prevents a confident-looking high tier. No evidence shows unknown rather than F−. The algorithm is unvalidated and is NOT a promised grade, a passing probability, or a guarantee. See docs/READINESS_METHOD.md for exact weights, caps and limitations.

Build 1–500-question fixed mock exams or targeted rehearsal, use relative deck weights, choose cold-only retrieval, set 0–720 minutes, preview allocation, mark mental/written answers, confidence, flags and error categories, jump between questions, submit early and self-mark. Save & close explicitly preserves one unfinished session and its written answers locally; timed mocks keep counting while closed. Review original misses or all original questions with retained responses and answer reveal. JSON result export excludes written prose.

Pip Study deprioritizes recently correct material and prioritizes unresolved misses/confident mistakes and delayed checks. It prompts uncued explanation, application and comparison—not generated multiple-choice questions. Learned-card rehearsal remains schedule-free. With Introduce new cards explicitly enabled, a currently active, unfiltered NEW card may receive a real Anki Again/Hard/Good/Easy rating after reveal. Identity, status, scope and collection are rechecked immediately before the native operation. Remaining learning steps belong to normal Anki review. Mocks never submit scheduling ratings.

Pip grows from one effort point per unique studied note/UTC day, across exams. Wrong effort counts; playing does not. The prior live 3D model, clarity/smoothness repairs, 46px reviewer companion, palette presets and Atelier adapter remain included. No new sidebar or card overlay is introduced.

## Privacy and release scope

Local profile files only; no account, telemetry, external AI or remote renderer. Completed written-answer saving is off by default and opt-in; explicit unfinished drafts are separately consented. See docs/PRIVACY.md.

**Release candidate, not native-certified.** Automated logic/SQLite, Anki/Qt doubles, real Chromium UI/WebGL and exact-Atelier tests do not replace a real Anki installation. In particular, verify the new native NEW-card grading boundary and your own card templates before public release. Target: Windows Anki 25.09.5 / Qt 6. No other platform/version or AnkiWeb server upload acceptance is certified. This is a desktop add-on distributed through AnkiWeb, not code running in the AnkiWeb browser or mobile apps.

Publication materials and the required native gate are in docs/ANKIWEB_PUBLISHING.md and docs/LIVE_ANKI_CHECKLIST.md. Nothing has been published and no AnkiWeb ID was invented.
