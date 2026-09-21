from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


DAYS = [
    ("Respect & first impression / सम्मान और पहली छाप", "Greeting, body language, listening and ownership.", "नमस्कार, सही body language, बिना टोके सुनना और जिम्मेदारी लेना।"),
    ("Active listening / ध्यान से सुनना", "Use open questions, confirm facts and never interrupt.", "खुले सवाल पूछें, तथ्य दोहराकर पुष्टि करें और ग्राहक को बीच में न रोकें।"),
    ("Professional language / पेशेवर भाषा", "Replace blame and casual language with calm, clear service language.", "दोष देने वाली भाषा के बजाय शांत, स्पष्ट और सम्मानजनक शब्दों का अभ्यास करें।"),
    ("LAST de-escalation / LAST से गुस्सा शांत करना", "Listen, Acknowledge, Solve, Thank.", "Listen, Acknowledge, Solve, Thank को role-play में लागू करें।"),
    ("Handling repeat complaints / बार-बार शिकायत", "Review history first and acknowledge repeated inconvenience.", "पुराना रिकॉर्ड पहले देखें और बार-बार हुई परेशानी को स्वीकार करें।"),
    ("Service recovery / शिकायत से भरोसा", "Own the next step, test the solution and close transparently.", "अगला कदम अपनी जिम्मेदारी लें, समाधान test करें और साफ तरीके से close करें।"),
    ("Customer PR / ग्राहक संबंध", "Build trust through punctuality, updates and kept promises.", "समय, update और निभाए गए वादों से professional PR बनाएं।"),
    ("Phone etiquette / फोन शिष्टाचार", "Open, verify, explain purpose, listen and close every call professionally.", "हर कॉल को परिचय, सत्यापन, उद्देश्य, सुनने और साफ closing के साथ करें।"),
    ("WhatsApp & digital etiquette / डिजिटल शिष्टाचार", "Use approved language, protect privacy and avoid unnecessary messages.", "स्वीकृत भाषा प्रयोग करें, privacy रखें और अनावश्यक message न भेजें।"),
    ("Appointment discipline / समय और appointment", "Confirm visits, communicate delays early and never make false ETA promises.", "visit confirm करें, delay पहले बताएं और गलत समय का वादा न करें।"),
    ("Home-visit etiquette / घर पर सेवा शिष्टाचार", "Ask permission, protect the home, keep tools organized and leave clean.", "अनुमति लें, घर का सम्मान करें, tools व्यवस्थित रखें और जगह साफ छोड़ें।"),
    ("Safety & boundaries / सुरक्षा और मर्यादा", "Recognize unsafe situations and escalate without arguing.", "असुरक्षित स्थिति पहचानें, बहस न करें और Manager/Admin को escalate करें।"),
    ("Privacy & confidentiality / गोपनीयता", "Protect phone, address, photos, payments and personal information.", "फोन, पता, फोटो, payment और निजी जानकारी की सुरक्षा करें।"),
    ("Ethics & truthful records / नैतिकता और सही रिकॉर्ड", "Never falsify attendance, location, photos, parts or job completion.", "attendance, location, photo, part या job completion का झूठा रिकॉर्ड न बनाएं।"),
    ("RO product basics / RO उत्पाद की बुनियाद", "Explain basic RO stages and common customer questions in simple language.", "RO के basic stages और आम सवाल ग्राहक को आसान भाषा में समझाएं।"),
    ("TDS explanation / TDS समझाना", "Explain input/output TDS without making medical claims.", "input/output TDS समझाएं, बिना किसी गलत medical claim के।"),
    ("Preventive maintenance / preventive maintenance", "Teach customers simple approved care and maintenance habits.", "ग्राहक को आसान और approved care तथा maintenance समझाएं।"),
    ("Diagnosing before replacing / part बदलने से पहले जाँच", "Follow diagnosis, evidence and authorization before replacing parts.", "part बदलने से पहले diagnosis, evidence और approval का पालन करें।"),
    ("Parts & inventory discipline / parts और inventory", "Scan, account for and document every physical part correctly.", "हर physical part को सही scan, account और document करें।"),
    ("Installation excellence / installation excellence", "Check site, fitment, leakage, TDS, testing and customer handover.", "site, fitment, leakage, TDS, testing और customer handover checklist पूरा करें।"),
    ("Service closure / service closure", "Close only after real work, evidence, explanation and customer verification.", "असली काम, evidence, explanation और customer verification के बाद ही close करें।"),
    ("OTP & signature integrity / OTP और signature", "Use OTP/signature only for the real customer workflow.", "OTP/signature केवल वास्तविक customer workflow में लें।"),
    ("Payment conversation / payment बातचीत", "Explain approved dues and offers; never pressure or invent discounts.", "approved dues/offer समझाएं; दबाव या unofficial discount न दें।"),
    ("Handling price objections / price objection", "Use value, policy and options instead of argument.", "बहस के बजाय value, policy और approved options बताएं।"),
    ("Referral request / referral माँगना", "Ask only after satisfaction and never pressure the customer.", "संतुष्टि के बाद विनम्रता से referral माँगें, दबाव न बनाएं।"),
    ("Difficult customer role-play / कठिन ग्राहक role-play", "Practice anger, delay, repeat complaint and policy-boundary scenarios.", "गुस्सा, delay, repeat complaint और policy-boundary scenario का role-play करें।"),
    ("Communication under pressure / दबाव में संवाद", "Stay calm, summarize facts and choose the next safe action.", "शांत रहें, तथ्य summarize करें और अगला सुरक्षित कदम चुनें।"),
    ("Team escalation / टीम escalation", "Escalate with facts, evidence, urgency and a clear requested action.", "तथ्य, evidence, urgency और clear action के साथ escalation करें।"),
    ("Personal improvement coaching / व्यक्तिगत सुधार", "Review behaviour, communication and knowledge gaps with the trainer.", "trainer के साथ behaviour, communication और knowledge की कमी review करें।"),
    ("Final simulation & action plan / अंतिम simulation", "Run a full customer journey simulation and create a 30-day improvement plan.", "पूरी customer journey simulation करें और आगे का improvement plan बनाएं।"),
]


def seed_corporate_training(apps, schema_editor):
    Course = apps.get_model("employees", "TrainingCourse")
    Lesson = apps.get_model("employees", "TrainingLesson")
    course = Course.objects.filter(slug="customer-respect-relationship-excellence").first()
    if not course:
        return
    course.title = "30-Day Customer Service & Professional Excellence / 30-दिवसीय ग्राहक सेवा प्रशिक्षण"
    course.description = (
        "Corporate 30-day bilingual programme. Minimum planned learning time is 60 minutes per day. "
        "Admin can act as Trainer, conduct role-play, score behaviour/communication/knowledge, record gaps "
        "and prescribe coaching actions. / 30 दिन का corporate bilingual programme; हर दिन कम से कम 60 मिनट। "
        "Admin Trainer role-play, व्यवहार/संवाद/ज्ञान score, कमी और सुधार की कार्ययोजना दर्ज कर सकता है।"
    )
    course.due_days = 30
    course.grace_days = 2
    course.save(update_fields=["title", "description", "due_days", "grace_days"])

    for day, (title, en, hi) in enumerate(DAYS, start=1):
        existing = Lesson.objects.filter(course=course, order=day).first()
        video = getattr(existing, "video_asset", "") if existing else ""
        Lesson.objects.update_or_create(
            course=course,
            order=day,
            defaults={
                "day_number": day,
                "duration_minutes": 60,
                "title": f"Day {day}: {title}",
                "content": (
                    f"ENGLISH\n{en}\n\nHINDI / हिन्दी\n{hi}\n\n"
                    "Daily structure / दैनिक संरचना: 15 min concept + 20 min trainer demonstration/role-play + "
                    "20 min employee practice + 5 min feedback and action note."
                ),
                "key_takeaway": "60-minute guided practice + trainer feedback / 60 मिनट अभ्यास और trainer feedback",
                "trainer_script": (
                    "Trainer: explain the concept in Hindi first, demonstrate one good and one poor example, "
                    "run a realistic ARI SMART RO customer role-play, then ask the employee to repeat the scenario. "
                    "Observe tone, listening, clarity, ownership and policy compliance."
                ),
                "practice_task": (
                    "Employee must complete a practical role-play. Trainer records one strength, one gap and one "
                    "specific improvement action before the day is considered coached."
                ),
                "video_asset": video,
            },
        )


class Migration(migrations.Migration):
    dependencies = [
        ("employees", "0016_bilingual_training_videos"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="traininglesson",
            name="day_number",
            field=models.PositiveSmallIntegerField(default=1),
        ),
        migrations.AddField(
            model_name="traininglesson",
            name="duration_minutes",
            field=models.PositiveSmallIntegerField(default=60),
        ),
        migrations.AddField(
            model_name="traininglesson",
            name="practice_task",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="traininglesson",
            name="trainer_script",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.CreateModel(
            name="TrainingTrainerReview",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("behaviour_score", models.PositiveSmallIntegerField(default=3)),
                ("communication_score", models.PositiveSmallIntegerField(default=3)),
                ("knowledge_score", models.PositiveSmallIntegerField(default=3)),
                ("strengths", models.TextField(blank=True, default="")),
                ("gaps", models.TextField(blank=True, default="")),
                ("coaching_action", models.TextField(blank=True, default="")),
                ("notes", models.TextField(blank=True, default="")),
                ("reviewed_at", models.DateTimeField(auto_now=True)),
                ("assignment", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="trainer_reviews", to="employees.employeetrainingassignment")),
                ("lesson", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="trainer_reviews", to="employees.traininglesson")),
                ("trainer", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="training_reviews_given", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["lesson__day_number", "lesson__order"]},
        ),
        migrations.AddConstraint(
            model_name="trainingtrainerreview",
            constraint=models.UniqueConstraint(fields=("assignment", "lesson"), name="unique_training_trainer_review"),
        ),
        migrations.RunPython(seed_corporate_training, migrations.RunPython.noop),
    ]
