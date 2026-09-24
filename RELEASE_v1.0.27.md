# ARI SMART RO v1.0.27 — Training Academy Builder

## Major training upgrade

- Replaces short 5–10 line lessons with a substantially expanded 30-day professional curriculum.
- Every day includes a learning objective, detailed concepts, a realistic ARI SMART RO scenario, common mistakes, a 60-minute learning plan, practical role-play/task, self-check and trainer coaching script.
- Final seeded test now covers all 30 training topics instead of only a small question set.

## Admin Training Builder

Admin can now manage training inside the app without changing code:

- Create a new training course as Draft.
- Choose audience: All, Engineer, Calling, Office or Manager.
- Set passing score, due days, grace days and compliance penalty draft amount.
- Add or edit detailed lessons at any time before/after publishing.
- Add optional external training video and resource/document links.
- Add or edit four-option test questions with correct answer and explanation.
- Configure certificate enabled/disabled, certificate validity, required trainer reviews and minimum trainer average.
- Publish only after at least one lesson and one test question exist.
- Assign a published course to eligible employees.
- Existing assigned-course history is protected from destructive lesson/question deletion.

## Certificate rules

- Certificate eligibility is now course-specific.
- A course can certify from lesson completion + passing test alone.
- Or Admin can require trainer reviews and a minimum trainer average.
- Certificate validity days are configurable per course.
- If trainer review is not required, final certificate score is based on the quiz score.
- If trainer review is required, the existing quiz + trainer weighted score remains.

## Security and SaaS isolation

- Training dashboards and assignments are scoped to the Admin's company workspace.
- Trainer reviews, certificate issue and certificate revoke are restricted to the same company workspace.
- Company-specific courses avoid cross-tenant training leakage.

## App UX

- Admin sees a Training Builder icon from Employee Training.
- Training material is selectable/readable and supports external video/resource links.
- Course UI now shows actual training-plan days/minutes instead of assuming every course is 30 days.
- Certificate card only appears when the course has certification enabled.

## Automated tests

- Draft course creation.
- Minimum meaningful lesson-content validation.
- Publish gate requiring lesson + question.
- Course assignment.
- Employee lesson completion + test pass.
- Test-only certificate issuance.
- Existing trainer-reviewed certificate behavior retained.

Version: 1.0.27+27
