# Exam Sprout 0.10.1 — architecture and write boundaries

## Assessment, distinct from the companion

`evidence.py` combines read-only SELECT snapshots of first native card/day reviews with bounded, validated local item outcomes. Current IDs/owners, per-note/day deduplication, exposure times, legacy weight and the safety cap are explicit. `readiness.py` is a pure, unvalidated heuristic with per-topic contributions, known/unknown evidence, published F−…S thresholds, coverage gates and an always-visible no-guarantee notice. It is not FSRS retrievability or a calibrated prediction of a real exam result.

`progress.py` separately owns profile-local lifetime effort. Normal reviews contribute through a guarded, read-only `reviewer_did_answer_card` listener. Independent self-marked sessions contribute when saved. Both use unique note/UTC-day keys; wrong answers count as effort, pet interactions do not. Old grade-derived percentages are not converted into effort. This listener does not intercept or replace Anki's grading.

## Sessions and scheduling

`core.py` retains pure plans and capped distinct-card/note sampling (now 1–500 questions and 0–720 minutes). `exam_engine.py` applies fixed representative quotas or bias-labelled targeted priorities, cold-only eligibility and interleaving. `exam_session.py` owns attempted/written/flagged state, locked pre-answer confidence, response timing, error categories, submission and restorable timing. It preserves original IDs/order; it never substitutes a question when resuming.

`runner.py` uses Anki's Previewer to render original card templates and media. The optional response pane starts closed. Native control rows separate question navigation, marking/confidence, timing/save controls and revealed-answer actions. Mistake review reads original cards and retained prose without creating another result. Normal-review-only template/add-on hooks may differ from Previewer hooks; native compatibility is not assumed.

There are three distinct scheduling paths:

1. **Normal Study:** select the deck through Anki's CollectionOp, then enter its scheduled reviewer. Normal ratings change normal scheduling.
2. **Independent exam / rehearsal / mistakes:** no scheduler-rating operation. Mocks cannot enable learning via a payload option. Existing learned cards in Pip Study are always rehearsal.
3. **Explicit new learning in Pip Study:** after reveal, native Again/Hard/Good/Easy controls call `new_learning.introduce_new` inside a serialized CollectionOp. It re-fetches the card and checks the original fingerprint, active NEW state (type/queue 0, reps 0, no filtered-deck original), current positive-weight exam scope/filter, API availability and explicit authorization. It calls Anki's `grade_now` backend once, without manually writing queues, intervals or revlog. Remaining learning steps belong to normal Anki. Busy, profile/collection/epoch, render-failure and stale-card guards reject unsafe requests. A failed native write cannot earn a local grade.

The third path is new and requires real Anki/FSRS and SM-2 verification before public release. API-contract doubles do not establish runtime scheduler semantics or undo behavior.

## Persistence and lifetime

`storage.py` validates bounded, atomic profile-local settings/exams/outcomes; `answers.py` separates optional last-ten completed-session prose. `drafts.py` holds one explicitly saved unfinished session, including prose, with strict validation and a distinct consent action. Timed mocks keep counting while closed and resume directly into grading if expired. Practice saves retain elapsed active time. No silent autosave of prose or collection sync is implied.

`integration.py` owns the bridge, menus, load/query operations, native windows, pending sample tokens and result handoff. State and callbacks capture the profile store, collection identity and epoch. Native reviewing invalidates stale previews. A main-window singleton prevents two 0.10.0 controllers from registering hooks. AnkiWeb's conflict metadata handles older sideloaded duplicates. User data is outside both sideloaded and numeric add-on folders.

## Unchanged visual system

The 0.9.7 Pip model/renderer and all matching artwork are retained byte-for-byte. `companion.py` still uses the 46-pixel native non-focus-taking footer button, verified free-space placement, no QDockWidget, no extra mascot webview and no card overlay. QMovie pauses/resumes instead of rewinding. `web/pip*.js` preserves the live WebGL2 scene, elapsed-time animation, supersampling and batched rigid meshes, and disposes resources when needed. No runtime CDN, image generator or AI service is required. The asset manifest binds pre-rendered frames to the live scene hash.

`web/app.*` adds readiness/method disclosures, independent effort, Pip Study options, larger mock settings, save/resume entry and richer result actions. The countdown and uploaded Atelier adapter keep their scoped slot/palette behavior. The add-on does not repackage or mutate Atelier.

## Verification boundary

Python exercises pure logic, SQLite read immutability and explicit Anki/Qt doubles. Chromium exercises real UI/geometry with a synthetic collection bridge, including the actual uploaded Atelier front end. The verifier runs these suites from a clean extraction of the exact local installer and separately checks the AnkiWeb upload variant differs only by manifest conflict metadata. No real Windows Anki scheduler, card-template ecosystem or AnkiWeb server acceptance is certified here.


## 0.10.1 native asset lifetime

Only the tiny Qt animation loader changed. A 4 MiB-capped context-managed read
closes before QMovie gets the bytes. QBuffer is parented to the movie and retained
by the badge; setData owns its QByteArray contents. Pausing preserves the device.
An action change/disposal stops and detaches the decoder before closing/clearing
the buffer. No QMovie filename remains, including fallback paths. No Anki updater
hook or storage/scheduling modification is required.
