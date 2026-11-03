# Operator runbook — preparation only

Do not run these operations against an unapproved destination. There is no production project to maintain yet. The exact project/region, operator, budget, secrets, SMTP and activation require owner approval.

## Configuration and membership

Deploy the single migration and function to the approved dedicated staging project. Store server keys only in server secrets. Check actual table grants/FORCE RLS and private bucket/policies after every deployment. Disable public Auth signup. An operator independently verifies each member, invites/creates the Auth account and inserts that real UUID with a display name/active status into `atelier_members`. Limit the pilot to 100 members. Do not copy a service-role key into the desktop. Native users need only the approved public project origin/key, distributed after activation approval.

## Cleanup and retention

Run the service-only `atelier_cleanup_candidates` from a protected scheduled operator job at least hourly. It atomically marks up to ten eligible snapshots revoked and returns their object paths: revoked/expired pending snapshots after their active leases end, plus ready versions older than the latest two. Delete each exact private object, accepting a confirmed not-found as already removed; only after success call `atelier_confirm_cleanup(snapshot UUID)`. Repeat in bounded batches with a strict job budget. Never manually zero `reserved_bytes`, delete live metadata or release quota just because a Storage DELETE failed. The Edge adapter also attempts bounded cleanup after publish/cancel/revoke, but this does not replace a tested schedule.

Client activity prunes that member's old rate rows and expired invitation history; scheduled hygiene should also prune stale non-object records under an operator-reviewed migration. Retain at most 100 course-history records/member and the latest two ready snapshots unless revocation/retention policy requires deletion. An interrupted/cancelled active upload remains reserved until its lease ends. Investigate orphan private objects by comparing Storage against the snapshot ledger, with an age/lease grace period, an exact deletion manifest and approval. A provider termination during an upload or object-delete confirmation can leave an orphan; no automatic claim of zero orphan storage is made.

## Backups and recovery

Before activation, choose an encrypted owner-controlled backup destination and retention. Snapshot database authorization/ledger and private objects as a matched manifest with SHA-256, sizes and snapshot IDs. Provider database backup alone does not prove private Storage recovery. Restore into an isolated project with signup/email disabled, read back and hash a version, verify recipient denial, preserve the small receipt, and reclaim the successful restore payload. Protect member email and deck content in all backups. Define a recovery-time/point objective and demonstrate it before making availability promises.

## Monitoring, failure and rollback

Monitor error/rate spikes, unexpected membership, object/ledger differences, reservation saturation, function CPU/latency and monthly provider/SMTP usage. Do not log bearer tokens, OTPs, card text, package contents or invite codes. Record bounded request IDs/status/timing. Configure owner alerts and a tested provider spend/abuse response; database reservations do not control all billable dimensions.

If compromised or misconfigured: disable service invocation/new memberships, preserve necessary logs safely, revoke/rotate affected server credentials through the approved owner/operator, disable affected members/courses, assess exposed material and obtain incident/privacy advice. Do not delete the only recovery copy. Client offline export and local study remain usable with no endpoint. Reverting the desktop URL to empty disables that client configuration; it does not erase hosted data or invalidate every issued server token. Roll back function code against the exact migration contract; do not drop tables/buckets as a rollback shortcut.

For member deletion, first verify the requester/operator authority. Revoke their courses, wait for active leases, perform confirmed private-object deletion, handle recipient access and membership/Auth records, and apply the approved backup/legal retention policy. Existing downloaded copies remain with recipients. This is a future operator procedure, not a deletion performed by this task.
