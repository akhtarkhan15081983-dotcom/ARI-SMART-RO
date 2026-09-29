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
- [x] Latest code-bearing warehouse/purchase hardening CI #680 passed all required jobs at `bf85c38b357d2d9d68e88846a5416a012d856bb7`: Django deployment/migration checks, full backend suite, Flutter analyze/tests, Android debug APK compile/upload, production container, Windows release/safe-build/startup smoke/installer. Windows Authenticode steps were skipped because trusted signing credentials are not configured.
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
- [ ] Synced business actions use idempotency/acknowledgement — GPS, jobs/installation and rent-payment retry paths have idempotency foundations; remaining business actions still require audit.
- [ ] Corrupt local queue/state preserved for diagnostics rather than silently discarded where recoverable.

### Current verified facts
- Production settings require configured DB when DEBUG is disabled; SQLite is development-only.
- Production media requires explicit persistent filesystem or S3-style storage.
- Flutter crash/error telemetry exists and sanitizes sensitive tokens/password-like values.
- Offline jobs/photos/signatures have local queue/storage support.
- Live location cadence is 20 seconds.
- Durable mobile GPS queue uses append-only JSONL in app-support storage, retains up to 6000 valid points (about 33 hours at 20-second cadence), and drains a bounded 200-point batch per tracking tick.
- Backend delayed-location batch accepts up to 500 points, validates coordinate/time/shift boundaries, has a 72-hour backfill limit, persists route points idempotently and does not move current live marker backwards.
- Rent payment supports `X-ARI-Action-ID`; server receipt + ledger write are atomic and Flutter retries a transient lost-response case once with the same ID.
- Rent integrity regression coverage now includes partial payment consistency, overpayment rollback, failed action-ID reuse and rejection of a second payment that exceeds the remaining balance.
- `CustomerRentHistory` has a database uniqueness rule for `(customer, rent_month)`.
- Production Render Postgres currently reports status `available`, PostgreSQL 18, Singapore, 1 GB disk, `0.1c-256mb`, no HA and no read replica.
- Backup/PITR availability is not yet marked verified because the actual Recovery page / restore drill has not been proven.
- Recovery runbook: `docs/PRODUCTION_BACKUP_RECOVERY_RUNBOOK.md`.
- Max-Pro recovery targets: database RPO <= 15 minutes once PITR is verified; RTO <= 2 hours; daily off-Render logical backup; monthly restore drill.

## Explicit operational tenant ownership — implemented on hardening branch only
Nullable indexed `company` ownership exists in model/migration state for:

- `Customer`
- `Job`
- `Service`
- `Complaint`

This is an expand-only hardening-branch schema. **No production migration has been run.**

### Safe operational backfill tooling
`python manage.py backfill_tenant_ownership` is dry-run by default.

- no phone-number ownership inference;
- evidence is derived from explicit employee/company, linked operational records and unambiguous active memberships;
- `RESOLVED` rows are eligible for write only with explicit `--apply`;
- `UNRESOLVED` rows stay unchanged;
- conflicting company evidence is reported as `CONFLICT` and stays unchanged;
- optional JSON audit report is supported;
- tests cover resolved, unresolved, conflict, dry-run/no-write and apply-only-resolved behavior.

## Explicit purchase / warehouse tenant ownership — implemented on hardening branch only
Expand-only nullable indexed `company` ownership now exists for:

- `Supplier`
- `Purchase`
- `PurchaseItem`
- `InventoryItem`
- `EngineerBagItem`
- `InventoryAuditLog`
- `PartRequest`

Migrations:
- `purchase/0004_tenant_ownership_expand.py`
- `inventory/0009_tenant_ownership_expand.py`

**Neither migration has been run on production.**

### Safe warehouse backfill tooling
`python manage.py backfill_inventory_tenant_ownership` is dry-run by default.

- no phone-number ownership inference;
- ownership evidence flows from explicit purchase/supplier/verifier membership and warehouse/engineer relations;
- conflicting evidence propagates downstream rather than silently picking one tenant;
- `RESOLVED` rows are eligible for write only with `--apply`;
- unresolved/conflicting rows remain unchanged;
- optional JSON audit report is supported;
- tests cover clean purchase-chain resolution, unresolved suppliers, cross-company bag conflicts, dry-run/no-write and apply-only-resolved behavior.

### Purchase / warehouse runtime guards
- Supplier, Purchase and PurchaseItem APIs are workspace-scoped.
- Supplier/Purchase/PurchaseItem company ownership is server-controlled; clients cannot spoof company input.
- PurchaseItem direct mutation endpoint is read-only; nested items inherit Purchase company.
- Manual purchase creation locks the supplier row and checks duplicate invoice number inside the transaction.
- OCR invoice analysis matches suppliers and detects duplicate invoices only inside the active workspace.
- OCR invoice confirmation locks the same supplier row before duplicate check/create, serializing concurrent manual/OCR posting for that supplier.
- Purchase-created InventoryItems inherit Purchase company.
- Inventory receiving queue, serialized receive, photo receive, code generation, QR PDF, summary and Excel report routes are explicitly company-scoped.
- Serialized receiving supports legacy null/blank serial stock but never mutates another workspace's purchase item.
- Cross-workspace serial collisions fail closed without exposing the other tenant.
- Engineer bag issue, My Bag/Admin Bag, PartRequest create/inbox/review/fulfil require matching explicit company ownership.
- Bag, stock and inventory audit rows are dual-written with company ownership on secured workflows.
- Company-bound users do not see unresolved `company=NULL` warehouse records.

## Phase 2 — Core operational certification
- [ ] Attendance
- [ ] Employee Live Location / Route History — implementation/CI strong; field certification pending.
- [ ] Face & Device Security
- [ ] Customer Management — explicit nullable ownership + backfill tooling/dual-write implemented and CI-green; production-like migration rehearsal/cutover pending.
- [ ] My Jobs / Secure Field Work — assignment scope + explicit nullable Job ownership implemented; migration rehearsal pending.
- [ ] Service — shared-phone isolation, company write guards and explicit nullable ownership implemented; migration rehearsal pending.
- [ ] Complaint Management — assignment/workflow guards, GPS behavior preservation and explicit nullable ownership implemented; migration rehearsal pending.
- [ ] Rent Management — explicit Customer company preferred; cross-tenant direct-ID reads/writes fail closed; production migration rehearsal pending.
- [ ] Payment History / Ledger — tenant-scoped reads/direct-ID writes plus atomic retry idempotency and payment-integrity regression coverage implemented.
- [ ] Inventory Control — explicit nullable warehouse ownership, scoped receiving/QR/summary/reporting and conflict-aware backfill implemented; migration rehearsal/cutover pending.
- [ ] Engineer Bag / Part Request — explicit company ownership + company-scoped issue/list/review/fulfil implemented and CI-green.

## Tenant / RBAC hardening evidence
- Customer assignment cannot target an active employee in another company.
- Admin emergency Job OTP cannot be retrieved by guessed primary key when the job engineer belongs to another company.
- Service customer access no longer relies on shared phone number alone; durable `Customer.user` linkage is preferred and legacy claiming is deterministic.
- Service staff writes validate target workspace; engineers cannot rewrite service ownership/link fields through generic updates.
- Complaint assignment validates workspace; generic update cannot bypass customer/status/job/service workflow ownership rules.
- Rent management/payment/history use explicit ownership first and narrow same-workspace legacy fallback only when company is null.
- Supplier/Purchase lists and writes are scoped to active workspace; foreign supplier IDs are rejected.
- OCR purchase analysis cannot match another tenant's supplier.
- Warehouse summary/receiving/issue/My Bag paths are protected by explicit company ownership.
- Legacy pre-tenancy compatibility is intentionally narrow; there is no all-company fallback.
- CI #680 validates the complete code-bearing hardening state after operational + warehouse tenant changes.

## Remaining migration / schema P1
The hardening branch now contains explicit nullable ownership across the operational and warehouse roots, but production data has **not** been rehearsed, backfilled or cut over.

Before production schema action:
1. verify backup/PITR and produce an off-provider logical backup;
2. restore a production-like copy in isolation;
3. run both tenant backfill commands in dry-run mode;
4. resolve/quarantine every conflict and unresolved active record;
5. rehearse `--apply` and reconcile counts;
6. only then consider non-null constraints and tenant-local unique constraints.

A database unique constraint for supplier invoice identity is intentionally not added yet because existing production-like data has not been duplicate-rehearsed. Current manual/OCR write paths use a transaction plus supplier-row lock to prevent concurrent duplicate posting. A database constraint remains a post-rehearsal hardening target.

Inventory/purchase design: `docs/MAX_PRO_INVENTORY_TENANT_OWNERSHIP_PLAN.md`.  
Tenant migration design: `docs/MAX_PRO_TENANT_OWNERSHIP_MIGRATION_PLAN.md`.

## Additional data-integrity P1s
- Customer/Job/Service/Complaint human-readable ID generation still uses a "read last number then +1" pattern. Concurrent creates can race. Replace with a database-safe allocator/sequence and add concurrency tests.
- Inventory Excel `Stock Value` calculation needs explicit quantity-weighted verification; current unit-price aggregation may understate value when PurchaseItem quantity is greater than one.
- Final supplier-invoice database uniqueness should be added only after isolated duplicate audit/rehearsal confirms safe constraint creation.

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
- [ ] Security/RBAC regression passed after production-like migration rehearsal.
- [ ] Migration rehearsal passed on production-like data.
- [ ] Performance/memory checks passed.
- [x] Windows build/installer CI path verified; trusted Authenticode signing remains separately open.
- [ ] Release checksums recorded.
- [ ] Rollback procedure tested.
- [ ] Final UAT signed off.

## 5/5 definition
A feature existing in code is not enough. A module is 5/5 only when implemented, permission-safe, recoverable, observable, tested on supported platforms, resilient to expected network/device failures, data-safe, and free of P0/P1 defects.

## Next actions
1. Replace race-prone Customer/Job/Service/Complaint human-readable ID generation with a database-safe allocator and add concurrency tests.
2. Verify/fix quantity-weighted inventory stock valuation and add financial/reporting regression tests.
3. Add migration-rehearsal tooling for operational + warehouse tenant ownership, including duplicate supplier-invoice audit; do not touch production.
4. After isolated duplicate audit is clean, design tenant-local supplier invoice database uniqueness constraint.
5. Harden remaining offline job-store concurrent writers / atomic temp-file recovery and continue idempotency audit for other business writes.
6. Verify Render/PostgreSQL PITR and perform an isolated restore drill before any production migration approval.
7. Verify production media persistence/object storage.
8. Certify Attendance + Location on real Vivo S20/Vivo T3/Redmi 8A-class devices, including app-killed, reboot, long-offline and reconnect stress tests.
9. Continue 38-module certification work.
