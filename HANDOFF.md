# Atelier 1.0.0 — frozen release handoff

Use this source kit, not any earlier divergent 0.8/0.9 shell. The input was the delivered 0.9.0-rc6 installer and matching source; every input byte matched before edits. The owner accepted visual and primary testing and requested a consumer-facing version 1 release.

The accepted design, navigation, independent Widgets route, visual-owner boundaries, figure caching, exports, progress, Pip groups, source approval, and practice behavior are frozen. Do not turn this finish into a new redesign. Embedded Sprout/Workshop version strings still identify their original upstream components; do not relabel them or overwrite their retained provenance documentation.

All code/version copy changes are in `release-copy-changes.json`. `tests/data/release-rc6-copy-baseline.json` and `release_copy.py` verify exact forward replay. Anything outside that list must fail the freeze tests. Runtime data schemas, provider consent, algorithms, CSS, icons, scenery, masks, defaults, and storage locations remain unchanged.

The integrated authoring/assessment frontend namespace must be tested in separate Python processes. Both historical harnesses import a test package called `addon`; combining them in one process causes a test-fixture namespace collision, not a production controller collision. The cumulative verifier already separates them.

Run `verify_release.py`, current render scripts, and `package_release.py`. Never reuse an old runtime fingerprint or screenshot proof. Generated proof totals count executed checks, not distinct native integrations. Exact-installer reruns are repeat checks and must not inflate totals.

Read `RELEASE-ACCEPTANCE.json`, `AUDIT-REPORT.md`, `RELEASE-GATES.md`, `MIGRATION.md`, and `src/USER-GUIDE.md`. The public listing is not uploaded. No code/asset fonts or private profile files belong in output archives. User-reported native acceptance and unperformed independent native QA must remain separate in release descriptions.
