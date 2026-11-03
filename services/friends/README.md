# Atelier private Friends service — prepared, not deployed

This folder contains the invite-only service source for Atelier's Friends & shared folders window. No Supabase project, public endpoint, SMTP sender, member account or paid resource has been created. The installer ships without a service URL or key. Installing/opening Atelier does not sign up a user, contact this service or upload a deck.

The desktop window and local companion journey also work with Atelier's visuals off, through **Tools → Atelier → Friends & shared folders / Companion journey**. Offline deck export remains Anki's normal exporter. No Onigiri code or artwork is included here.

## What sharing does

A publisher attaches 1–20 native parent folders/decks to one shared course, chooses current friends, and publishes a native `.apkg` version. Parents include descendants; overlapping roots count once. Originals remain separate. Native export includes the chosen note/card content, note types and referenced media, without scheduling, deck options or review history. The selected-course media boundary is tested against unrelated files.

Automatic publishing is a separate, explicit checkbox. While that profile is signed in, native collection changes are debounced for 15 seconds and inspected when Anki returns to its deck browser. A content digest includes note fields/tags, note types, deck paths, card identities and referenced media size/mtime. Review/rating/scheduling changes alone do not publish. Media-only changes made outside Anki need **Publish now**; they may not raise a collection hook. Files changed externally while Anki is closed are detected after signing in again. A failure suspends that course until a manual retry or preference change; there is no retry storm. This is a publisher feed, not simultaneous collaborative editing or a two-way sync.

Friends see the latest version in Updates, explicitly download it, and review Anki's normal import/update choices. A native import does not automatically delete cards absent from the new snapshot, mirror moved/removed folders, or overwrite a recipient's local edits regardless of import options. Anki matches native note identities and uses its own note-type/update rules. Native modification timestamps have one-second precision; the automatic debounce exceeds that interval. A downloaded version is labelled **downloaded**, never automatically labelled imported.

## Local verification

Use the retained exact npm lockfile; do not create another browser/Python installation:

```powershell
npm ci --prefix services/friends --ignore-scripts
npm test --prefix services/friends
npm run check --prefix services/friends
```

Tests execute the migration in real PGlite PostgreSQL, including forced RLS and permissive-policy collision cases. Handler tests exercise real Web Streams and SHA-256 with controlled Auth/RPC/Storage responses. Desktop tests exercise the stdlib client; native Anki tests separately prove real export/import and native review activity. These do not certify managed Supabase configuration, deployed Deno behavior, production concurrency, SMTP delivery, backup restoration or live end-to-end sharing.

Read **HOSTING-REQUIREMENTS.md**, **SECURITY.md** and **OPERATIONS.md** before requesting hosting approval. `supabase/config.toml` contains an intentionally unconfigured project name. No deploy command has been run.
