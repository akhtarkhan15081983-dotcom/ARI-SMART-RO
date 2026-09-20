from decimal import Decimal
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
from django.utils.text import slugify
from django.utils import timezone
from datetime import timedelta


def seed_training(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    TrainingCourse = apps.get_model("employees", "TrainingCourse")
    TrainingLesson = apps.get_model("employees", "TrainingLesson")
    TrainingQuestion = apps.get_model("employees", "TrainingQuestion")
    EmployeeProfile = apps.get_model("employees", "EmployeeProfile")
    Assignment = apps.get_model("employees", "EmployeeTrainingAssignment")

    creator = User.objects.filter(role="ADMIN", is_active=True).order_by("id").first()
    if creator is None:
        return

    course, _ = TrainingCourse.objects.get_or_create(
        slug="customer-respect-relationship-excellence",
        defaults={
            "title": "Customer Respect & Relationship Excellence",
            "description": (
                "Mandatory practical training for respectful communication, de-escalation, "
                "service recovery and long-term customer relationship building."
            ),
            "audience": "ALL",
            "is_mandatory": True,
            "passing_score": 80,
            "due_days": 7,
            "grace_days": 2,
            "penalty_amount": Decimal("100.00"),
            "is_active": True,
            "created_by": creator,
        },
    )

    lessons = [
        (
            1,
            "Respect first: tone, listening and ownership",
            """Every customer interaction begins with respect. Your job is not only to repair an RO, collect rent or close a service request; your job is to protect the customer's trust in ARI SMART RO.

1. Greet the customer calmly and use their name when appropriate.
2. Let the customer finish speaking before you answer.
3. Do not argue, interrupt, mock or blame.
4. Acknowledge the problem: “I understand why this is frustrating.”
5. Take ownership of the next step even if another team caused the issue.
6. Give a realistic next action and time commitment. Never promise what you cannot deliver.
7. Before leaving, confirm what was done and what happens next.

Use calm, short sentences. A respectful tone is more important than proving who is right.""",
            "Respect + listening + ownership reduces conflict before technical discussion starts.",
        ),
        (
            2,
            "Handling an angry or rude customer safely",
            """When a customer is angry, do not mirror their anger.

Use the L-A-S-T method:
L — Listen without interruption.
A — Acknowledge the emotion and inconvenience.
S — Solve what you can now; explain the next step clearly.
T — Thank the customer for allowing you to fix the issue.

Example:
Customer: “Your company is useless. I have complained three times.”
Employee: “I understand why you are upset. I can see this has taken too long. I will first check the current issue, then I’ll tell you exactly what I can resolve today and what needs escalation.”

Never say:
• “It is not my problem.”
• “Calm down.”
• “You are wrong.”
• “I cannot do anything.”
• “Talk to the office.”

If the customer becomes abusive, threatening or unsafe, stay professional, create distance, end the visit politely and escalate to Admin/Manager. Safety comes before service.""",
            "Do not fight the customer; de-escalate, set boundaries and escalate unsafe behavior.",
        ),
        (
            3,
            "Service recovery: turn complaints into trust",
            """A complaint is a chance to repair trust.

Service recovery steps:
1. Confirm the exact issue in the customer’s words.
2. Check previous service/complaint history in the app before asking repeated questions.
3. Explain the cause only after you understand it.
4. Fix the immediate problem where possible.
5. If a part or approval is needed, create/confirm the request in the app.
6. Show the customer the completed work and test the RO together.
7. Ask: “Is there anything else related to this RO that you want me to check before I leave?”
8. Record truthful notes and photos. Never mark work complete before it is complete.

If ARI made a mistake, do not hide it. A clear apology and a correct solution builds more trust than excuses.""",
            "Fast, transparent service recovery can strengthen the customer relationship.",
        ),
        (
            4,
            "Build your PR with the customer",
            """PR means professional relationship—not personal pressure.

Good customer PR:
• Remember the customer’s preferred communication style.
• Be punctual and call before arriving when possible.
• Keep promises and update the customer if a delay occurs.
• Explain maintenance in simple language.
• Keep the work area clean.
• Ask permission before moving household items.
• Never demand tips, gifts, referrals or personal favors.
• Never misuse a customer’s phone number or contact them for unrelated personal reasons.
• After service, politely remind them how to contact ARI for future support.
• If the customer is satisfied, you may ask for feedback or a referral without pressure.

A strong relationship comes from consistency, honesty and useful service—not flattery or repeated calls.""",
            "Professional PR is earned through reliability and boundaries.",
        ),
        (
            5,
            "Communication scripts for difficult situations",
            """Use these patterns and adapt naturally:

Delay:
“I’m sorry for the delay. I have checked the status. The next step is ____. I will update you by ____.”

Repeat complaint:
“I can see this issue has already been reported. I won’t make you repeat everything. I’ll review the previous notes first and then confirm today’s action.”

Customer demands something outside policy:
“I understand what you are asking. I’m not authorized to promise that, but I can escalate it to Admin/Manager right now and record your request correctly.”

Customer insults you:
“I want to help you and I’ll stay respectful. I request that we speak respectfully so I can resolve the issue. If the situation remains unsafe, I’ll need to escalate and leave.”

Price/rent concern:
“I’ll show you the current amount and any active offer in the app. I won’t quote an unofficial discount.”

Closing:
“Today we completed ____. Please check the RO once. If this issue returns, report it through ARI SMART RO so the full history stays recorded.”""",
            "Use respectful scripts, never unofficial promises or hidden discounts.",
        ),
        (
            6,
            "Ethics, privacy and reputation",
            """Customer trust can be lost in one careless moment.

Never:
• Share customer address, phone number, payment details or photos outside work.
• Take personal photos/videos inside a customer’s home.
• Post customer information on social media.
• Collect cash without recording the correct transaction.
• Offer unofficial discounts or side deals.
• Use abusive, discriminatory or sexual language.
• Pressure a customer to change a complaint or rating.
• Falsify service notes, location, attendance or completion evidence.

If you make a mistake, report it quickly. Hiding a mistake creates a bigger problem.

Your personal reputation and ARI SMART RO’s reputation are connected in every visit and call.""",
            "Professional conduct, privacy and accurate records are mandatory.",
        ),
    ]
    for order, title, body, takeaway in lessons:
        TrainingLesson.objects.update_or_create(
            course=course,
            order=order,
            defaults={"title": title, "content": body, "key_takeaway": takeaway},
        )

    questions = [
        (1, "An angry customer says this is their third complaint. What should you do first?",
         "Tell them another team caused it", "Let them finish and acknowledge the frustration",
         "Ask them to call the office", "Tell them to calm down", "B",
         "Listening and acknowledgement should come before explanation."),
        (2, "Which response is best when you cannot authorize a requested discount?",
         "Promise it and ask Admin later", "Say it is not your problem",
         "Explain you are not authorized and escalate the request", "Give a cash-only discount", "C",
         "Only approved offers and authorized decisions should be promised."),
        (3, "What is the correct way to build customer PR?",
         "Frequent personal calls", "Reliability, respectful communication and useful service",
         "Asking for gifts", "Adding the customer on personal social media", "B",
         "Professional trust grows from consistent service and boundaries."),
        (4, "If a customer becomes threatening or the visit feels unsafe, what should you do?",
         "Argue until they listen", "Continue work no matter what",
         "Create distance, end politely and escalate", "Record them secretly", "C",
         "Safety comes before service."),
        (5, "When should a job be marked completed?",
         "When you reach the customer", "Before testing, to save time",
         "Only after the actual work is complete and verified", "When the customer stops complaining", "C",
         "Records must reflect reality."),
        (6, "What should you say about an unexpected delay?",
         "Nothing until the customer calls", "Give a realistic update and next commitment",
         "Blame traffic or another employee", "Promise an impossible time", "B",
         "Proactive, realistic updates protect trust."),
        (7, "Which action violates customer privacy?",
         "Recording service notes in the app", "Using the address to reach the assigned job",
         "Sharing the customer phone number outside work", "Checking service history", "C",
         "Customer information is only for authorized business use."),
        (8, "A repeat complaint is opened. What is the best approach?",
         "Make the customer explain everything again", "Review previous notes first",
         "Close the complaint", "Tell them to buy a new RO", "B",
         "Using history shows ownership and prevents frustration."),
        (9, "Which phrase is most professional after a customer insults you?",
         "You are also rude", "Calm down", "I want to help; please let us speak respectfully",
         "I am leaving and will never return", "C",
         "Set a respectful boundary without escalating."),
        (10, "What is the LAST method?",
         "Listen, Acknowledge, Solve, Thank", "Leave, Argue, Stop, Talk",
         "Listen, Avoid, Sell, Transfer", "Lead, Answer, Speak, Test", "A",
         "LAST is a simple de-escalation framework."),
    ]
    for order, question, a, b, c, d, correct, explanation in questions:
        TrainingQuestion.objects.update_or_create(
            course=course,
            order=order,
            defaults={
                "question": question,
                "option_a": a,
                "option_b": b,
                "option_c": c,
                "option_d": d,
                "correct_option": correct,
                "explanation": explanation,
            },
        )

    today = timezone.localdate()
    for employee in EmployeeProfile.objects.filter(is_active=True):
        Assignment.objects.get_or_create(
            employee=employee,
            course=course,
            defaults={
                "due_date": today + timedelta(days=course.due_days),
                "grace_until": today + timedelta(days=course.due_days + course.grace_days),
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ("employees", "0013_performance_review"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="TrainingCourse",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=180)),
                ("slug", models.SlugField(max_length=180, unique=True)),
                ("description", models.TextField(blank=True, default="")),
                ("audience", models.CharField(choices=[("ALL", "All Employees"), ("ENGINEER", "Engineer"), ("MANAGER", "Manager"), ("OFFICE", "Office Staff"), ("CALLING", "Calling Staff")], default="ALL", max_length=20)),
                ("is_mandatory", models.BooleanField(default=True)),
                ("passing_score", models.PositiveIntegerField(default=80)),
                ("due_days", models.PositiveIntegerField(default=7)),
                ("grace_days", models.PositiveIntegerField(default=2)),
                ("penalty_amount", models.DecimalField(decimal_places=2, default=100, max_digits=10)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="created_training_courses", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["title"]},
        ),
        migrations.CreateModel(
            name="TrainingLesson",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("order", models.PositiveIntegerField(default=1)),
                ("title", models.CharField(max_length=180)),
                ("content", models.TextField()),
                ("key_takeaway", models.CharField(blank=True, default="", max_length=300)),
                ("course", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="lessons", to="employees.trainingcourse")),
            ],
            options={"ordering": ["course", "order", "id"]},
        ),
        migrations.CreateModel(
            name="TrainingQuestion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("order", models.PositiveIntegerField(default=1)),
                ("question", models.CharField(max_length=500)),
                ("option_a", models.CharField(max_length=300)),
                ("option_b", models.CharField(max_length=300)),
                ("option_c", models.CharField(max_length=300)),
                ("option_d", models.CharField(max_length=300)),
                ("correct_option", models.CharField(choices=[("A", "A"), ("B", "B"), ("C", "C"), ("D", "D")], max_length=1)),
                ("explanation", models.CharField(blank=True, default="", max_length=500)),
                ("course", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="questions", to="employees.trainingcourse")),
            ],
            options={"ordering": ["course", "order", "id"]},
        ),
        migrations.CreateModel(
            name="EmployeeTrainingAssignment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("assigned_at", models.DateTimeField(auto_now_add=True)),
                ("due_date", models.DateField()),
                ("grace_until", models.DateField()),
                ("status", models.CharField(choices=[("PENDING", "Pending"), ("IN_PROGRESS", "In Progress"), ("COMPLETED", "Completed"), ("OVERDUE", "Overdue")], default="PENDING", max_length=16)),
                ("lessons_completed", models.JSONField(blank=True, default=list)),
                ("quiz_score", models.PositiveIntegerField(default=0)),
                ("attempts", models.PositiveIntegerField(default=0)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("compliance_strike", models.BooleanField(default=False)),
                ("penalty_created", models.BooleanField(default=False)),
                ("course", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="assignments", to="employees.trainingcourse")),
                ("employee", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="training_assignments", to="employees.employeeprofile")),
                ("penalty", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="training_assignments", to="employees.employeepenalty")),
            ],
            options={"ordering": ["status", "due_date", "-assigned_at"]},
        ),
        migrations.AddConstraint(
            model_name="traininglesson",
            constraint=models.UniqueConstraint(fields=("course", "order"), name="unique_training_lesson_order"),
        ),
        migrations.AddConstraint(
            model_name="employeetrainingassignment",
            constraint=models.UniqueConstraint(fields=("employee", "course"), name="unique_employee_training_course"),
        ),
        migrations.RunPython(seed_training, migrations.RunPython.noop),
    ]
