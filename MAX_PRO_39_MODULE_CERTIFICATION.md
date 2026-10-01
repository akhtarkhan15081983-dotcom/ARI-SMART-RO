# ARI SMART RO — 39-Module Max-Pro Certification Matrix

Branch: `hardening/max-pro-5of5-2026-09-29`

Policy: No module is certified 10/10 from code inspection alone. A 10/10 requires backend/API correctness, tenant isolation, role/permission enforcement, audit/history integrity, retry/idempotency/offline behavior where relevant, automated regression evidence, and mobile/Windows/field behavior where relevant.

Legend:
- **STRONG / CI GATE** — backend/security/regression evidence is strong; exact-head CI and/or platform evidence still gates final 10/10.
- **PLATFORM GATE** — code/tests are strong; real device/Windows behavior remains.
- **MIGRATION GATE** — schema/code is ready but isolated migration rehearsal is required before production.
- **ARCHITECTURE GATE** — a known production architecture decision remains.
- **CERTIFICATION REVIEW** — no known critical defect from current review, but remaining evidence must be consolidated before 10/10.

| # | Module | Current certification state | Remaining hard gate before 10/10 |
|---|---|---|---|
| 1 | Attendance | STRONG / CI GATE | Exact-head CI + final field-device verification |
| 2 | Employee HRMS | STRONG / CI GATE | Exact-head CI + final payroll/field workflow evidence |
| 3 | Training | STRONG / CI GATE | Exact-head CI + final mobile/Windows training UX evidence |
| 4 | Employee Management | STRONG / CI GATE | Exact-head CI + final cross-role/platform review |
| 5 | Work Calendar | STRONG / CI GATE | Exact-head CI + final mobile/Windows schedule UX evidence |
| 6 | Work Route / Day Journey | STRONG / CI GATE | Exact-head CI + real route/location field behavior |
| 7 | My Jobs | STRONG / CI GATE | Exact-head CI + field-device offline workflow verification |
| 8 | Assigned Customers | STRONG / CI GATE | Exact-head CI |
| 9 | Customer Management | STRONG / CI GATE | Exact-head CI + final shared-phone/account-link migration review |
| 10 | Walk-In Installation | MIGRATION GATE | Exact-head CI + isolated ROAsset company migration rehearsal |
| 11 | Service | STRONG / CI GATE | Exact-head CI + final mobile/Windows workflow evidence |
| 12 | Complaint Management | STRONG / CI GATE | Exact-head CI + final mobile/Windows workflow evidence |
| 13 | Inventory Control | MIGRATION GATE | Exact-head CI + isolated ROAsset migration rehearsal |
| 14 | Engineer Bag | STRONG / CI GATE | Exact-head CI |
| 15 | Part Request | STRONG / CI GATE | Exact-head CI |
| 16 | QR Verification | STRONG / CI GATE | Exact-head CI + physical scan field verification |
| 17 | Live Map | PLATFORM GATE | Real multi-employee map/device location verification |
| 18 | Engineer Live Location | PLATFORM GATE | Background Android field verification across device classes |
| 19 | Rent Management | STRONG / CI GATE | Exact-head CI |
| 20 | Payment History | STRONG / CI GATE | Exact-head CI |
| 21 | Business Reports | STRONG / CI GATE | Exact-head CI + generated file/platform validation |
| 22 | Calling Desk | STRONG / CI GATE | Exact-head CI |
| 23 | Notifications & Offers | STRONG / CI GATE | Exact-head CI + final push/display platform verification |
| 24 | Refer & Wallet | STRONG / CI GATE | Exact-head CI |
| 25 | My RO | STRONG / CI GATE | Exact-head CI + final customer-device UX verification |
| 26 | Customer Rent & Payment | STRONG / CI GATE | Exact-head CI |
| 27 | Customer History | CERTIFICATION REVIEW | Consolidate explicit history/audit regression + platform UX evidence |
| 28 | Shop | STRONG / CI GATE | Exact-head CI is green; final real-device/customer checkout UX verification remains |
| 29 | Profile | STRONG / CI GATE | Exact-head CI |
| 30 | Face & Device Security | PLATFORM GATE | Exact-head CI + remaining field-device compatibility evidence |
| 31 | Password Reset Approvals | STRONG / CI GATE | Exact-head CI |
| 32 | Role Access Control | STRONG / CI GATE | Exact-head CI |
| 33 | Attendance Selfie Review | STRONG / CI GATE | Exact-head CI + final admin UI/platform verification |
| 34 | Attendance Security Test | STRONG / CI GATE | Exact-head CI + device-level mock/root/emulator field checks |
| 35 | Device Health Center | STRONG / CI GATE | Exact-head CI + final device-class field validation |
| 36 | Download Center | PLATFORM GATE | Actual Android + Windows external-file opening verification |
| 37 | SaaS Command Center | STRONG / CI GATE | Exact-head CI + final platform-superuser operational review |
| 38 | ANDY AI | PLATFORM / EXTERNAL-SERVICE GATE | Exact-head CI + external inference service validation + client field UX |
| 39 | RO Alarm Center | STRONG / CI GATE | Exact-head CI + final mobile/customer notification UX verification |

## Key hardening already present

- Shared/duplicate phone identity resolution fails closed rather than selecting the first customer.
- Service, Complaint, My Jobs, Calling Desk, Assigned Customers, Payment History, Business Reports, HRMS, Engineer Bag, Part Request and several admin/security paths have explicit tenant isolation.
- Rent payment authorization is enforced in the actual tenant-scoped routed wrapper before tenant/customer lookup.
- Inventory summary and export are tenant-scoped.
- Physical RO units now support company ownership through `ROAsset.company`.
- Authenticated Shop stock can derive from company-owned active unassigned WAREHOUSE ROAssets through `tenant_stock_quantity`.
- Dedicated guest builds route public requests using `TENANT_SLUG`; public guest requests support company ownership.
- ANDY heavy LLM/STT/TTS inference stays outside the main Django process, with authenticated external services, bounded retries/timeouts, tenant-scoped reads/knowledge, confirmation-gated actions and normal Job audit history.
- Download Center file discovery handles supported extensions, disappearing files and read/open failures gracefully.
- RO Alarm Center has explicit own-RO/customer scoping, cross-company blocking, idempotent automatic refresh, customer/admin notification fan-out, and acknowledge/resolve actor/timestamp lifecycle coverage.

## Production blockers shared across modules

1. Exact-head CI must be fully green.
2. `assets/0004_roasset_company.py` and `customers/0022_publiccustomerrequest_company.py` must not be run on production before isolated migration rehearsal.
3. Global/non-dedicated guest Shop builds need an explicit tenant-selection/routing decision before full multi-tenant Shop certification.
4. Download Center needs real Android + Windows external-file opening evidence.
5. Background location, face/device and other hardware-sensitive flows need final field-device evidence before 10/10.
6. No production deploy/release is authorized by this document.


## Exact-head CI baseline

Verified exact-head baseline:
- Commit: `1db2656868f1bc45a0c6d327f296e817c0e298a0`
- CI: #1051
- Result: SUCCESS
- Production container: PASS
- Django deployment checks: PASS
- Backend tests: PASS
- Flutter analyze: PASS
- Flutter tests: PASS
- Android debug APK compile: PASS
- Android artifact upload: PASS
- Android emulator startup smoke: PASS
- Windows release / installer chain: PASS

This closes the generic CI gate for modules whose only remaining blocker was exact-head build/test evidence. Modules that still have migration, architecture, hardware, external-service or field-device gates remain not-10/10 until those separate risks are closed.


## Shop architecture gate closure

Verified on exact-head CI #1057 at commit `811d2ac288e99d07d15c66d2d9f88cdcba69fcba`:
- Backend tests: PASS
- Flutter analyze/tests: PASS
- Android compile/emulator smoke: PASS
- Windows: PASS
- Production container: PASS

Shop tenant-routing evidence:
- Dedicated builds use deterministic `TENANT_SLUG` routing.
- Global/non-dedicated builds discover only active, public, subscription-accessible ARI shops.
- Global guest checkout requires explicit shop/company selection instead of guessing a tenant.
- Selected `company_slug` is persisted through the public request flow.
- `PublicCustomerRequest.company` stores tenant ownership.
- Calling Desk scopes tenant-owned guest leads.
- Authenticated physical availability derives from company-owned active unassigned WAREHOUSE ROAssets.
- Legacy global `ROModel.stock_quantity` remains only as backward-compatible guest fallback where tenant stock is unavailable.

The prior Shop ARCHITECTURE GATE is therefore closed. Shop is not yet 10/10 because final real-device/customer checkout UX evidence and migration rehearsal for tenant ownership fields remain separate gates.
