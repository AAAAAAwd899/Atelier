# Privacy, persistence and scheduling boundaries

Exam Sprout runs locally. No account, telemetry, cloud inference, API key, remote model, third-party CDN or remote Pip renderer is used. Clicking the author link deliberately opens the author's website. Original Anki card templates may themselves contain external links/resources; the add-on does not rewrite or sandbox all user templates.

Within the current Anki profile's `exam_sprout` folder:

- `state.json` and its validated backup: plans, settings, and at most 50 result summaries with original card/note IDs, self-marks, confidence, flags, error categories, timing and sampling metadata. No card template contents or written responses are added here.
- `pip_progress.json`: lifetime effort total and the current UTC day's note IDs for deduplication.
- Written responses: in memory by default, bounded to recent sessions. Optional `practice_answers.json` retains at most ten completed sessions locally, subject to a size limit. Turning off that setting deletes this optional response file.
- **Explicit Save & close is separate consent:** `active_exam.json` stores one unfinished session, its exact sampled IDs/order, flags, confidence, original written responses and timer. It stays until completion or explicit discard. Turning off completed-answer retention does NOT silently delete an explicitly saved unfinished exam. The UI explains this before saving. Timed mocks continue counting while closed; quick-practice timers preserve active elapsed time instead.
- Diagnostic logs contain local technical events. Review diagnostic text before sharing. Current-session logs are separated from older events.

Local plan/Pip/draft files do not sync through AnkiWeb. Normal Anki changes can sync using Anki's own sync. Profiles remain separate. The add-on's install folder contains only code/assets, so replacing a sideloaded or numeric AnkiWeb folder does not replace plan storage.

## Which actions change Anki?

1. **Normal Study:** opens Anki's scheduled reviewer. User grading has its ordinary scheduling effects.
2. **Pip Study, currently NEW card, Introduce new cards enabled:** after reveal, explicit Again/Hard/Good/Easy invokes Anki's Grade Now backend inside CollectionOp. The card is refetched and checked for unchanged identity/status, active unfiltered NEW state, zero repetitions, positive scope, and optional exam query. No scheduling SQL, manual intervals, queue assignments or synthetic review logs are used. A missing API or failed check shows an error and does not advance the session. This can introduce a card beyond the day's normal new-card quota; it does not edit deck limits. Remaining learning steps happen in normal Anki review.
3. **Pip Study on learned/learning cards, independent Focus, mocks, mistake review and pet interactions:** no scheduler rating is submitted. Marks are local self-assessment only.

A reopened/changed/deleted/moved card is not silently treated as the original writable NEW card. Repeated clicks cannot queue duplicate learning ratings. Real native scheduler semantics and undo behavior still require the documented acceptance test on supported Anki versions.

Deleting an exam removes its summaries, cached responses, linked optional saved answers and a readable unfinished draft for that exam. File deletion failures are reported; unreadable drafts are preserved for explicit discard. Backups remain local until the user removes them. Anki's own media and collection are never deleted by deleting an exam.
