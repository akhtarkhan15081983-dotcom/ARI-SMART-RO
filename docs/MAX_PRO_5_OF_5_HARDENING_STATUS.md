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
- [x] Latest code-bearing integrity CI #734 / run `36527660460` passed all required jobs at `c4c40622063c28949f85004e85256bfb8b8678ce`: Django deployment/migration checks, full backend suite, Flutter analyze/tests, Android debug APK compile/upload, production container, Windows release/safe-build/startup smoke/installer. Windows Authenticode steps were skipped because trusted signing credentials are not configured.
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
- [ ] Failed background/offline work survives app restart and network loss on a real device.
- [ ] Offline location history retained for at least 24 hours at normal cadence — implementation and CI verification complete; real-device 24h/reboot/app-killed verification pending.
- [ ] Offline location queue drains safely after reconnect without starving current tracking — implementation and CI verification complete; device stress verification pending.
- [ ] Synced business actions use idempotency/acknowledgement — GPS, jobs/installation, rent payment and Part Request create retry paths have idempotency coverage; remaining business writes still require audit.
- [x] Corrupt offline job state is quarantined/reported instead of silently discarded where recoverable; valid `.tmp` crash state and last-known-good backup recovery are CI-covered.
- [x] Offline job-state read/modify/write is serialized inside one Dart process and across store/process instances using a per-root in-process mutation queue plus OS file lock; same-instance and two-store concurrency tests are CI-green.
- [x] Offline ACK removal test proves only the confirmed action ID is removed; unrelated pending actions remain queued.

### Current verified facts
- Production settings require configured DB when DEBUG is disabled; SQLite is development-only.
- Production media requires explicit persistent filesystem or S3-style storage.
- Flutter crash/error telemetry exists and sanitizes sensitive tokens/password-like values.
- Offline jobs/photos/signatures have local queue/storage support.
- Live location cadence is 20 seconds.
- Durable mobile GPS queue uses append-only JSONL in app-support storage, retains up to 6000 valid points (about 33 hours at 20-second cadence), and drains a bounded 200-point batch per tracking tick.
- Backend delayed-location batch accepts up to 500 points, validates coordinate/time/shift boundaries, has a 72-hour backfill limit, persists route points idempotently and does not move current live marker backwards.
- Rent payment supports `X-ARI-Action-ID`; server receipt + ledger write are atomic and Flutter retries a transient lost-response case once with the same ID.
- Part Request create now supports `X-ARI-Action-ID`; a lost-response retry replays the first successful response and does not create a second request row.
- Rent integrity regression coverage includes partial payment consistency, overpayment rollback, failed action-ID reuse and rejection of a second payment that exceeds the remaining balance.
- `CustomerRentHistory` has a database uniqueness rule for `(customer, rent_month)`.
- Production Render Postgres currently reports status `available`, PostgreSQL 18, Singapore, 1 GB disk, `0.1c-256mb`, no HA and no read replica.
- Backup/PITR availability is not yet marked verified because the actual Recovery page / restore drill has not been proven.
- Recovery runbook: `docs/PRODUCTION_BACKUP_RECOVERY_RUNBOOK.md`.
- Max-Pro recovery targets: database RPO <= 15 minutes once PITR is verified; RTO <= 2 hours; daily off-Render logical backup; monthly restore drill.

## Human-readable operational ID integrity — CI verified
Customer, Job, Service and Complaint visible IDs no longer rely on an unlocked "last row + 1" read.

- allocation occurs inside `transaction.atomic()`;
- PostgreSQL transaction advisory locks serialize each visible-ID namespace/year;
- the allocator scans the existing visible high-water mark under the lock, preserving imported/legacy IDs and avoiding reuse/collision;
- existing external formats remain unchanged: `CUS-YYYY-NNNNNN`, `ARI-YYYY-NNNNNN`, `JOB-YYYY-NNNNNN`, `SER-YYYY-NNNNNN`, `CMP-YYYY-NNNNNN`;
- CI #734 includes direct simultaneous-create regression tests for Customer, Job, Service and Complaint and verifies no duplicate visible IDs under concurrent creation;
- Customer high-water regression verifies allocation starts above an imported legacy identifier.

This implementation remains schema-free; no new production sequence table is required.

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
Expand-only nullable indexed `company` ownership exists for:

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

### Migration rehearsal tooling — code verified, real rehearsal pending
`python manage.py rehearse_tenant_migration` is read-only and performs no writes.

It combines operational and warehouse ownership plans and reports:
- before owned/unowned/total counts;
- projected post-backfill counts;
- resolved, unresolved and conflict counts;
- relation inconsistencies across operational and warehouse chains;
- optional JSON evidence output.

CI verifies the tooling path. **It has not yet been run against an isolated restored production-like database, so migration rehearsal is not marked complete.**

### Purchase duplicate audit — code verified, production-like audit pending
`python manage.py audit_duplicate_supplier_invoices` is a read-only duplicate audit.

- identity is scoped by tenant + supplier + normalized invoice number;
- normalization trims/case-normalizes/whitespace-normalizes without silently collapsing punctuation identity;
- duplicate groups report raw invoice values, row IDs and counts;
- optional JSON report is supported;
- no data is modified;
- future database uniqueness remains intentionally deferred until a production-like duplicate audit/rehearsal is clean.

### Purchase / warehouse runtime guards
- Supplier, Purchase and PurchaseItem APIs are workspace-scoped.
- Supplier/Purchase/PurchaseItem company ownership is server-controlled; clients cannot spoof company input.
- PurchaseItem direct mutation endpoint is read-only; nested items inherit Purchase company.
- Manual purchase creation locks the supplier row and checks duplicate invoice number inside the transaction.
- OCR invoice analysis matches suppliers and detects duplicate invoices only inside the active workspace.
- OCR invoice confirmation locks the same supplier row before duplicate check/create, serializing concurrent manual/OCR posting for that supplier.
- Purchase-created InventoryItems inherit Purchase company.
- Inventory receiving queue, serialized receive, photo receive, code generation, QR PDF, summary and Excel report routes are explicitly company-scoped.
- Cross-workspace serial collisions fail closed without exposing the other tenant.
- Engineer bag issue, My Bag/Admin Bag, PartRequest create/inbox/review/fulfil require matching explicit company ownership.
- Bag, stock and inventory audit rows are dual-written with company ownership on secured workflows.
- Company-bound users do not see unresolved `company=NULL` warehouse records.

## Inventory financial integrity — CI verified
Financial/reporting calculations are reconciled to physical `InventoryItem` units rather than summing PurchaseItem unit prices as if every purchase line represented one unit.

- purchase value = `PurchaseItem.quantity × purchase_price`;
- physical inventory counts come from actual serialized/unit InventoryItem rows;
- received units/value exclude only `PENDING_RECEIPT` stock;
- warehouse balance/value includes `IN_STOCK + RETURNED` physical units;
- `ISSUED`, `INSTALLED` and `SCRAP` units/value are reported separately;
- purchased-vs-physical unit gap is explicit rather than hidden;
- Excel Purchase lines include quantity-aware Line Total;
- regression tests verify a 5 × ₹125.50 purchase line = ₹627.50 and validate received/issued/installed/returned value transitions plus missing-unit variance.

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
- [ ] Inventory Control — explicit nullable warehouse ownership, scoped receiving/QR/summary/reporting, financial reconciliation and conflict-aware backfill implemented; migration rehearsal/cutover pending.
- [ ] Engineer Bag / Part Request — explicit company ownership + company-scoped issue/list/review/fulfil + create idempotency implemented and CI-green.

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
- CI #734 validates the latest complete code-bearing integrity state.

## Remaining migration / schema P1
The hardening branch contains explicit nullable ownership across operational and warehouse roots, but production data has **not** been rehearsed, backfilled or cut over.

Before production schema action:
1. verify backup/PITR and produce an off-provider logical backup;
2. restore a production-like copy in isolation;
3. run `rehearse_tenant_migration` and both backfill commands in dry-run mode;
4. run duplicate supplier-invoice audit;
5. resolve/quarantine every ownership conflict, unresolved active record and duplicate invoice identity;
6. rehearse `--apply` on the isolated copy and reconcile counts;
7. only then consider non-null ownership constraints and tenant-local unique constraints.

A database unique constraint for supplier invoice identity is intentionally not added yet because existing production-like data has not been duplicate-rehearsed. Current manual/OCR write paths use a transaction plus supplier-row lock to prevent concurrent duplicate posting. A database constraint remains a post-rehearsal hardening target.

Inventory/purchase design: `docs/MAX_PRO_INVENTORY_TENANT_OWNERSHIP_PLAN.md`.  
Tenant migration design: `docs/MAX_PRO_TENANT_OWNERSHIP_MIGRATION_PLAN.md`.

## Remaining P0/P1 blockers
No new CI-detected P0 defect is open at CI #734, but Max-Pro completion still has material P1/certification blockers:

- actual isolated restored production-like tenant migration + duplicate-invoice rehearsal;
- production PostgreSQL PITR/Recovery verification and a real isolated restore drill;
- production media persistence/object-storage verification;
- real-device Attendance/GPS 24h, app-killed, reboot, long-offline, reconnect and permission/battery stress certification on supported low-memory devices;
- client/server crash telemetry live-device end-to-end verification;
- continued idempotency audit for remaining business write endpoints beyond the currently protected paths;
- stronger Android integrity/root/emulator/fake-camera/liveness controls where compatible with older supported devices;
- trusted Windows Authenticode certificate/signature verification;
- all 38 modules mapped/certified, performance/memory checks, rollback rehearsal, checksums and final UAT.

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
- [ ] Offline→online sync stress test passed on device.
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
1. Run tenant ownership + duplicate supplier-invoice rehearsal on an isolated restored production-like database only; do not touch production.
2. Verify Render/PostgreSQL PITR and execute a real isolated restore drill before any production migration approval.
3. Verify production media persistence/object storage.
4. Continue business-write idempotency audit, prioritizing inventory receiving/issue/fulfil, complaint/service transitions, customer import/edit and other retryable mobile actions.
5. Certify Attendance + Location on real Vivo S20/Vivo T3/Redmi 8A-class devices, including app-killed, reboot, long-offline and reconnect stress tests.
6. Verify crash telemetry end-to-end on real devices and continue device integrity/root/emulator/fake-camera/liveness hardening with compatibility fallbacks.
7. Continue 38-module certification, performance/memory/rollback/checksum/final-UAT work.
