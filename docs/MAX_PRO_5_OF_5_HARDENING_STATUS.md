# ARI SMART RO — Max-Pro 5/5 Hardening Status

**Hardening branch:** `hardening/max-pro-5of5-2026-09-29`  
**Live-production baseline:** `hotfix/admin-otp-testing-toggle-2026-09-27` @ `9066929c8297181dc1fce20943f67e4ef09fed88`  
**Prepared production ancestor:** `deploy/v1.0.48-production` @ `10f475e78610d90c1d6454c7b66f906ff8d044b6`  
**Started:** 2026-09-29

## Non-negotiable release rule
ARI SMART RO must not be declared 5/5 Max-Pro until every P0/P1 and certification gate is verified with evidence. Code existence or a green CI run alone is not sufficient for overall 5/5. `main` and live production are not active hardening branches.

## Latest exact code-bearing verification

**Verified code SHA:** `3c7338c464555be778a32c05fb1d9451d98dfd45`
**CI:** #763
**Run ID:** `36550641895`

CI #763 passed all required exact-head code-bearing gates:

- Django deployment/migration checks: PASS
- full PostgreSQL-backed backend regression: PASS
- Flutter analyze: PASS
- Flutter tests: PASS
- Android debug APK compile: PASS
- shareable APK preparation/upload: PASS
- production container build: PASS
- Windows release build: PASS
- Windows safe-build verification: PASS
- Windows startup smoke: PASS
- Setup.exe build/upload: PASS
- Windows Authenticode install/sign/verify steps: SKIPPED because trusted signing credentials are not configured

This verification includes the database-safe visible-ID concurrency/rollback gates, Inventory financial reconciliation gates, supplier-invoice concurrency protection, and the machine-verifiable duplicate-invoice rehearsal command/tests described below.

**No production deployment, Render branch change, production database migration, production data mutation, `main` merge or release was performed during this cycle.**

## 2026-09-29 continuation

- CI #753 / `5ab3f6e` remains the last verified **code-bearing** baseline.
- The subsequent `19f1f764` commit updated this status document only.
- The Render connector listed one workspace (`My Workspace`) but required explicit
  workspace selection before database inspection. No instance metadata, PITR
  availability, backup or restored copy has yet been verified in this session.
- The isolated restore, off-provider export, command and evidence procedure is
  prepared in `docs/MAX_PRO_ISOLATED_RESTORE_REHEARSAL.md`. Its commands have
  **not** been executed against a production-like restored database.
- Offline queue audit found that the backup stored the preceding state, so a
  corrupt primary could discard the latest committed pending action. Commit
  `7599b378cb1507638058160b0a72ddd8d2bb06a2` preserves the committed
  queue in the backup and tests corruption/restart recovery. Exact-head CI
  #755 (run `36535545551`) passed backend deployment/migrations and tests,
  Flutter analyze/tests and Android compile/upload, production container,
  Windows release/safe-build/startup/installer. Trusted signing remains open.
- Inventory receiving audit found that a lost response followed by the same
  QR/photo request could consume another pending physical unit. The locked
  purchase-item/action-receipt fix and two-unit regression are on
  `3a1c2a86a4bff83024ab7346ae7cab76ac5739e7`. Exact-head CI #756
  (run `36536379435`) **FAILED** backend tests because the new test fixture
  assigned NULL to the non-null inventory barcode column (2 errors). Flutter,
  Android/upload, production container and Windows jobs passed in that run.
  The fixture correction requires a new full exact-head CI; receiving remains
  unverified until that run passes.
- CI #757 (run `36537369655`) also failed backend tests: both new retry tests
  reached replay but the shared receipt response still reported
  `idempotent_replay=false`. Commit `6961bf8f` corrected the shared replay
  response. Exact-head CI #758 (run `36538291546`) passed backend deployment
  checks and full tests, Flutter analyze/tests and Android compile/upload,
  production container, and Windows release/safe-build/startup/installer.
  The receive-retry code/test gate is therefore verified at that SHA; trusted
  Windows signing was skipped.
- Read-only Render metadata identifies `ari-smart-ro-db` as an available
  PostgreSQL 18 primary in Singapore on compute plan `0.1c-256mb` with 1 GB
  disk. This metadata does not expose the instance's Recovery page, available
  PITR timestamps, or exports. Those capabilities remain unverified for this
  particular instance. No restored instance was listed or used in this check.
- Commit `705493f3` added receipt-backed retries for inventory return and
  part-request fulfilment. Tests cover replay ACK and no second movement/event,
  including a late return retry after that physical item has been reissued.
  Exact-head CI #760 (run `36548450938`) passed all four jobs. CI #761 was
  cancelled by a subsequent hardening-branch push; it is not cited as a pass.
- Commit `6bc3b4d2` added receipt-backed manual and OCR Purchase creation;
  retries with the same action ID no longer generate a second NO-BILL Purchase
  and stock rows. Changed payload with the same action ID returns conflict. Commit
  `b8953b86` made Service completion preserve its original timestamp and
  Complaint resolve/close retries preserve terminal state. Full CI #762
  (run `36549723096`) passed all four jobs for both commits together.
- Commit `3c7338c4` added wallet redemption action receipts and an owner lock
  plus a duplicate-reference debit guard for non-rent transactions. The
  regression covers replay, one debit, and changed action ID on the same bill.
  Exact-head CI #763 (run `36550641895`) passed all four jobs.
- `docs/MAX_PRO_RESTORE_REHEARSAL_EVIDENCE_TEMPLATE.json` explicitly keeps
  unrehearsed counts null and the gate OPEN. All three Bash blocks in the
  isolated restore runbook passed syntax checking. This environment has no
  `pg_dump`, `pg_restore`, or `psql`; no export, restore, or SQL rehearsal ran.
- Offline action tests cover ACK removal only after success, restart recovery,
  corrupt-state quarantine, duplicate local IDs, concurrent enqueue, and
  preservation of unrelated valid pending actions. Device kill/reboot and
  extended offline field tests remain open.
- End-to-end inventory and purchase retry certification is still OPEN: the
  current Flutter `InventoryWorkflowService` does not yet send stable
  `X-ARI-Action-ID` values for purchase, OCR confirm, fulfil or receiving.
  The server receipt tests establish protection only for requests carrying
  that header. A lost response from the current app can still be retried as
  a distinct write, especially for blank-invoice Purchases.
- The broader service/complaint, inventory, purchase and wallet retry audit
  remains open. No real restore rehearsal counts are available; do not infer
  zero values for any category.

## Phase 0 — Release safety
- [x] Identify actually deployed Render branch and live commit.
- [x] Base hardening on live production state.
- [x] Keep work isolated on hardening branch.
- [x] CI gates enabled on `hardening/**`.
- [x] Latest exact code-bearing integrity state verified by CI #763.
- [ ] Protect final release branch from direct unverified changes.
- [ ] Consolidate intentionally retained divergent Windows work before final RC.
- [ ] Produce one immutable Release Candidate commit, release notes and checksums.

## Phase 1 — Crash, data and recovery safety
- [ ] PostgreSQL automated backups/PITR verified on the actual production Recovery page.
- [ ] Restore drill completed from a real backup into an isolated DB.
- [x] Max-Pro RPO/RTO targets documented.
- [ ] Production media persistence/object storage verified.
- [ ] Backup/restore procedure demonstrated before destructive production migrations.
- [ ] Client/server crash telemetry verified end-to-end on real devices.
- [ ] Failed background/offline work survives real-device restart/network loss certification.
- [ ] 24h location queue and reconnect drain verified on real devices; implementation/CI evidence exists.
- [x] Corrupt offline job state quarantine/recovery implemented and CI-covered.
- [x] Offline job-state mutation serialization/locking implemented and CI-covered.
- [x] Offline ACK regression proves unrelated pending actions remain queued.

### Current recovery facts
- production mode requires configured PostgreSQL; SQLite is development-only;
- production media requires persistent filesystem or S3-style storage;
- recovery runbook: `docs/PRODUCTION_BACKUP_RECOVERY_RUNBOOK.md`;
- target DB RPO <= 15 minutes once PITR is verified;
- target core RTO <= 2 hours;
- daily off-provider logical backup and monthly restore drill are required;
- PITR and a real restore drill are still not marked verified.

# Exact completion gate: database-safe visible IDs — PASS

Customer, Job, Service and Complaint visible-ID allocation no longer relies on an unlocked `last + 1` read.

Implementation:
- allocation occurs inside `transaction.atomic()`;
- PostgreSQL transaction advisory locks serialize each namespace/year;
- allocation reads the existing visible high-water mark while locked;
- imported/legacy identifiers are preserved;
- no new production sequence table is required.

External formats remain unchanged:
- Customer: `CUS-YYYY-NNNNNN`
- Customer card: `ARI-YYYY-NNNNNN`
- Job: `JOB-YYYY-NNNNNN`
- Service: `SER-YYYY-NNNNNN`
- Complaint: `CMP-YYYY-NNNNNN`

Verified regression evidence retained in the latest full backend suite:
- **20 simultaneous Customer creates**: all visible IDs unique and all card IDs unique;
- **20 simultaneous Job creates**: all visible IDs unique;
- **20 simultaneous Service creates**: all visible IDs unique;
- **20 simultaneous Complaint creates**: all visible IDs unique;
- each concurrency test mixes two tenants 10 + 10 and preserves the correct company on every created row;
- exact visible prefix/format checks pass;
- forced transaction rollback is tested for all four models;
- rolled-back visible IDs do not leave persisted rows and may be safely reused only because the entire allocation transaction rolled back;
- legacy high-water regression proves new Customer/card allocation starts above an imported high identifier;
- no duplicate visible-ID `IntegrityError` escaped the tested create paths.

**Visible-ID race completion gate: PASS.**

# Explicit operational tenant ownership — implemented, production rehearsal pending
Nullable indexed `company` ownership exists in hardening-branch model/migration state for:
- Customer
- Job
- Service
- Complaint

`python manage.py backfill_tenant_ownership` is dry-run by default:
- never infers ownership from phone number;
- reports `ALREADY_OWNED`, `RESOLVED`, `UNRESOLVED` and `CONFLICT` cases;
- writes only explicit resolved rows when `--apply` is supplied;
- unresolved/conflicting rows remain unchanged;
- JSON evidence output is supported.

**No production migration has been run.**

# Explicit purchase / warehouse tenant ownership — implemented, production rehearsal pending
Nullable indexed `company` ownership exists for:
- Supplier
- Purchase
- PurchaseItem
- InventoryItem
- EngineerBagItem
- InventoryAuditLog
- PartRequest

Expand migrations:
- `purchase/0004_tenant_ownership_expand.py`
- `inventory/0009_tenant_ownership_expand.py`

`python manage.py backfill_inventory_tenant_ownership` is dry-run by default and propagates authoritative conflicts rather than silently choosing a tenant.

`python manage.py rehearse_tenant_migration` provides read-only combined operational/warehouse ownership evidence, before/projected counts and relationship inconsistencies.

**These migrations/backfills have not been run on production.**

# Exact completion gate: Inventory financial/data integrity — PASS for code/CI scope

Financial source of truth reconciles PurchaseItem quantity/cost with physical InventoryItem state using Decimal arithmetic.

Verified rules:
- purchase value = `PurchaseItem.quantity × purchase_price`;
- physical inventory count comes from InventoryItem rows;
- `PENDING_RECEIPT` is not received stock;
- warehouse-available value counts physical `IN_STOCK` and reconciled returned stock semantics;
- `ISSUED`, `INSTALLED` and `SCRAP` values are separated;
- installed stock is not counted as available warehouse stock;
- purchased-vs-physical unit variance is explicit instead of hidden;
- tenant financial snapshots exclude other-company stock/value;
- Excel Purchase lines are quantity-aware;
- API summary, Excel Executive Summary and DB financial snapshot are compared field-by-field.

Verified regression evidence retained in CI #753 covers:
- serialized inventory;
- non-serialized inventory;
- zero-price inventory;
- 5 × ₹125.50 purchase line = ₹627.50;
- ₹0.00 reconciliation difference for fully represented purchase states;
- pending, received/in-stock, issued, installed, returned and missing-unit variance;
- cross-tenant stock/value exclusion;
- API ↔ Excel ↔ database money/count parity;
- duplicate receiving is rejected by the warehouse workflow;
- installed physical stock cannot be reused as available stock;
- two simultaneous engineers attempting to issue the same physical unit produce exactly one active assignment.

## Safe return/reissue lifecycle
- tenant-safe `/api/inventory/return/` is transactionally locked;
- only currently issued same-company physical stock can be returned;
- EngineerBagItem history becomes `RETURNED` and records `return_date`;
- physical InventoryItem returns to `IN_STOCK`, restoring available warehouse value;
- duplicate return is rejected;
- audit log records the issued → warehouse return transition;
- the existing OneToOne bag row is safely reused when the same physical unit is later reissued;
- reissue can move the physical unit to another same-company engineer without creating a second bag row;
- serialized parts still require a serial number.

**Inventory financial/data-integrity code+CI completion gate: PASS.**  
A production-like inventory ownership migration/reconciliation rehearsal is still a separate open release gate.

# Exact completion gate: duplicate supplier invoices — code/test gate PASS, real rehearsal OPEN

Canonical runtime/audit identity:

`company + supplier + normalized invoice number`

Normalization:
- trim surrounding whitespace;
- uppercase;
- remove whitespace differences;
- preserve punctuation identity.

Runtime protection:
- manual Purchase create locks the supplier row inside `transaction.atomic()`;
- OCR Confirm locks the same supplier row before duplicate check/create;
- manual and OCR paths use the same canonical identity helper;
- supplier/company workspace scope remains server-controlled.

Concurrency evidence retained in the latest full regression:
- **20 parallel manual Purchase submissions** using whitespace/case variants of the same logical invoice create exactly **1 Purchase**;
- **20 parallel OCR Confirm submissions** using whitespace/case variants create exactly **1 Purchase**.

Read-only command:
`python manage.py audit_duplicate_supplier_invoices`

The rehearsal report now includes:
- `DRY_RUN_ONLY` mode;
- normalization rule;
- total purchase count;
- unique identity count;
- duplicate groups and duplicate row count;
- company ID;
- supplier ID/name;
- normalized and raw invoice values;
- affected Purchase IDs;
- blank normalized-invoice IDs/count;
- unresolved/null-company Purchase IDs/count;
- aggregate `blocking_issue_count`;
- machine-readable `rehearsal_status` = `CLEAN` or `BLOCKED`;
- machine-readable `constraint_ready` boolean;
- optional JSON output;
- future normalized-key database uniqueness design.

`--fail-on-conflict` now exits non-zero if any duplicate identity, blank normalized invoice, or unresolved company row blocks the future uniqueness constraint.

CI #753 specifically proves:
- the audit remains read-only;
- clean data returns `CLEAN` and `constraint_ready=true`;
- duplicate normalized identity causes `--fail-on-conflict` to fail;
- blank identity is an explicit blocker;
- unresolved/null-company ownership is an explicit blocker;
- duplicate identity stays tenant+supplier scoped, so the same external invoice string in another tenant/supplier scope is not falsely treated as a duplicate.

**Duplicate-invoice code/concurrency/tooling gate: PASS.**  
**Actual isolated restored production-like duplicate audit: NOT YET RUN, therefore the rehearsal/release gate remains OPEN.**

The future database uniqueness constraint remains intentionally deferred until a real restored production-like rehearsal reports `CLEAN`/`constraint_ready=true`, or every blocking legacy row has an approved remediation. It must not be applied to production without explicit approval.

# Phase 2 — Core operational certification
- [ ] Attendance — implementation strong; real-device certification pending.
- [ ] Employee Live Location / Route History — implementation/CI strong; field certification pending.
- [ ] Face & Device Security — code hardening present; full device/integrity certification pending.
- [ ] Customer Management — explicit ownership/backfill + visible-ID race gate passed; production-like migration rehearsal pending.
- [ ] My Jobs / Secure Field Work — assignment/tenant scope + visible-ID race gate passed; migration rehearsal pending.
- [ ] Service — shared-phone/tenant guards + visible-ID race gate passed; migration rehearsal pending.
- [ ] Complaint Management — tenant/workflow guards + visible-ID race gate passed; migration rehearsal pending.
- [ ] Rent Management — tenant scope/idempotency/payment integrity covered; production migration rehearsal pending.
- [ ] Payment History / Ledger — tenant reads/writes + atomic retry idempotency covered.
- [ ] Inventory Control — tenant ownership, financial reconciliation, return/reissue, concurrent issue protection CI-green; migration rehearsal pending.
- [ ] Engineer Bag / Part Request — company scope + create idempotency + return/reissue lifecycle CI-green.

# Remaining migration/schema/recovery P1 blockers
No CI-detected P0 defect is open at CI #753, but overall Max-Pro remains blocked by material P1/certification work:

1. **Actual isolated restored production-like rehearsal** for Customer/Job/Service/Complaint ownership.
2. **Actual isolated restored production-like rehearsal** for Supplier/Purchase/PurchaseItem/Inventory ownership.
3. Run `audit_duplicate_supplier_invoices --fail-on-conflict` on that isolated production-like copy and resolve/quarantine every blocking legacy identity/ownership issue before any DB unique constraint.
4. Verify Render/PostgreSQL PITR/Recovery availability and perform a real isolated restore drill.
5. Verify production media persistence/object storage.
6. Certify Attendance/GPS on real Vivo S20, Vivo T3 and Redmi 8A-class devices: app killed, reboot, permission/battery changes, 24h tracking, long offline and reconnect.
7. Verify crash telemetry end-to-end on real devices.
8. Continue idempotency audit for remaining retryable/destructive business writes.
9. Continue Android root/emulator/mock/fake-camera/liveness strengthening with older-device compatibility fallback.
10. Obtain/configure trusted Windows Authenticode signing and verify signatures.
11. Map/certify all 38 modules, performance/memory, rollback rehearsal, checksums and final UAT.

# Production migration gate
Before any production schema/cutover action:
1. verify PITR and create an off-provider logical backup;
2. restore a production-like DB copy in isolation;
3. run `rehearse_tenant_migration` read-only;
4. run both tenant backfill commands in dry-run mode;
5. run `audit_duplicate_supplier_invoices --fail-on-conflict` with JSON evidence;
6. reconcile every unresolved/conflict/duplicate/blank-identity result;
7. rehearse `--apply` only on the isolated copy;
8. prove before/after object counts and relationship consistency;
9. only then propose production migration/constraints for explicit approval.

# Phase 3 — Corporate modules
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

# Phase 4 — Final certification
- [ ] All 38 blueprint modules mapped to tests.
- [ ] Zero open P0 blockers.
- [ ] Zero open P1 blockers.
- [ ] Android device matrix passed including low-memory devices.
- [ ] App-killed/reboot/background-location/permission-change tests passed.
- [ ] Offline→online sync stress test passed on device.
- [ ] Database backup + restore drill passed.
- [ ] Security/RBAC regression passed after production-like migration rehearsal.
- [ ] Migration rehearsal passed on production-like data.
- [ ] Duplicate invoice rehearsal passed on production-like data.
- [ ] Performance/memory checks passed.
- [x] Windows unsigned build/installer CI path verified; trusted Authenticode signing remains separately open.
- [ ] Release checksums recorded.
- [ ] Rollback procedure tested.
- [ ] Final UAT signed off.
