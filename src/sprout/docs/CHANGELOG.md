# 0.10.1 — Windows animation file-lock repair

- Native Pip movies now receive memory bytes through QBuffer, not an installed
  file path. This removes the persistent Pip animation file handle implicated in
  the user's WinError 32 during add-on replacement.
- Retain current frames across pause/resume, release decoder/device contents on
  cleanup, bound inputs and avoid retry loops for unavailable animation assets.
- Full 0.10.0 feature set and all visual assets are retained. No change to the
  exam/readiness/new-learning algorithms, storage, reviewer layout or card scope.
- Add regression tests and safe-mode recovery instructions; first upgrade from
  the old running filename-backed player must occur after closing Anki completely.
- Existing native Windows/scheduler/publication gates remain unresolved.

# Changes

## 0.10.0 — assessment and targeted study release candidate

- Separate experimental projected readiness (F−…A+ / S) from lifetime Pip effort. Display evidence strength, topic gaps, sensitivity, method and no-guarantee notice. No evidence remains unknown.
- Add conservative note/day evidence deduplication, actual card-variant coverage, delayed retrieval, target-date shrinkage, broad cold-mock gates and high-emphasis blind-spot caps. Confidence and petting add no grade points.
- Expand mocks to 1–500 unique questions and timers to 720 minutes. Representative fixed blueprints and adaptive targeted rehearsal are labelled separately; cold-only eligibility never silently backfills.
- Add mental/written attempted markers, pre-answer confidence, mistake categories, confidence-error reporting, original-card review-all and outcome-only JSON export.
- Add explicit Save & close / resume / discard for one locally saved unfinished session. Timed mocks keep counting while closed. Expired mocks resume in grading. Optional completed-answer retention remains separate and off by default.
- Add Pip Study: prioritize unresolved/confident misses and delayed checks, downweight recently correct cards, and show uncued explanation/contrast/application prompts. These prompts do not generate new case or multiple-choice questions.
- Introduce currently NEW cards only through explicit, guarded native Grade Now ratings inside CollectionOp. Learned-card rehearsal and mocks never reschedule. Render errors, changed card/profile/collection and duplicate in-flight actions cannot submit a rating. Native acceptance is mandatory before public release.
- Track companion effort independently across exams with one point per unique note/UTC day, including wrong-but-graded practice. Preserve 0.9.7 character art, motion fixes, 46px footer, palettes and Atelier placement.
- Include separate AnkiWeb publication materials with numeric-folder compatibility and old-sideload conflict metadata. Prepared, not published; no install code assigned.

---

## Historical notes

# 0.9.7 — motion continuity and release readiness

- Preserve native playback frame/action timeout during hide/show/footer refresh.
- Export four consistent stages at 30fps; sharpen full artwork to 480px and keep
  96px native assets at the same noninvasive 46px display size.
- Seamless idle cycle, eased one-shot pet/water reactions, irregular live blinks.
- Preserve the same live canvas on plan redraw; display-paced, elapsed-time motion.
- Device-aware supersampling; no framebuffer clear for an unchanged size.
- Batch compatible meshes without reducing model triangles or changing materials.
- Erase an exam’s optionally retained written answers when deleting that exam.
- Reject late Focus/mistake-review opens after a competing review has started.
- Validate card-fitting dimensions and ignore stale measurements.
- Re-run complete automated suites from an extraction of the exact installer.
- Native Windows/Qt/hardware/template acceptance remains explicitly unverified.

---

# 0.9.6 — Living Pip and complete study/exam hardening

Local real-time 3D habitat; one leaf-skinned model family; consistent growth
milestones; animated/interactive same-model fallbacks; native 96px assets in the
existing 46px reviewer footer button. GPU/resource lifetime handling and explicit
reduced-motion/hidden-state support. Original image-only/plush designs no longer
appear in the interface. No reviewer sidebar.

Question navigator with flags and response preservation; separate native control
rows; result-modal stale-close race repair; isolated optional answer-file failure;
old-profile response-cache protection. Complete previous Study/Focus/Browse,
weighted exam, mistake review, bulk editing and Atelier features retained.

Current release status and test scope: TEST_REPORT.md. Native Windows/Anki testing
is still required; historical reports below are not current evidence.

---

# Changelog

## 0.9.4 — functional test build

- Reconstructed from the last preserved 0.9.3 source, rather than repackaging that version unchanged.
- Dedicated Study/Start here path selects the deck with Anki's CollectionOp then opens the scheduled reviewer. Filtered exam scopes and overlapping parent rows route to exact independent focus practice.
- Kept Browser viewing separate; removed obsolete `import aqt.dialogs` and empty `cid:0` mistake-review routing.
- Added retained card IDs/grades and read-only Review misses & unanswered with original responses and Reveal/Hide controls.
- Added bounded in-memory responses and opt-in local persistence in a separate file; old histories remain readable.
- Parent coverage is removed from duplicate sampling quotas. Named coverage reporting replaces repeated raw-ID warnings.
- Added a full-workspace planner/practice layout, shorter deck paths, collapsible priorities, side response panel, and whole-card zoom.
- Preserved bulk confidence/emphasis editing, themes, weighted sampling, and Atelier integration.
- Replaced the unsettling humanoid/acorn Pip artwork with a round mint plant creature: four stages, idle/pet/water 3D-rendered animations.
- Added a separately owned reviewer companion dock; hide/pause/reduced-motion options; read-only study-signal refresh.
- Diagnostics default to current-session errors; prior logs are opt-in and labeled.
- Added current regression tests and package checks. Native Windows/Anki testing remains outstanding.

## Earlier builds

0.9.3 added bulk values and a Browser compatibility repair but Study still opened the Browser. 0.9.2 corrected the conflicting Qt event handler and added Atelier mounting. Earlier images/reports in docs/legacy are historical, not evidence for this version.

## 0.9.5 — complete replacement, tiny reviewer companion

Removed the full-height native dock. Pip is now a 46px native control in verified
spare footer space; no reviewer/card resizing, no auto-opened controls, and no
mascot webview. Persistent reviewer-only hide. Optional practice answer pane
starts closed. Full study/exam/mistake-review functionality is bundled and tested
again. Experimental; Windows native integration is not certified.
