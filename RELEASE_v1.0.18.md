# ARI SMART RO v1.0.18

## Trusted Engineer & Professional Employee Onboarding
- Corporate employee joining form with designation, job title, department, grade, reporting manager, salary, address and emergency contact.
- Existing automatic Employee ID retained.
- Secure non-sequential employee verification code for every employee.
- Professional Digital Employee ID card with photo, official Employee ID, company, designation/job title, QR payload, validity and active/verified state.
- Joining readiness checklist: profile, face/device security and mandatory training.
- Existing employees are preserved and backfilled with verification codes and ID-card validity.
- Admin Employee Management shows onboarding status and can view each employee digital ID.
- Customer My RO shows the exact engineer assigned to the active job: photo, name, Employee ID, role, job number, visit status and verification code.
- Customer notification alerts include assigned engineer name and Employee ID.
- Customer must match photo/ID before sharing service OTP.
- Customer-safe identity payload never exposes employee salary, phone, home address or HR records.
- Customer assigned-engineer access is scoped to the customer's own active job.
- Customer OTP mobile endpoint aligned with backend route.

## Security
- Verification codes are random and unique.
- Arbitrary private HR data is never returned by employee verification endpoints.
- Unassigned customers receive no engineer identity.

- Admin can immediately see joining readiness and open the official digital ID from Employee Management.
