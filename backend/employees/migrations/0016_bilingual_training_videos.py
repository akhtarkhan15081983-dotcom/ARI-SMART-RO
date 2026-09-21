from django.db import migrations, models


LESSONS = [
    (1, "Respect first / सम्मान सबसे पहले", """ENGLISH\nEvery customer interaction starts with respect. Greet calmly, listen without interruption, acknowledge the problem, take ownership of the next step, and give only a realistic commitment. Before leaving, explain what was completed and what happens next.\n\nहिन्दी\nहर ग्राहक से बातचीत सम्मान से शुरू करें। शांत होकर नमस्कार करें, ग्राहक की बात बिना टोके पूरी सुनें, समस्या को स्वीकार करें और अगले कदम की जिम्मेदारी लें। केवल वही समय या समाधान बताएं जो वास्तव में पूरा कर सकें। जाने से पहले साफ बताएं कि आज क्या काम हुआ और आगे क्या होगा।\n\nकहें: “मैं आपकी परेशानी समझता हूँ। पहले मैं पूरी समस्या देख लेता हूँ, फिर आपको सही अगला कदम बताऊँगा।”\nन कहें: “यह मेरा काम नहीं है” या “आप गलत हैं”।""", "Respect, listening and ownership reduce conflict. / सम्मान, सुनना और जिम्मेदारी विवाद कम करते हैं।", "assets/training/respect_first_hi.mp4"),
    (2, "Angry customer & LAST / नाराज़ ग्राहक और LAST", """ENGLISH\nUse LAST: Listen, Acknowledge, Solve, Thank. Never mirror the customer's anger. Set a respectful boundary and leave safely if there is abuse or danger.\n\nहिन्दी\nLAST तरीका अपनाएँ:\nL — Listen: बिना टोके पूरी बात सुनें।\nA — Acknowledge: भावना और परेशानी स्वीकार करें।\nS — Solve: जो अभी हो सकता है करें और अगला कदम साफ बताएं।\nT — Thank: समाधान का मौका देने के लिए धन्यवाद कहें।\n\nउदाहरण: “मैं समझ सकता हूँ कि बार-बार शिकायत के बाद आप नाराज़ हैं। मैं पहले रिकॉर्ड और RO जाँचता हूँ, फिर आज का सही समाधान बताता हूँ।”\nयदि ग्राहक धमकी दे या माहौल असुरक्षित हो, बहस न करें; दूरी बनाएं, विनम्रता से निकलें और Manager/Admin को सूचित करें।""", "De-escalate; do not argue. / बहस नहीं—स्थिति को शांत करें।", "assets/training/last_method_hi.mp4"),
    (3, "Service recovery / शिकायत से भरोसा", """ENGLISH\nConfirm the issue in the customer's words, review previous history, fix what is possible, explain approvals or parts honestly, test the RO with the customer, and record truthful notes.\n\nहिन्दी\nग्राहक की भाषा में समस्या दोहराकर पुष्टि करें। ऐप में पुरानी शिकायतें देखें ताकि ग्राहक को सब दोबारा न बताना पड़े। जो काम तुरंत हो सकता है करें; part या approval चाहिए तो साफ बताएं। ग्राहक के सामने RO test करें और केवल असली काम पूरा होने पर ही job complete करें।\n\nअंत में पूछें: “RO से जुड़ी कोई और बात है जिसे मैं जाने से पहले जाँच दूँ?”\nARI से गलती हुई हो तो बहाना नहीं—साफ माफी और सही समाधान दें।""", "Transparent recovery can strengthen trust. / साफ समाधान भरोसा मजबूत करता है।", "assets/training/service_recovery_hi.mp4"),
    (4, "Professional customer PR / पेशेवर ग्राहक संबंध", """ENGLISH\nProfessional PR is earned through punctuality, updates, cleanliness, simple explanations, privacy and kept promises—not personal pressure.\n\nहिन्दी\nCustomer PR का मतलब निजी दबाव नहीं, बल्कि पेशेवर रिश्ता है। समय पर पहुँचें, संभव हो तो आने से पहले फोन करें, देरी हो तो खुद update दें, काम की जगह साफ रखें और maintenance आसान भाषा में समझाएँ। सामान हटाने से पहले अनुमति लें।\n\nTip, gift, personal favour या referral के लिए दबाव न दें। ग्राहक के नंबर का निजी उपयोग न करें। संतुष्ट ग्राहक से feedback या referral विनम्रता से माँग सकते हैं, लेकिन दबाव नहीं डाल सकते।""", "Reliability and boundaries create lasting PR. / भरोसेमंदी और मर्यादा से PR बनता है।", "assets/training/customer_pr_hi.mp4"),
    (5, "Difficult-situation scripts / कठिन बातचीत के वाक्य", """ENGLISH + हिन्दी PRACTICE\nDelay: “देरी के लिए क्षमा करें। अगला कदम ____ है और मैं आपको ____ बजे तक update दूँगा।”\nRepeat complaint: “मैं पिछला रिकॉर्ड पहले देखूँगा; आपको सब दोबारा बताने की जरूरत नहीं है।”\nOutside policy: “मैं बिना अनुमति यह वादा नहीं कर सकता, लेकिन आपकी request अभी Manager/Admin तक दर्ज कर रहा हूँ।”\nInsult: “मैं आपकी मदद करना चाहता हूँ और सम्मान से बात करूँगा। कृपया हम दोनों सम्मान से बात करें ताकि समाधान हो सके।”\nPrice: “मैं ऐप में current amount और approved offer दिखाता हूँ; unofficial discount quote नहीं करूँगा।”\nClosing: “आज हमने ____ पूरा किया। कृपया RO check कर लें; समस्या लौटे तो ARI SMART RO में report करें।”""", "Use calm scripts and never make unofficial promises. / शांत भाषा और केवल अधिकृत वादा।", ""),
    (6, "Ethics, privacy & reputation / नैतिकता और गोपनीयता", """ENGLISH\nProtect customer data, money and dignity. Never falsify attendance, location, service evidence or completion. Report mistakes quickly.\n\nहिन्दी\nग्राहक का पता, फोन, payment detail या photo काम के बाहर share न करें। घर के अंदर निजी photo/video न लें। cash payment को सही transaction के बिना न रखें। unofficial deal, अपमानजनक भाषा, complaint/rating बदलने का दबाव और झूठे service notes सख्त मना हैं।\n\nAttendance, location, selfie या job completion का गलत evidence न बनाएं। गलती हो तो तुरंत report करें—छिपाने से समस्या बड़ी होती है। हर visit में आपकी और ARI SMART RO की reputation जुड़ी है।""", "Privacy and truthful records are mandatory. / गोपनीयता और सही रिकॉर्ड अनिवार्य हैं।", ""),
]

QUESTIONS = [
    (1, "An angry customer says this is their third complaint. What should you do first? / नाराज़ ग्राहक कहता है यह तीसरी शिकायत है। पहले क्या करें?", "Blame another team / दूसरी टीम को दोष दें", "Listen fully and acknowledge the frustration / पूरी बात सुनकर परेशानी स्वीकार करें", "Ask them to call office / ऑफिस फोन करने को कहें", "Tell them to calm down / शांत होने को कहें"),
    (2, "You cannot authorize a discount. What is best? / आप discount approve नहीं कर सकते। सही जवाब क्या है?", "Promise now / अभी वादा करें", "Say it is not your problem / कहें यह मेरी समस्या नहीं", "Explain the limit and escalate / सीमा समझाकर request escalate करें", "Give cash discount / cash discount दें"),
    (3, "How is professional customer PR built? / पेशेवर Customer PR कैसे बनता है?", "Personal calls / निजी फोन", "Reliable respectful service / भरोसेमंद सम्मानजनक सेवा", "Asking for gifts / gift माँगना", "Personal social media / निजी social media"),
    (4, "What if a customer becomes threatening? / ग्राहक धमकी देने लगे तो क्या करें?", "Argue / बहस करें", "Continue at any cost / हर हाल में काम जारी रखें", "Create distance, leave politely and escalate / दूरी बनाकर विनम्रता से निकलें और escalate करें", "Record secretly / छिपकर recording करें"),
    (5, "When should a job be completed in the app? / ऐप में job कब complete करें?", "On arrival / पहुँचते ही", "Before testing / test से पहले", "After real work and verification / असली काम और verification के बाद", "When complaint stops / शिकायत बंद होने पर"),
    (6, "How should you communicate an unexpected delay? / अचानक देरी कैसे बताएं?", "Wait for customer to call / ग्राहक के फोन का इंतजार", "Give a realistic update and commitment / सही update और वास्तविक समय दें", "Blame someone / किसी को दोष दें", "Promise impossible time / असंभव समय दें"),
    (7, "Which action violates privacy? / कौन सा काम privacy का उल्लंघन है?", "App service notes / ऐप में service notes", "Using assigned address / assigned address का उपयोग", "Sharing phone number outside work / नंबर काम से बाहर share करना", "Checking history / history देखना"),
    (8, "Best approach to a repeat complaint? / repeat complaint पर सही तरीका?", "Ask everything again / सब दोबारा पूछें", "Review previous notes first / पहले पुराने notes देखें", "Close it / बंद करें", "Tell them to buy new RO / नया RO खरीदने को कहें"),
    (9, "Best response after an insult? / अपमान के बाद सही जवाब?", "You are rude too / आप भी rude हैं", "Calm down / शांत हो जाइए", "I want to help; let us speak respectfully / मैं मदद चाहता हूँ; सम्मान से बात करें", "I will never return / मैं कभी नहीं आऊँगा"),
    (10, "What does LAST mean? / LAST का अर्थ क्या है?", "Listen, Acknowledge, Solve, Thank", "Leave, Argue, Stop, Talk", "Listen, Avoid, Sell, Transfer", "Lead, Answer, Speak, Test"),
]


def update_bilingual_training(apps, schema_editor):
    Course = apps.get_model("employees", "TrainingCourse")
    Lesson = apps.get_model("employees", "TrainingLesson")
    Question = apps.get_model("employees", "TrainingQuestion")
    course = Course.objects.filter(slug="customer-respect-relationship-excellence").first()
    if not course:
        return
    course.title = "Customer Respect & Relationship Excellence / ग्राहक सम्मान एवं संबंध उत्कृष्टता"
    course.description = "Mandatory bilingual practical training in English and Hindi for respectful service, complaint handling and professional customer PR. / सम्मानजनक सेवा, शिकायत समाधान और पेशेवर Customer PR की अनिवार्य द्विभाषी ट्रेनिंग।"
    course.save(update_fields=["title", "description"])
    for order, title, content, takeaway, video_asset in LESSONS:
        Lesson.objects.filter(course=course, order=order).update(
            title=title, content=content, key_takeaway=takeaway, video_asset=video_asset
        )
    for order, question, a, b, c, d in QUESTIONS:
        Question.objects.filter(course=course, order=order).update(
            question=question, option_a=a, option_b=b, option_c=c, option_d=d
        )


class Migration(migrations.Migration):
    dependencies = [("employees", "0015_employee_id_verification_onboarding")]
    operations = [
        migrations.AddField(
            model_name="traininglesson",
            name="video_asset",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.RunPython(update_bilingual_training, migrations.RunPython.noop),
    ]
