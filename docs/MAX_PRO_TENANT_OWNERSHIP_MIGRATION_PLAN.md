# ARI SMART RO — Max-Pro Tenant Ownership Migration Plan

Status: DESIGN ONLY — no production migration/deploy is authorized by this document.

## Goal

Make tenant/company ownership explicit and enforceable for the operational domain instead of inferring it indirectly from employee assignment.

Primary models in scope:

- `customers.Customer`
- `jobs.Job`
- `service.Service`
- `complaints.Complaint`

Follow-on inventory dependency:

- `inventory.InventoryItem`
- `inventory.PartRequest`
- purchasing/stock records that feed `InventoryItem`

## Why this is required

Today several records derive company context from an assigned employee. That is insufficient for:

- unassigned customers;
- shared/duplicate customer phone numbers;
- staff/admin direct-ID endpoints;
- reassignment between employees;
- historical records whose assigned employee changed;
- stock that is not currently in an engineer bag;
- reliable database-level tenant constraints.

## Safety principles

1. Never add a required `company_id` in one step.
2. Never infer tenant from customer phone number.
3. Never silently guess when evidence conflicts.
4. Backfill only from explicit trusted relations.
5. Keep legacy rows quarantinable until ownership is proven.
6. Add read/write guards before making `company_id` non-null.
7. Take a verified logical backup/export before production migration.
8. Run migration first on an isolated restored copy of production data.
9. Reconcile row counts and cross-tenant conflicts before cutover.
10. Production rollout requires separate explicit approval.

## Proposed schema — Phase 1 (expand, nullable)

Add nullable indexed `company` foreign keys to:

```text
Customer.company   -> tenancy.Company (PROTECT, null=True, db_index=True)
Job.company        -> tenancy.Company (PROTECT, null=True, db_index=True)
Service.company    -> tenancy.Company (PROTECT, null=True, db_index=True)
Complaint.company  -> tenancy.Company (PROTECT, null=True, db_index=True)
```

Do not change existing API behavior in the schema migration itself.

For inventory follow-on, add nullable company ownership to the purchasing/stock root first, then propagate to `InventoryItem`; do not derive stock ownership from the current engineer bag because stock exists before issue and after return.

## Backfill evidence order

### Customer

Use the first unambiguous source below:

1. `assigned_engineer.company_id`
2. linked active/historical Jobs when every non-null `job.engineer.company_id` agrees
3. linked Services when every non-null `service.engineer.company_id` agrees
4. linked Complaints when every non-null `complaint.engineer.company_id` agrees
5. linked customer user's active `CompanyMembership`, only when exactly one active company exists

If two trusted sources disagree, do **not** choose one. Write the row to a migration conflict report.

### Job

Preferred ownership:

1. `job.customer.company_id` after Customer backfill
2. `job.engineer.company_id`

If both exist and differ, quarantine as a conflict. Never overwrite silently.

### Service

All non-null ownership evidence must agree:

- `service.customer.company_id`
- `service.engineer.company_id`
- `service.job.company_id` when linked

Any disagreement is a conflict.

### Complaint

All non-null ownership evidence must agree:

- `complaint.customer.company_id`
- `complaint.engineer.company_id`
- `complaint.job.company_id` when linked
- `complaint.linked_service.company_id` when linked

Any disagreement is a conflict.

## Phase 2 — audit-only backfill command

Create a management command with dry-run as the default, for example:

```text
python manage.py backfill_tenant_ownership --dry-run
```

The command must output:

- total rows per model;
- already-owned rows;
- rows safely inferable;
- rows with no evidence;
- rows with conflicting evidence;
- per-company counts;
- stable IDs for every unresolved/conflicting row.

No write should occur unless an explicit `--apply` flag is supplied.

## Phase 3 — dual write and tenant-scoped reads

Before enforcing non-null ownership:

- every Customer creation/import assigns `company=request_company(request)`;
- every Job inherits `company=customer.company` and verifies engineer company matches;
- every Service verifies customer, engineer, asset and job all resolve to the same company;
- every Complaint verifies customer, engineer, job and linked service all resolve to the same company;
- all staff list/detail/search/update/delete endpoints filter `company=request_company(request)`;
- customer endpoints filter by durable `Customer.user` linkage plus company ownership;
- engineer endpoints require both `company` and assignment.

During this phase, legacy `company=NULL` reads may remain only in narrowly defined legacy compatibility paths. Company-bound users must never fall back to null/all-company records.

## Phase 4 — database integrity constraints

After backfill reaches 100% resolved for active operational rows:

1. add indexes on frequently filtered `(company, status)` and `(company, id)` paths;
2. make company non-null for active-domain models where safe;
3. add model/database validation for relation consistency;
4. add unique constraints that are tenant-local where business IDs should be reusable across companies in future;
5. retain globally unique immutable IDs only where intentionally global.

Application-level validation is still required because standard SQL foreign keys do not prove that two referenced rows belong to the same company.

## Phase 5 — remove legacy inference

Only after the new ownership field is fully populated and CI/UAT is green:

- remove phone-number ownership inference;
- remove all-company fallback code;
- remove tenant-less operational write paths;
- keep explicit migration/admin repair tooling for historical quarantine rows.

## Conflict handling

Create a durable migration report rather than silently modifying ambiguous data. Each conflict entry should contain:

- model + primary key;
- candidate company IDs and their evidence sources;
- assigned employee/customer/job/service references;
- resolution state;
- manual resolution note and actor.

No conflicting row should become accessible to another tenant while unresolved.

## Test matrix before production

Required automated tests:

- admin A cannot list/read/update/delete company B rows by guessed ID;
- engineer A cannot mutate company B work even if directly assigned ID is supplied in request data;
- customer with a duplicate/shared phone sees only their durable linked Customer record;
- cross-company customer/engineer pairing is rejected on Job/Service/Complaint create and update;
- reassignment cannot move a record across company boundaries;
- bulk import always stamps the active company;
- unassigned customers remain visible only inside their owning company;
- emergency/admin OTP remains company scoped;
- rent/payment history and reports are company scoped;
- inventory issue/receive/report paths cannot cross company ownership.

## Production rollout gate

Do not deploy the schema migration until all of the following are true:

- current hardening CI is fully green;
- production backup/PITR availability has been verified;
- a current production logical backup has been restored successfully into an isolated database;
- dry-run ownership report has zero unexplained conflicts or every conflict has an approved resolution;
- row-count and financial-ledger reconciliation passes;
- rollback procedure has been rehearsed;
- explicit production migration/deploy approval is given.

## Rollback strategy

The early phases are expand-only: nullable columns and dual-write logic are backward compatible. If application rollout must be reverted, retain populated `company_id` columns and roll back application code first. Do not drop ownership columns during an emergency rollback. Destructive cleanup belongs only to a later maintenance release after stable production evidence.
