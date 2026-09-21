# ARI SMART RO v1.0.28 — Employee Work Hours, Overtime & Daily Activity

## 8-hour working-hours control
- Regular shift is calculated from the employee's actual check-in time.
- The server caps the regular shift at the configured daily work hours (8 hours by current HR policy).
- At the 8-hour point, effective checkout is recorded at the exact shift-end time.
- If the app is open, Attendance refreshes automatically at shift end.
- If the phone is closed/offline, the server reconciles the attendance to the exact 8-hour checkout time on the next sync/read/payroll/report operation.
- Manual early checkout records the actual regular hours worked.

## Payroll based on actual hours
- Regular working hours are tracked separately from overtime.
- Short regular hours generate an hourly short-hours deduction.
- Existing late, half-day, absence and approved penalty rules remain.
- Overtime pay uses only Admin-approved overtime actually worked.
- Unapproved extra time does not create overtime salary.
- Payroll screen and Excel salary register show Short Hours, Short-hours Deduction, Approved OT Hours and Approved OT Amount.

## Admin-approved overtime
Employee flow:
1. Regular 8-hour shift completes and auto-checkout applies.
2. Employee submits overtime hours + reason.
3. Admin approves/rejects and can approve fewer hours than requested.
4. Employee starts approved overtime after the regular shift is complete.
5. Employee can stop early, or the session auto-stops at the approved limit.
6. Actual approved overtime is recorded for payroll.

Admin:
- Attendance Selfie Review now links to Overtime Approvals.
- Pending/Approved/Completed/Rejected views.
- Employee, date, reason, requested hours, approved hours, regular hours and OT worked are visible.
- Approval/rejection and audit note are recorded.

## Employee-wise business reports
Reports now show each employee's selected-period activity:
- regular working hours
- approved overtime hours
- jobs completed
- complaints resolved
- services completed
- installations completed
- calls logged
- rent payments and rent collected
- detailed activity timeline

For Daily period this becomes a direct “who did what today” view.
Excel adds:
- Employee Daily Activity
- Employee Activity Detail

## Tests
Automated coverage includes:
- exact 8-hour auto-checkout
- overtime blocked before Admin approval
- approved overtime start/accounting
- short-hours salary deduction
- unapproved time not paid as overtime
- employee-wise business activity reporting and Excel sheets

Version: 1.0.28+28
