# ARI SMART RO — Max-Pro 5/5 Hardening Status

**Hardening branch:** `hardening/max-pro-5of5-2026-09-29`  
**Live-production baseline:** `hotfix/admin-otp-testing-toggle-2026-09-27` @ `9066929c8297181dc1fce20943f67e4ef09fed88`  
**Prepared production ancestor:** `deploy/v1.0.48-production` @ `10f475e78610d90c1d6454c7b66f906ff8d044b6`  
**Started:** 2026-09-29

## Non-negotiable release rule
ARI SMART RO must not be declared 5/5 Max-Pro until every P0/P1 item below is verified with test evidence. `main` and live production branches are not active development branches.

## Phase 0 — Release safety
- [x] Identify the actually deployed Render branch.
- [x] Confirm live Render production is one commit newer than `deploy/v1.0.48-production`.
- [x] Rebase hardening baseline to the live production commit.
- [x] Create isolated hardening branch.
- [x] Enable CI gates on `hardening/**`: backend checks/tests, Flutter analyze/tests, Android debug compile, container build and Windows build/installer.
- [x] Code-bearing hardening CI #624 passed all required jobs at `ee11b4e27596865509f09fcccd17f4e57c95ef8c`: backend, Flutter analyze/tests, Android debug APK compile/upload, production container, Windows release/safe-build/startup smoke/installer. Windows Authenticode steps were skipped because trusted signing credentials are not configured.
- [ ] Protect final release branch from direct unverified changes.
- [ ] Consolidate intentionally retained divergent Windows work before final RC.
- [ ] Produce a single Release Candidate commit and immutable release notes.

## Phase 1 — Crash, data and recovery safety
- [ ] PostgreSQL automated backups/PITR verified on the actual production Recovery page.
- [ ] Restore drill completed from a real backup into an isolated DB.
- [x] Define/document Max-Pro RPO/RTO targets.
- [ ] Media storage verified persistent/object storage; no critical file on ephemeral disk.
- [ ] Backup/restore procedure tested before destructive migrations.
- [ ] Client/server crash telemetry verified end-to-end.
- [ ] Failed background/offline work survives app restart and network loss on device.
- [ ] Offline location history retained for at least 24 hours at normal cadence — implementation and CI verification complete; real-device 24h/reboot/app-killed verification pending.
- [ ] Offline location queue drains safely after reconnect without starving current tracking — implementation and CI verification complete; device stress verification pending.
- [ ] Synced business actions use idempotency/acknowledgement — GPS, jobs/installation and rent-payment retry paths now have idempotency foundations; remaining business actions still require audit.
- [ ] Corrupt local queue/state preserved for diagnostics rather than silently discarded where recoverable.

### Current verified facts
- Production settings require configured DB when DEBUG is disabled; SQLite is development-only.
- Production media requires explicit persistent filesystem or S3-style storage.
- Flutter crash/error telemetry exists and sanitizes sensitive tokens/password-like values.
- Offline jobs/photos/signatures have local queue/storage support.
- Live location cadence is 20 seconds.
- Durable mobile GPS queue now uses append-only JSONL in app-support storage instead of putting thousands of points in secure key-value storage.
- Queue retains up to 6000 valid points, approximately 33 hours at the normal 20-second cadence; compaction is periodic rather than performed on every GPS append.
- Reconnect draining uploads a bounded 200-point batch per tracking tick so backlog replay cannot starve current-position capture.
- New backend batch endpoint accepts up to 500 delayed points per request, validates coordinate/time/shift boundaries, and stores route-history points idempotently without moving the current live marker backwards.
- Backend batch backfill window is bounded to 72 hours.
- Regression tests cover delayed-point persistence, duplicate retry idempotency and rejection outside the attendance window.
- Legacy 30-point secure-storage backlog is migrated into the durable queue.
- Rent payment POST now supports `X-ARI-Action-ID`; the server atomically claims/completes a receipt with the payment and replays a completed response on retry instead of inserting a second ledger transaction.
- Flutter rent payment sends a stable action ID and performs one transient timeout/client retry with the same ID, covering the response-lost-after-commit scenario.
- Production Render Postgres currently reports status `available`, PostgreSQL 18, Singapore, 1 GB disk, `0.1c-256mb`, no HA and no read replica.
- Backup/PITR availability is not yet marked verified because the actual Recovery page / restore drill has not been proven.
- Recovery runbook: `docs/PRODUCTION_BACKUP_RECOVERY_RUNBOOK.md`.
- Max-Pro recovery targets: database RPO <= 15 minutes once PITR is verified; RTO <= 2 hours; daily off-Render logical backup; monthly restore drill.

## Phase 2 — Core operational certification
- [ ] Attendance
- [ ] Employee Live Location / Route History — implementation/CI strong; field certification pending.
- [ ] Face & Device Security
- [ ] Customer Management — cross-company assignment guards added; explicit tenant ownership migration still pending.
- [ ] My Jobs / Secure Field Work — engineer mutation paths assignment-scoped; admin emergency OTP tenant-scoped.
- [ ] Service — customer shared-phone isolation and engineer/company write guards added; explicit tenant ownership migration still pending.
- [ ] Complaint Management — assigned-engineer visibility, shared-phone isolation, cross-company assignment and generic workflow-bypass guards added; explicit tenant ownership migration still pending.
- [ ] Rent Management — company-bound staff list is fail-closed to customers assigned inside the active workspace until `Customer.company` exists.
- [ ] Payment History / Ledger — tenant-scoped reads/direct-ID writes plus atomic rent-payment retry idempotency implemented and CI-covered.
- [ ] Inventory Control — engineer issue/bag/part-request workflows tenant-scoped; stock/purchase/report tenant ownership remains a structural P1.
- [ ] Engineer Bag / Part Request — company-scoped issue/list/review/fulfil guards implemented and CI-covered by the full backend suite.

## Tenant / RBAC hardening evidence
- Customer assignment cannot target an active employee in another company.
- Admin emergency Job OTP cannot be retrieved by guessed primary key when the job engineer belongs to another company.
- Service customer access no longer uses phone number alone when duplicate/shared phone records exist; durable `Customer.user` linkage is preferred and legacy claiming is deterministic.
- Service staff writes validate the target engineer workspace; engineers cannot rewrite service ownership/link fields through generic updates.
- Complaint assignment validates the engineer workspace; generic complaint updates cannot bypass customer/status/job/service workflow ownership protections.
- Rent management hides other-company customers using an interim fail-closed assigned-engineer scope.
- Rent payment write/history endpoints apply tenant scope before customer-ID filtering.
- Inventory engineer-bag issue/list and part-request inbox/review/fulfil endpoints are workspace-scoped.
- Legacy pre-tenancy compatibility is intentionally narrow: tenant-less actors may only target tenant-less records; there is no all-company fallback.
- Regression coverage includes cross-tenant customer assignment, complaint assignment/update bypass, admin job OTP, rent visibility/direct-ID payment isolation, shared-phone complaint isolation and rent-payment replay idempotency.

## Structural P1 — explicit tenant ownership
`Customer`, `Job`, `Service` and `Complaint` do not yet have a consistent direct `company` ownership key. `Purchase`, `PurchaseItem`/purchase-root stock and `InventoryItem` also lack direct tenant ownership. Interim assignment-derived guards reduce exposure but cannot safely classify unassigned customers or warehouse stock.

Safe migration design: `docs/MAX_PRO_TENANT_OWNERSHIP_MIGRATION_PLAN.md`.

The plan is expand-only first: nullable indexed company keys, dry-run evidence backfill, conflict quarantine, dual writes and tenant-scoped reads, then constraints only after restore rehearsal and reconciliation. No production schema migration has been run.

## Phase 3 — Corporate modules
- [ ] Employee HRMS
- [ ] Training/certification
- [ ] Work Calendar
- [ ] Calling Desk
- [ ] Notifications & Offers
- [ ] Business Reports
- [ ] SaaS Command Center
- [ ] Shop/customer commerce
- [ ] Digital RO Passport / My RO
- [ ] Remaining blueprint modules

## Phase 4 — Final certification
- [ ] All 38 blueprint modules mapped to tests.
- [ ] Zero open P0 blockers.
- [ ] Zero open P1 blockers.
- [ ] Android device matrix passed, including low-memory ARI devices.
- [ ] App-killed/reboot/background-location/permission-change tests passed.
- [ ] Offline→online sync stress test passed.
- [ ] Database backup + restore drill passed.
- [ ] Security/RBAC regression passed on a migration-ready explicit-tenant schema.
- [ ] Migration rehearsal passed on production-like data.
- [ ] Performance/memory checks passed.
- [x] Windows build/installer CI path verified; trusted Authenticode signing remains separately open.
- [ ] Release checksums recorded.
- [ ] Rollback procedure tested.
- [ ] Final UAT signed off.

## 5/5 definition
A feature existing in code is not enough. A module is 5/5 only when implemented, permission-safe, recoverable, observable, tested on supported platforms, resilient to expected network/device failures, data-safe, and free of P0/P1 defects.

## Next actions
1. Rehearse the explicit tenant-ownership migration on an isolated restored copy before any production schema change.
2. Extend tenant ownership to purchasing/warehouse stock roots, then scope inventory receiving/QR/summary/Excel reporting without inference.
3. Verify Render/PostgreSQL PITR on the actual production Recovery page and perform an isolated restore drill.
4. Verify production media persistence/object storage.
5. Certify Attendance + Location on real devices, including app-killed, reboot, long-offline and reconnect stress tests.
6. Harden corrupt offline job-state recovery/quarantine and continue idempotency audit for remaining offline business actions.
7. Continue core certification through Customer → Jobs/Service/Complaint → Rent/Payments → Inventory after the tenant migration rehearsal.
