# Atelier 1.0.0 — release decision and distribution

## Direct-install release decision

The project owner requested version 1 and reported that **visual and primary testing passed** on the accepted rc6 build. That report is the release's user-acceptance evidence. Individual native cases were not itemized, so it is not represented as an independently executed Windows compatibility matrix.

Version 1 freezes the accepted layout and functionality. Only the reviewed copy/version edits in `release-copy-changes.json` and release documentation are allowed. A successful current-runtime verifier, source/installer equality, preserved engine boundaries, and reproducible archives are required before delivery.

**Distribution identity:** `daedalus_atelier`. **Target:** Windows desktop Anki 26.08.1, standard editor. **Delivery:** direct `.ankiaddon` installation. No external publication is performed by these scripts.

## Recorded checks

Use `verification/verified.json`, `Atelier-1.0.0-Build.json`, and the SHA-256 file for actual execution totals and installer bytes. The source freeze tests reconstruct the precise rc6 text from reviewed substitutions; they are not a generic exclusion for changed files. The original engine tests still run.

The maintainer's automated tests use Linux Chromium, Python/SQLite, and explicit Anki/Qt doubles. They do not independently certify native Windows DPI, real Sync/Undo, Qt PDF codecs, image-occlusion extensions, Onigiri rewards, or live GPU Pip. The owner reported visual/primary testing, not an exhaustive matrix of all these cases.

## Before publishing a public AnkiWeb listing

This is distribution administration, not a missing feature-development slice:

1. Use an authorized publishing account and confirm the public support destination and asset/brand permissions. Keep the supplied MIT/BSD notices and distinguish screenshots with fictional records from real usage.
2. Obtain the numeric listing ID. Test installation in a spare profile, then the identity transition described in `MIGRATION.md` using a backup copy. Do not guess an ID or silently run two independent copies.
3. Verify source availability and the supplied user guide/privacy notes. Publish the final support address only after it exists. State the bounded Windows/Anki target instead of advertising universal compatibility.
4. Obtain explicit approval for the upload. The request to prepare version 1 did not itself perform any upload.

The included listing text is ready to adapt to the actual distribution page. No public ID, support address, hosted download, digital signature, or automatic update channel is invented by this release kit.
