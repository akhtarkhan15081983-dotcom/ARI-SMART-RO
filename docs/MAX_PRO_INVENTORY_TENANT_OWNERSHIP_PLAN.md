# ARI SMART RO — Max-Pro Inventory / Purchase Tenant Ownership Plan

Status: DESIGN / HARDENING BRANCH ONLY. No production migration is authorized by this document.

## Goal

Make warehouse, purchasing and physical stock ownership explicit so inventory is never scoped by whichever engineer currently holds an item.

## Ownership roots

Recommended expand-first fields:

- `purchase.Supplier.company -> tenancy.Company` (nullable/indexed during transition)
- `purchase.Purchase.company -> tenancy.Company` (nullable/indexed; authoritative purchase root)
- `purchase.PurchaseItem.company -> tenancy.Company` (nullable/indexed denormalized integrity/query key, must equal `purchase.company`)
- `inventory.InventoryItem.company -> tenancy.Company` (nullable/indexed; inherited from `purchase_item.company`)
- `inventory.PartRequest.company -> tenancy.Company` (nullable/indexed; inherited from requesting engineer)
- `inventory.EngineerBagItem.company -> tenancy.Company` (nullable/indexed; must match engineer + inventory item)
- `inventory.InventoryAuditLog.company -> tenancy.Company` (nullable/indexed immutable audit ownership)

`PartMaster` may remain a global catalogue unless ARI later needs tenant-customized part catalogues. A physical `InventoryItem` must never be global.

## Why engineer-bag inference is not enough

Stock exists before issue, while returned, while pending receipt, while scrapped, and while not assigned to any engineer. Deriving company from the current bag would make unissued/returned stock ambiguous and historical ownership mutable.

## Backfill evidence order

### Supplier / Purchase

1. explicit purchase creator/verifier membership when exactly one active company is provable;
2. all existing PurchaseItems -> InventoryItems -> EngineerBagItems, only when every non-null engineer company agrees;
3. related inventory audit actors only as supporting evidence, never as the sole source when actor has multiple memberships.

Conflicting evidence must produce a conflict report; do not choose one company silently.

### PurchaseItem

Authoritative ownership must equal `purchase.company`. Any existing item evidence that disagrees is a migration conflict.

### InventoryItem

Authoritative ownership must equal `purchase_item.company`. A current/historical engineer bag may confirm ownership but must not override purchase ownership.

### PartRequest

Ownership is the requesting engineer's company. If engineer company is null, request stays unresolved.

### EngineerBagItem

All three must agree when non-null:
- bag `company`;
- engineer `company`;
- inventory item `company`.

### InventoryAuditLog

Prefer immutable inventory-item ownership. Engineer/actor/job relations must not contradict it.

## Safe rollout

1. Add nullable indexed fields only.
2. Add dry-run ownership report with totals, resolved, unresolved and conflicts.
3. Rehearse against an isolated restored production-like database.
4. Resolve/quarantine conflicts; never expose unresolved rows cross-tenant.
5. Dual-write company on supplier/purchase/receipt/issue/request/return/install/audit operations.
6. Switch all staff reads to explicit `company=request_company(request)`.
7. Scope code generation, receiving queue, QR PDF, summary and Excel reports by explicit company.
8. Add relation-consistency validation.
9. Make active-domain ownership non-null only after 100% reconciliation and a restore rehearsal.
10. Remove assignment-derived legacy fallbacks only after production cutover approval.

## Endpoints that remain schema-dependent until rollout

The following are global today and must not be called tenant-certified until explicit stock ownership exists:

- inventory receiving queue;
- inventory receive / receive-photo;
- purchase-based internal code generation;
- inventory QR label PDF;
- inventory summary counts;
- professional inventory Excel report;
- purchase/supplier aggregates used by inventory reporting.

Engineer bag and part-request flows already have workspace guards, but this does not make the warehouse itself tenant-safe.

## Required migration rehearsal assertions

- row counts before/after match except intentional migration metadata;
- every resolved PurchaseItem company equals Purchase company;
- every resolved InventoryItem company equals PurchaseItem company;
- no bag may link engineer company A to inventory company B;
- no PartRequest company may differ from engineer company;
- no inventory audit row may cross ownership boundaries;
- tenant A summary/QR/report contains zero tenant B stock;
- unresolved/conflicting stock is excluded from tenant-facing reads;
- rollback restores pre-migration schema/data on the rehearsal database.
