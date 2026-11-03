# Hosting requirements and owner approval gate

Prepared November 2, 2026. Classification: D (database application), E (accounts), F (personal information), J (isolated service preparation). Existing local Anki/optional-AI behavior remains separate. This is not a production deployment or legal certification.

## Concrete proposed private pilot

Use a **dedicated, owner-controlled Supabase project**, managed Auth/PostgreSQL/private Storage, and the included `atelier-friends` Edge Function. Choose and approve the exact project, region, provider account, support contact, privacy/retention terms, SMTP provider/domain and acceptable recurring cost **before** creation/deployment. No destination or purchase is assumed. Do not place this schema in a client project or a bucket used by another application.

Start with at most 100 explicitly allowlisted members. Disable public signup in Auth; an administrator creates/invites an approved Auth user and separately inserts that verified user UUID into `atelier_members`. No client can add membership. Use production SMTP with OTP email content and test delivery/rate limits. A friendship invitation does not create an Auth account or bypass the member allowlist. Sign-in requests use `create_user:false`. The desktop never requests an AnkiWeb password.

Only the HTTPS project origin and **public** publishable/anon key go into the desktop's optional configuration. `SUPABASE_SERVICE_ROLE_KEY` stays in managed server secrets. It must not appear in an installer, webview, Git history, log or public configuration. Use Supabase-provided server credentials compatible with Auth/PostgREST/Storage; verify key rotation on staging. The adapter authenticates every bearer with Auth `/user`, then calls user-scoped SQL RPCs. `verify_jwt=false` is intentional because application validation is mandatory and supports managed signing keys; removing that validation is a security failure, not a configuration shortcut.

Apply the reviewed migration; verify FORCE RLS and grants in the deployed project. The `atelier-friends` bucket must actually be **private**, limited to 40 MiB and permitted MIME types, with no public URL or bypass policy. The restrictive exclusions must defeat broader anonymous/authenticated policies. Service credentials are trusted administrator credentials and must remain server-only. Publish the exact public URL/key to desktop users only after all live gates pass and the owner approves enabling the service.

## Hard pilot bounds

- 40 MiB maximum package; 50,000 cards and 64 MiB of local source/media per course.
- 20 friends/member, 25 active courses/member, 100 course-history records/member.
- 200 reserved snapshots/member; 10,000 snapshots globally. The latest two ready versions are retained after cleanup.
- 128 MiB reserved storage/publisher and 500 MiB globally, including pending/revoked objects until deletion is confirmed.
- 2 GiB upload reservations and 2 GiB download reservations per UTC month, globally. Failed/aborted authorized transfers can consume reservation budget; reservations are conservative, not provider billing measurements.
- 100 RPC requests/minute/member; 10 friend invitation codes/day/member; one use, seven-day expiry. Provider Auth/edge and infrastructure abuse limits must also be configured and tested.
- Stream uploads/downloads with fixed byte/hash bounds and 120-second transfer signals. An upload ticket is one attempt; a failed attempt must be cancelled and republished with a fresh object identity. A ten-minute lease protects late operations from premature cleanup.

These are intentionally small private-pilot limits, not an unlimited school-wide service. Public rollout, larger media, resumable transfers, mobile clients, cross-device authentication persistence, paid plans and higher quotas need separate capacity/security/cost approval. No payments, subscriptions, public directories, chat, contact uploads or automatic emails to friends are implemented.

## Platform assumptions to recheck at deployment

Official docs were reviewed for private Storage/RLS, passwordless Auth and Edge resource limits. A plan's included quota is not a hard cost ceiling. Current Free limits cited by the provider include 1 GB storage, 5 GB egress and 50 MB maximum file size; Edge resources and quotas can change. Recheck current pricing, function CPU/memory/wall-clock limits, project pausing, backup availability, email limits, billing alerts/spend controls and DPA/region choices. The proposed reservations leave some headroom but do not bound every provider request/log/database/SMTP expense or sustained pre-auth abuse.

- https://supabase.com/pricing
- https://supabase.com/docs/guides/platform/billing-on-supabase
- https://supabase.com/docs/guides/functions/limits
- https://supabase.com/docs/guides/storage/uploads/file-limits
- https://supabase.com/docs/guides/storage/security/access-control
- https://supabase.com/docs/guides/auth/auth-email-passwordless
- https://supabase.com/docs/guides/auth/general-configuration

## Required live evidence before activation

1. Owner approves the exact destination, region, account and budget; professional/privacy/IP questions are resolved for the intended users. Approved operator and incident contact are named.
2. Deploy to an isolated staging project with synthetic users/packages. Confirm the actual Deno adapter, public/private key split, signup-disabled behavior, member allowlist, email OTP and operator credential recovery.
3. Real two-account export → upload → authorized list → verified download → explicit native import → edited/additional-card update passes. Test forged account/course/version, stale invitation, removed recipient, disabled publisher, revoked share, arbitrary direct PostgREST/Storage access, redirects, corruption, interruption and profile switching.
4. Run concurrent upload/cancel/revoke, stale lease and cleanup races against managed PostgreSQL/Storage. PGlite tests are not production concurrency proof. Validate large-package latency/memory/CPU, quotas, Auth/edge abuse limits and operator budget alerts.
5. Inventory every policy/grant/bucket on that project. Confirm no package has a public URL and no endpoint exposes service credentials. Review deployment against SECURITY.md.
6. Restore an encrypted database **and private-object** backup into isolation and read/hash a shared version. Check that restored manifests/authorization match the objects. Verify cleanup/retention and account deletion; retain recovery evidence and reclaim the restored payload.
7. Test a safe rollback/disable and support/incident response. Publish reviewed privacy/retention/IP guidance, not an unconfigured placeholder policy.
8. Owner reviews the exact deployed endpoint and installer/configuration hash and explicitly approves activation/distribution. This source preparation is not that approval.
