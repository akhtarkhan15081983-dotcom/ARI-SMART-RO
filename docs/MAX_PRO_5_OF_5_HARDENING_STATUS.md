# ARI SMART RO — Max-Pro 5/5 Hardening Status

**Hardening branch:** `hardening/max-pro-5of5-2026-09-29`  
**Live-production baseline:** `hotfix/admin-otp-testing-toggle-2026-09-27` @ `9066929c8297181dc1fce20943f67e4ef09fed88`  
**Prepared production ancestor:** `deploy/v1.0.48-production` @ `10f475e78610d90c1d6454c7b66f906ff8d044b6`  
**Started:** 2026-09-29

## Non-negotiable release rule
ARI SMART RO must not be declared 5/5 Max-Pro until every P0/P1 and certification gate is verified with evidence. Code existence or a green CI run alone is not sufficient for overall 5/5. `main` and live production are not active hardening branches.

## Latest exact code-bearing verification

**Verified code SHA:** `769f04041d1df5acee07e554efbf85f3292fff9e`  
**CI:** #750  
**Run ID:** `36530880757`

CI #750 passed all required code-bearing gates:

- Django deployment checks: PASS
- migration drift check (`makemigrations --check --dry-run`): PASS / no changes detected
- full PostgreSQL-backed backend regression: PASS — **450 tests, 0 failures**
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

The previous #749 backend failure was a test-fixture problem caused by `reset_sequences=True` combined with CI `--keepdb`; it occurred before inventory business code ran. The fixture was made sequence-agnostic and the corrected exact-head suite passed in #750.

**No production deployment, Render branch change, production database migration, production data mutation, `main` merge or release was performed during this cycle.**

## Phase 0 — Release safety
- [x] Identify actually deployed Render branch and live commit.
- [x] Base hardening on live production state.
- [x] Keep work isolated on hardening branch.
- [x] CI gates enabled on `hardening/**`.
- [x] Latest exact code-bearing integrity state verified by CI #750.
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

Exact CI #750 evidence:
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

Exact regression evidence in CI #750 covers:
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
A missing workflow was found and fixed rather than faking the `RETURNED` state:

- new tenant-safe `/api/inventory/return/` action is transactionally locked;
- only currently issued same-company physical stock can be returned;
- EngineerBagItem history becomes `RETURNED` and records `return_date`;
- physical InventoryItem returns to `IN_STOCK`, restoring available warehouse value;
- duplicate return is rejected;
- audit log records the issued → warehouse return transition;
- the existing OneToOne bag row is safely reused when the same physical unit is later reissued;
- reissue can move the physical unit to another same-company engineer without creating a second bag row;
- serialized parts still require a serial number.

Exact regression evidence:
- issue changes warehouse value from ₹350.00 to ₹0.00;
- return restores warehouse value to exactly ₹350.00;
- duplicate return returns conflict;
- returned physical item can be reissued;
- exactly one EngineerBagItem row remains for that physical item;
- simultaneous issue race yields one successful active assignment.

**Inventory financial/data-integrity code+CI completion gate: PASS.**  
A production-like inventory ownership migration/reconciliation rehearsal is still a separate open release gate.

# Exact completion gate: duplicate supplier invoices — code/test gate PASS, real rehearsal OPEN

Canonical runtime/audit identity is now shared:

`company + supplier + normalized invoice number`

Normalization:
- trim surrounding whitespace;
- uppercase;
- remove whitespace differences;
- preserve punctuation identity.

This closes the previous mismatch where the audit could classify `"INV 100"` and `"inv100"` as the same logical invoice while runtime `iexact` checks could allow separate writes.

Runtime protection:
- manual Purchase create locks the supplier row inside `transaction.atomic()`;
- OCR Confirm locks the same supplier row before duplicate check/create;
- manual and OCR paths use the same canonical identity helper;
- supplier/company workspace scope remains server-controlled.

Exact concurrency tests in CI #750:
- **20 parallel manual Purchase submissions** using whitespace/case variants of the same logical invoice create exactly **1 Purchase**;
- **20 parallel OCR Confirm submissions** using whitespace/case variants create exactly **1 Purchase**.

Read-only command:
`python manage.py audit_duplicate_supplier_invoices`

Report includes:
- `DRY_RUN_ONLY` mode;
- normalization rule;
- total purchase count;
- unique identity count;
- duplicate group count;
- duplicate row count;
- company ID;
- supplier ID/name;
- normalized invoice number;
- raw invoice values;
- affected Purchase IDs;
- per-group count;
- optional JSON output;
- future normalized-key database uniqueness design.

Tests prove the command does not modify Purchase rows and keeps duplicate identity tenant+supplier local, allowing the same external invoice string in a different tenant/supplier scope.

**Duplicate-invoice code/concurrency gate: PASS.**  
**Actual isolated restored production-like duplicate audit: NOT YET RUN, therefore the rehearsal/release gate remains OPEN.**

The future database uniqueness constraint remains intentionally deferred until that real rehearsal identifies/cleans any legacy conflicts. It must not be applied to production without explicit approval.

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

# Tenant / RBAC evidence
Verified hardening includes:
- cross-company customer assignment blocked;
- guessed-ID Admin Job OTP cross-tenant access blocked;
- shared-phone Service/Complaint customer ambiguity hardened with durable linkage;
- Service ownership fields cannot be rewritten by engineer generic updates;
- Complaint assignment/workflow relations enforce workspace rules;
- Rent management/payment/history fail closed across tenants;
- Supplier/Purchase lists/writes and OCR supplier matching are workspace-scoped;
- warehouse receiving/summary/reporting/issue/bag paths are company-scoped;
- company-bound users do not gain all-company fallback through legacy compatibility.

# Remaining migration/schema/recovery P1 blockers
No CI-detected P0 defect is open at CI #750, but overall Max-Pro remains blocked by material P1/certification work:

1. **Actual isolated restored production-like rehearsal** for Customer/Job/Service/Complaint ownership.
2. **Actual isolated restored production-like rehearsal** for Supplier/Purchase/PurchaseItem/Inventory ownership.
3. Run `audit_duplicate_supplier_invoices` on that isolated production-like copy and resolve/quarantine every legacy duplicate identity before any DB unique constraint.
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
5. run duplicate supplier-invoice audit;
6. reconcile every unresolved/conflict/duplicate result;
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

## 5/5 definition
A module is 5/5 only when implemented, permission-safe, recoverable, observable, data-safe, tested on supported platforms, resilient to expected device/network failures, and free of open P0/P1 defects. ARI SMART RO is **not yet declared 5/5 complete**.

## Next execution order
1. Build/verify the isolated restored-database migration rehearsal workflow and evidence bundle without touching production.
2. Run tenant ownership + duplicate invoice rehearsal only against an isolated production-like copy when such a copy is available/authorized.
3. Verify Render PITR and execute the isolated restore drill before production migration approval.
4. Continue remaining business-write idempotency audit and close retry/race gaps.
5. Certify Attendance + GPS on the required real-device matrix.
6. Verify production media durability and crash telemetry.
7. Continue 38-module certification, performance/memory, rollback/checksum and final UAT work.
