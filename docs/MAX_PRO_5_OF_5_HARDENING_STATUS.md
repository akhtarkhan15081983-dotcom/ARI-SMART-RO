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
- [ ] Latest hardening CI run passes all required jobs.
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
- [ ] Offline location history retained for at least 24 hours at normal cadence — implementation complete; CI/device verification pending.
- [ ] Offline location queue drains safely after reconnect without starving current tracking — implementation complete; CI/device verification pending.
- [ ] Synced business actions use idempotency/acknowledgement — location path implemented; remaining business actions still require audit.
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
- Production Render Postgres currently reports status `available`, PostgreSQL 18, Singapore, 1 GB disk, `0.1c-256mb`, no HA and no read replica.
- Backup/PITR availability is not yet marked verified because the actual Recovery page / restore drill has not been proven.
- Recovery runbook: `docs/PRODUCTION_BACKUP_RECOVERY_RUNBOOK.md`.
- Max-Pro recovery targets: database RPO <= 15 minutes once PITR is verified; RTO <= 2 hours; daily off-Render logical backup; monthly restore drill.

## Phase 2 — Core operational certification
- [ ] Attendance
- [ ] Employee Live Location / Route History
- [ ] Face & Device Security
- [ ] Customer Management
- [ ] My Jobs / Secure Field Work
- [ ] Service
- [ ] Complaint Management
- [ ] Rent Management
- [ ] Payment History / Ledger
- [ ] Inventory Control
- [ ] Engineer Bag / Part Request

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
- [ ] Security/RBAC regression passed.
- [ ] Migration rehearsal passed on production-like data.
- [ ] Performance/memory checks passed.
- [ ] Windows build/installer verified if included.
- [ ] Release checksums recorded.
- [ ] Rollback procedure tested.
- [ ] Final UAT signed off.

## 5/5 definition
A feature existing in code is not enough. A module is 5/5 only when implemented, permission-safe, recoverable, observable, tested on supported platforms, resilient to expected network/device failures, data-safe, and free of P0/P1 defects.

## Next actions
1. Obtain a clean all-jobs CI result for the durable GPS implementation and patch any failure.
2. Verify Render/PostgreSQL PITR on the actual production Recovery page and perform an isolated restore drill.
3. Verify production media persistence/object storage.
4. Certify Attendance + Location together, including app-killed, reboot, long-offline and reconnect stress tests.
5. Continue core certification: Security → Customer → Jobs/Service/Complaint → Rent/Payments → Inventory.
