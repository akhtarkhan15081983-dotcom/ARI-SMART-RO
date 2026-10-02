# ARI SMART RO — Corporate HRMS Blueprint

## Objective
Build HRMS as a complete employee lifecycle system, not a collection of leave/payroll screens. The system must support HR, managers, employees and auditors from manpower request / joining through active employment, performance, payroll, compliance and exit.

## 1. HR Command Center
- Active workforce, present/absent, late, half-day, overtime
- New joiners, probation due, confirmations due
- Pending joining tasks and missing documents
- Training pending/overdue/completed
- Leave approvals, payroll approvals, penalty drafts
- Appraisals due, promotion/transfer approvals
- Exits in progress and full-and-final pending
- Compliance alerts and expiring documents

## 2. Recruitment-to-Joining / Preboarding
Minimum joining packet:
- Candidate / employee personal profile
- Contact, address, DOB, gender, emergency contact
- Joining date, department, designation, job title, grade, reporting manager
- Employment type: probation / permanent / contractual / trainee
- Work location / branch
- Salary / compensation profile
- Bank details
- Aadhaar / PAN / identity records where business policy requires them
- Employee photograph
- Offer / appointment / joining records
- Temporary login credentials and first-login password reset

Workflow:
DRAFT -> HR REVIEW -> APPROVED -> EMPLOYEE CREATED -> ONBOARDING -> READY FOR DUTY

## 3. Onboarding Checklist
Required items must be independently visible and auditable:
- Personal profile completed
- Employment profile completed
- Mandatory documents received and verified
- Bank/payroll information completed
- Policies acknowledged
- Training assigned and mandatory induction completed
- Face enrollment completed/verified when role requires it
- Attendance device registration completed
- Role permissions assigned
- Employee ID card issued
- Reporting manager confirmed
- Work assets / engineer kit issued when applicable

Employee must not become READY FOR DUTY until required controls are complete or a documented HR override is approved.

## 4. Employee Master / Digital Personnel File
One employee profile must show:
- Identity and contact information
- Employment details
- Reporting hierarchy
- Salary and compensation history
- Attendance summary
- Leave history and balances
- Training and certificates
- Documents and verification status
- Performance reviews
- Promotions / transfers / salary revisions
- Disciplinary actions / penalties with approval history
- Assigned assets
- Security/device status
- ID card
- Complete audit trail

## 5. Employment Status, Probation and Confirmation
Statuses:
- Pre-joining
- Onboarding
- Probation
- Active / Confirmed
- Notice period
- Suspended (optional policy-controlled)
- Separated
- Inactive

Probation controls:
- Probation start and expected confirmation date
- Manager review due reminder
- HR review
- Extend probation with reason and revised date
- Confirm employment with effective date
- Confirmation history

## 6. Organization and Career Management
- Departments
- Designations
- Job titles
- Grades / levels
- Reporting managers
- Branch / work location
- Promotion
- Demotion
- Department transfer
- Reporting manager change
- Salary revision
- Effective-date based changes
- Draft -> Approve -> Effective workflow
- Historical snapshot for each career movement

## 7. Attendance, Shift and Time Controls
- Check-in / checkout
- Face/selfie verification
- Device binding
- Live location only during active attendance where policy permits
- Auto checkout policy
- Late attendance
- Half day
- Absence
- Overtime with approval
- Missed checkout exceptions
- Attendance correction request and approval
- Monthly attendance register

## 8. Leave Management
- Leave types and policy-driven entitlement
- Full day / half day
- Paid / unpaid handling
- Leave balance
- Apply / cancel
- Manager / HR approval workflow
- Reason and approval notes
- Leave calendar
- Holiday calendar
- Audit history

## 9. Payroll and Compensation
- Base salary
- Salary revisions with effective dates
- Attendance deductions
- Paid/unpaid leave effect
- Late / half-day / absence deductions
- Approved overtime
- Incentives
- Approved penalties / recoveries
- Other earnings and deductions
- Payroll draft -> review -> approve -> paid
- Payslip / salary register
- Month locking after approval/payment
- Audit snapshot of every calculation

## 10. Performance and Appraisal
- Review cycle and period
- Reviewer / reporting manager
- Role-specific KPIs
- Attendance score
- Service quality
- Customer feedback
- Sales / collections where applicable
- Goals and achievements
- Strengths
- Improvement plan
- Overall rating
- Employee acknowledgement
- Increment / promotion recommendation
- Performance history

## 11. Training and Certification
- Mandatory induction
- 30-day ARI training program
- Sequential lessons
- Daily progress
- Quiz / assessment
- Trainer review
- Mandatory completion before work where policy requires
- Overdue alerts
- Certificate issue/revoke/verification
- Refresher / recertification support

## 12. Document and Compliance Management
Suggested document types:
- Aadhaar / identity
- PAN
- Address proof
- Photograph
- Bank proof
- Education / technical certificates
- Driving licence where role requires
- Police verification / background check where company policy requires
- Signed appointment / policy acknowledgements

Each document should support:
- Missing / uploaded / verified / rejected / expired status
- Uploaded date
- Verified by / verified date
- Expiry date where applicable
- Rejection / correction reason
- Reminder before expiry

## 13. Disciplinary / Penalty Controls
Penalties must never be silently deducted.
Workflow:
DRAFT -> REVIEW -> APPROVED / CANCELLED -> PAYROLL EFFECT

Store:
- Reason
- Evidence / note
- Amount or consequence
- Created by
- Approved by
- Dates and audit trail

## 14. Asset / Kit Management
For applicable employees:
- Phone/device
- SIM
- ID card
- Engineer bag
- Tools
- Spare inventory / issued material
- Uniform
- Other company assets

Track issue date, condition, custodian, return, loss/damage and clearance.

## 15. Employee Separation / Exit Management
Workflow:
RESIGNATION / TERMINATION INITIATED -> NOTICE PERIOD -> HANDOVER -> CLEARANCE -> F&F -> ACCESS DISABLED -> SEPARATED

Controls:
- Separation type
- Resignation / termination date
- Notice period
- Last working day
- Handover owner
- Pending jobs / customers / collections
- Asset return
- Attendance closure
- Payroll / incentive / deduction closure
- Full-and-final settlement
- Login/device/access revocation
- Exit interview / reason
- Relieving / experience record status

Employee history must remain preserved after exit; do not delete operational history.

## 16. Employee Self Service
Employees should be able to see only their permitted data:
- Profile
- ID card
- Attendance
- Leave and balance
- Payslip / salary status
- Training
- Certificates
- Assigned work assets
- Performance acknowledgement
- Personal document status
- Requests requiring HR approval

## 17. HR / Manager Role Access
Example separation of duties:
- ADMIN: full control
- HR: joining, employee master, documents, probation, leave, payroll preparation, separation
- MANAGER: team attendance, leave recommendation, performance, probation feedback
- PAYROLL/ACCOUNTS: payroll review/payment, limited salary access
- TRAINER: assigned training administration
- EMPLOYEE: self-service only

Sensitive fields such as salary, bank details, identity documents and disciplinary records require restricted permissions.

## 18. Audit, Safety and Data Governance
Every critical mutation should record:
- Who performed it
- When
- Old value
- New value
- Reason
- Approval identity where required

Never permanently delete an employee with linked operational/payroll/customer history. Deactivate/separate while preserving history.

## 19. Reporting
Required HR reports:
- Employee master register
- New joiners
- Probation / confirmation due
- Active / inactive / separated staff
- Attendance register
- Leave register
- Overtime
- Payroll register
- Incentives / deductions
- Training compliance
- Document compliance / expiries
- Performance/appraisal
- Promotion / transfer / salary revision history
- Separation / attrition
- Asset clearance

## 20. UI / UX Standard
Desktop:
- Left navigation / section navigation for major HR domains
- Compact executive KPI row
- Action queue
- Employee table with search/filter/saved views
- Status chips and due-date alerts
- No oversized empty cards
- Drill-down employee profile instead of long mixed page

Mobile:
- Responsive cards
- Bottom sheets / stepper for actions
- Employee self-service first
- Admin workflows remain usable without horizontal overflow

## Recommended implementation order
P0 — Corporate foundation
1. HR Command Center redesign
2. New Joining Wizard
3. Employee Master / Digital Personnel File
4. Onboarding checklist and Ready-for-Duty gate
5. Probation / confirmation

P1 — Core operations
6. Attendance / leave integration
7. Payroll lifecycle
8. Documents/compliance
9. Performance/appraisal
10. Training integration

P2 — Lifecycle completion
11. Career / promotion / transfer
12. Asset management
13. Exit / clearance / full-and-final
14. Reports and audit views
15. HR policy configuration

## Acceptance standard
The HRMS is considered company-standard only when a new employee can be processed from pre-joining through onboarding, active employment, payroll, attendance, training, appraisal, career changes and final separation without relying on disconnected manual records for core HR lifecycle control.
