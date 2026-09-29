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
- [ ] Add/verify CI gates: backend tests, Flutter tests/analyze, Android build, migration checks.
- [ ] Protect final release branch from direct unverified changes.
- [ ] Consolidate intentionally retained divergent Windows work before final RC.
- [ ] Produce a single Release Candidate commit and immutable release notes.

## Phase 1 — Crash, data and recovery safety
- [ ] PostgreSQL automated backups verified in production.
- [ ] Restore drill completed from a real backup into an isolated DB.
- [ ] Define/document RPO and RTO targets.
- [ ] Media storage verified persistent/object storage; no critical file on ephemeral disk.
- [ ] Backup/restore procedure tested before destructive migrations.
- [ ] Client/server crash telemetry verified end-to-end.
- [ ] Failed background/offline work survives app restart and network loss.
- [ ] Offline location history retained for at least 24 hours at normal cadence.
- [ ] Offline location queue drains safely after reconnect without starving current tracking.
- [ ] Synced business actions use idempotency/acknowledgement.
- [ ] Corrupt local queue/state preserved for diagnostics rather than silently discarded where recoverable.

### Current verified facts
- Production settings require configured DB when DEBUG is disabled; SQLite is development-only.
- Production media requires explicit persistent filesystem or S3-style storage.
- Flutter crash/error telemetry exists and sanitizes sensitive tokens/password-like values.
- Offline jobs/photos/signatures have local queue/storage support.
- Live location cadence is 20 seconds.
- **Known P1 blocker:** pending location queue capacity is 30 points (~10 minutes), below the 24-hour Max-Pro target.
- **Design note:** do not solve this by blindly putting thousands of GPS points into secure key-value storage; use a durable bounded local store plus controlled batch draining.

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
1. Replace the ~10-minute GPS backlog design with durable 24h+ local storage and bounded reconnect draining.
2. Verify Render/PostgreSQL backup and restore capability.
3. Verify CI coverage on the hardening baseline and add missing gates.
4. Certify core modules in order: Attendance → Location → Security → Customer → Jobs/Service/Complaint → Rent/Payments → Inventory.
