# Isolated production-like migration rehearsal (OPEN)

This is an operator runbook, not evidence of a completed restore. Never run the
backfill `--apply` against the live database. The production connection must
not be present in the rehearsal process environment.

## Provider and backup preflight

1. Confirm the selected Render workspace and the `ari-smart-ro-db` instance ID,
   plan, PostgreSQL version, region, Recovery page, oldest/newest recoverable
   timestamps, snapshot/export availability, and PITR retention. Capture the
   page or API response with timestamp; redact hostnames, users and secrets.
2. In the Recovery flow choose **restore to a new instance**, inspect the
   destination name and price before confirming, and abort any flow that
   proposes replacing the existing instance. Record source backup timestamp,
   restore instance ID, start/end time and chosen recovery point.
3. For an independent copy, run `pg_dump` from a controlled machine over TLS
   with a read-only source credential where possible. Use the PostgreSQL client
   major version compatible with the server. Configure distinct `pg_service.conf`
   entries and a protected `PGPASSFILE` (mode 0600) outside the repository;
   connection URLs and passwords must not appear in command arguments, history
   or CI logs. Require TLS certificate verification for external connections.

```bash
umask 077
test -n "${SOURCE_PG_SERVICE:-}" && test -n "${BACKUP_DIR:-}" || exit 1
mkdir -p "$BACKUP_DIR"
pg_dump --dbname="service=$SOURCE_PG_SERVICE" --format=custom --no-owner --no-acl \
  --file="$BACKUP_DIR/ari-source.dump"
test -s "$BACKUP_DIR/ari-source.dump"
pg_restore --list "$BACKUP_DIR/ari-source.dump" > "$BACKUP_DIR/archive.list"
sha256sum "$BACKUP_DIR/ari-source.dump" > "$BACKUP_DIR/ari-source.dump.sha256"
```

Copy the encrypted dump and checksum to durable storage outside Render, then
verify the copied object's checksum. Record size, SHA-256, storage location
identifier and retention policy without exposing credentials or customer data.

## Destination isolation and restore

Provision a separate PostgreSQL instance and a separate logical database with
the same major version. No production service may reference it. Deny application
traffic and scheduled workers; use an isolated operator credential. The target
must be empty. The operator must compare the instance IDs and hostnames from
the Render dashboard before configuring `RESTORE_PG_SERVICE`.

```bash
test -n "${RESTORE_PG_SERVICE:-}" && test -n "${SOURCE_PG_SERVICE:-}" || exit 1
test "$RESTORE_PG_SERVICE" != "$SOURCE_PG_SERVICE" || exit 1
sha256sum --check "$BACKUP_DIR/ari-source.dump.sha256"
psql "service=$RESTORE_PG_SERVICE" -X -v ON_ERROR_STOP=1 -Atc \
  "SELECT current_database(), current_user, inet_server_addr(), current_setting('server_version');"
psql "service=$RESTORE_PG_SERVICE" -X -v ON_ERROR_STOP=1 -Atc \
  "SELECT count(*) FROM pg_class WHERE relkind IN ('r','p') AND relnamespace='public'::regnamespace;"
# Require zero user tables and independently confirm this is the isolated target.
pg_restore --dbname="service=$RESTORE_PG_SERVICE" --no-owner --no-acl \
  --exit-on-error --single-transaction "$BACKUP_DIR/ari-source.dump"
```

The service-name comparison alone is insufficient: different entries can address the same
database. Record separate source and target **Render instance IDs** and require
an operator check of host/database identity and zero target tables. Do not run
`--clean`, `--create`, or `--if-exists`. Do not start the application against the
restored instance before the safe commands below.

## Read-only evidence on the restored copy

Create an evidence directory with restricted permissions. Set `DATABASE_URL`
only to the isolated target in a shell with production credentials removed.
First record `django_migrations` and row counts for Customer, Job, Service,
Complaint, Supplier, Purchase, PurchaseItem, InventoryItem, EngineerBagItem,
PartRequest and InventoryAuditLog. Apply **reviewed** expand migrations only to
the isolated target if its source schema predates this branch, then run:

```bash
python manage.py rehearse_tenant_migration --json "$EVIDENCE_DIR/rehearsal.json"
python manage.py backfill_tenant_ownership --report "$EVIDENCE_DIR/operational.json"
python manage.py backfill_inventory_tenant_ownership --report "$EVIDENCE_DIR/warehouse.json"
python manage.py audit_duplicate_supplier_invoices \
  --fail-on-conflict --json "$EVIDENCE_DIR/invoices.json"
```

Keep the invoice JSON even when the command exits nonzero. Record its exit code.
Extract per-model and total `ALREADY_OWNED`, `RESOLVED`, `UNRESOLVED`, `CONFLICT`
from both backfill reports; record `duplicate_group_count`,
`duplicate_row_count`, `blank_identity_row_count`,
`unresolved_company_row_count`, `blocking_issue_count` and
`relation_inconsistency_count`. Keep the unresolved/conflict row identifiers
in restricted evidence, not a public issue or commit.

Take counts and relation inconsistency snapshots before and after **dry-run**:
all physical row counts and ownership counts must match exactly. On a second
fresh isolated copy, `--apply` may be rehearsed only after the dry-run findings
are reviewed; record before/after counts, owned/unowned deltas and relationship
consistency. Every model's total row count must remain unchanged. Resolved
ownership gains must equal applied rows; unresolved/conflict rows remain
unchanged. Any unexplained mismatch blocks the gate.

## Evidence manifest

Record: UTC time; branch and commit; source backup time and checksum; source
and target instance IDs (redacted for public report); PostgreSQL versions;
restore duration; schema migration heads; command lines, exit codes and JSON
checksums; before/after per-model totals and ownership; exact category counts;
relation inconsistency count; invoice blocker counts; reviewer and disposition.
Set `rehearsal_status: PASS` only after an **actual isolated restored
production-like** database was used, all commands executed and discrepancies
reviewed. Otherwise record `OPEN` or `BLOCKED` with the missing prerequisite.
