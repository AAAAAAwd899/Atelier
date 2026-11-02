# Atelier release retention and recovery

Keep the current 1.0.12 installer/source and tested 1.0.11 rollback locally. The untouched 1.0.2 implementation kit remains a required baseline. No third editable checkout is needed.

Older installer, source and publication containers have project-local recovery manifests in `verification/retention-112`. Each eligible archive was rebuilt independently from retained Git blobs, immutable small metadata deltas and named evidence leaves. The rebuilt ZIP SHA-256 had to equal the original exactly before eligibility. The manifests retain original member hashes and ZIP metadata. Audit is non-destructive; retirement additionally requires current and rollback build/installer/source checksums to pass.

`tools/release_retention_112.py --restore Atelier-1.0.10.ankiaddon` restores a selected historical archive into the single bounded `output/retention-112` area and verifies its exact SHA and ZIP CRC. It does not install or open Anki. Keep the Git objects/history, the recovery manifests and `.recovery/metadata` together. Referenced historical evidence leaves are part of this recovery chain, not additional editable project versions. Do not prune Git objects or remove those leaves independently.

The current evidence package includes compact recovery manifests and metadata deltas. The original artwork, personal/school files, owner profiles, credentials and account settings are outside the retirement scope. The older unique 1.0.3 visual comparison container is a read-only acceptance fixture, not an executable project snapshot; its 534 frames did not have identical current copies, so it was not treated as a verified duplicate.

Logical retired bytes and measured free space before/after are separately recorded in `verification/retention-112/removal.json`. Concurrent writes and filesystem allocation can make those measures differ. A successful temporary restore is removed after its durable manifest and results are saved.
