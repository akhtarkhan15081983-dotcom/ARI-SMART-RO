# ARI SMART RO — Production Backup & Disaster Recovery Runbook

**Status:** Max-Pro hardening requirement  
**Production database:** Render Postgres `ari-smart-ro-db`  
**Region:** Singapore  
**Current reported database plan:** `0.1c-256mb`  
**Current reported disk:** 1 GB  
**High availability:** not enabled  
**Read replicas:** none

## 1. Max-Pro recovery targets

These are release requirements, not claims that the current environment already meets them.

- **Database RPO target:** <= 15 minutes after PITR availability is verified.
- **Database RTO target:** <= 2 hours for a production data-loss incident.
- **Portable backup:** at least one off-Render logical backup per day.
- **Portable backup retention target:** 30 daily backups + 12 monthly backups.
- **Restore drill:** at least monthly and before any destructive/high-risk migration.
- **Production deletion rule:** never delete the active database until a verified recovery/backup exists outside the instance being deleted.

## 2. Render recovery capabilities to verify

Render documentation states that paid Render Postgres databases receive continuous point-in-time recovery (PITR). The recovery window depends on the workspace plan (currently documented as 3 days for Hobby and 7 days for Pro+). PITR creates a new database instance, which should be validated before switching production traffic.

Render also supports on-demand logical exports retained by Render for seven days. Those exports must be downloaded or copied elsewhere for long-term retention.

**ARI gate:** Do not mark backup/recovery as PASS until the `ari-smart-ro-db` Recovery page visibly confirms PITR availability and at least one restore drill succeeds.

## 3. Required backup layers

### Layer A — Continuous PITR

1. Open Render Dashboard -> `ari-smart-ro-db` -> Recovery.
2. Confirm Point-in-Time Recovery is available.
3. Record the oldest recoverable timestamp and workspace recovery window.
4. Record verification date in the Max-Pro hardening status document.

### Layer B — Daily portable logical backup

Target implementation:

- run `pg_dump` once per day from a controlled backup job;
- use a portable PostgreSQL custom/directory backup format;
- encrypt backup storage at rest;
- upload to an off-Render object-storage bucket;
- verify upload checksum/size;
- retain 30 daily copies and 12 monthly copies;
- alert if a scheduled backup is missing or zero-sized.

Do not store long-term backups only on the same Render service/database account without an independent copy.

### Layer C — Pre-migration safety backup

Before any migration that can delete, transform or irreversibly rewrite production data:

1. create a fresh logical export;
2. confirm the export is complete;
3. capture the production database schema/migration version;
4. rehearse the migration on production-like data when risk is material;
5. deploy only after tests and rollback steps are documented.

## 4. Monthly restore drill

A backup is not considered verified until it has been restored.

1. Create an isolated recovery database; never overwrite production for a drill.
2. Restore from PITR or the chosen logical backup.
3. Run application migrations/checks against the recovered database.
4. Validate critical record counts and relationships:
   - users/employees;
   - customers;
   - attendance;
   - jobs/service/complaints;
   - rent/payments;
   - inventory;
   - employee location history.
5. Validate that the app can read the recovered data with a non-production test service.
6. Record drill date, backup timestamp, result, restore duration and anomalies.
7. Delete/suspend the temporary recovery resources after verification.

## 5. Emergency recovery procedure

### A. Suspected application crash only

Do not restore the database automatically. First determine whether the incident is application/runtime-only. A service restart should not imply database rollback.

### B. Accidental delete/bad migration/data corruption

1. Stop further destructive writes if safe to do so.
2. Record the approximate incident time in UTC and Asia/Kolkata.
3. Select a PITR timestamp immediately before the damaging operation.
4. Restore to a **new** Render database instance.
5. Validate critical data before cutover.
6. Update the API database connection only after validation.
7. Keep the old database isolated until the recovered production system is verified.
8. Produce a post-incident report and add a regression control preventing recurrence.

### C. Complete provider/database loss

1. Provision a compatible PostgreSQL version in the chosen recovery environment.
2. Restore the newest verified off-Render logical backup.
3. Apply only migrations newer than the backup after reviewing their safety.
4. Validate critical counts and business workflows.
5. Point the API to the recovered database.

## 6. Data integrity checks after restore

Minimum post-restore checks:

- no orphan customer/job/payment foreign keys;
- active employees retain correct company/role/device state;
- attendance check-in/check-out pairs remain consistent;
- payment/rent ledger totals reconcile;
- inventory quantities are non-negative where business rules require it;
- employee route points remain ordered by capture time;
- authentication/admin access works;
- media references resolve from persistent/object storage;
- API error rate and memory remain stable after cutover.

## 7. Release gate

Backup/recovery receives **PASS** only when all are true:

- PITR availability for the actual production database is verified;
- off-Render logical backup exists and is recent;
- a restore drill has succeeded;
- RPO/RTO results are recorded;
- migration rollback procedure is documented;
- the process has an owner and failure alerting.

Until then, backup/recovery remains **P0/P1 OPEN** for Max-Pro certification.
