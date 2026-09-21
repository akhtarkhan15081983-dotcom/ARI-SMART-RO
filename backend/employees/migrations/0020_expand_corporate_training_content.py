from django.db import migrations


TOPICS = [
    {
        "title": "Respect & First Impression / सम्मान और पहली छाप",
        "objective": "Customer se pehle 60 seconds mein trust build karna: greeting, permission, body language, tone aur ownership.",
        "concepts": "Namaste/Good morning ke saath apna naam aur ARI SMART RO role batayein; ghar/office mein enter karne se pehle permission lein; aankhon ka contact natural rakhein; customer ki baat kaatna nahi; pehle problem samjhein phir technical jawab dein; jo promise karein wahi likhein aur nibhayein.",
        "scenario": "Customer darwaza kholte hi bolta hai: 'Pichli baar engineer ne bahut ganda kaam kiya tha.' Employee ko defensive hue bina concern accept karna hai aur visit ka clear plan batana hai.",
        "mistakes": "Seedha RO khol dena; bina greeting ke kaam shuru karna; 'pichla engineer galat tha' bolna; customer ki baat beech mein rokna; over-friendly/personal hona.",
        "practice": "2 role-play: ek normal customer, ek pehle se upset customer. Employee 60-second professional opening kare. Trainer tone, introduction, permission, listening aur ownership score kare.",
        "takeaway": "First impression technical skill se pehle trust banata hai.",
    },
    {
        "title": "Active Listening / ध्यान से सुनना",
        "objective": "Problem ko customer ke words mein accurately samajhna aur repeat questions se frustration kam karna.",
        "concepts": "Open questions poochhein: 'Problem kab se aa rahi hai?'; customer ke answer ko summarize karein; assumptions na banayein; service history dekhein; key facts note karein; end mein confirm karein: 'Main sahi samjha ki...?'",
        "scenario": "Customer bolta hai water taste kabhi theek kabhi kharab hai. Sirf 'filter change' assume karne ke bajay usage, input water, last service aur symptoms samajhne hain.",
        "mistakes": "Ek symptom sunte hi diagnosis bol dena; same sawal baar-baar poochna; phone dekhte rehna; customer ko hurry feel karana.",
        "practice": "Trainer 2-minute complaint story bolega jisme 6 facts honge. Employee interrupt nahi karega, phir facts summarize karke 3 clarification questions poochega.",
        "takeaway": "Sahi listening diagnosis aur customer trust dono improve karti hai.",
    },
    {
        "title": "Professional Language / पेशेवर भाषा",
        "objective": "Rude, blaming ya casual language ko calm, clear aur solution-focused language se replace karna.",
        "concepts": "'Mujhe nahi pata' ki jagah 'Main verify karke batata hoon'; 'ye mera kaam nahi' ki jagah 'Main correct team tak request pahunchata hoon'; short sentences; respectful titles; unofficial promises avoid; WhatsApp/call par bhi same standard.",
        "scenario": "Customer refund maangta hai lekin employee authorize nahi kar sakta. Employee ko limit explain karke escalation karna hai bina false promise ke.",
        "mistakes": "'Calm down', 'aap galat hain', 'office se baat karo', 'kuch nahi ho sakta', slang ya sarcasm.",
        "practice": "10 unprofessional sentences ko professional alternatives mein convert karein. Trainer clarity aur policy compliance check kare.",
        "takeaway": "Words conflict ko badha bhi sakte hain aur solve bhi.",
    },
    {
        "title": "LAST De-escalation / LAST से गुस्सा शांत करना",
        "objective": "Angry customer ko Listen-Acknowledge-Solve-Thank framework se safely handle karna.",
        "concepts": "Listen bina interruption; Acknowledge inconvenience, zaroori nahi ki har allegation agree karein; Solve mein immediate action + next step; Thank for opportunity; volume low rakhein; personal attack ka jawab personal attack se na dein.",
        "scenario": "Customer kehta hai '3 baar complaint ki, company bekaar hai.' Employee ko history dekhkar action plan dena hai.",
        "mistakes": "Defensive hona; blame shift; customer se debate; impossible ETA; customer ko 'shant ho jaiye' command dena.",
        "practice": "Trainer gradually anger level badhaye. Employee LAST ke 4 steps complete kare aur unsafe point par respectful boundary set kare.",
        "takeaway": "Anger ka jawab control aur structure se dein, ego se nahi.",
    },
    {
        "title": "Repeat Complaints / बार-बार शिकायत",
        "objective": "Repeat complaint ko priority aur context ke saath handle karna taki customer ko dobara sab na batana pade.",
        "concepts": "App history pehle padhein; previous parts/work verify karein; recurring root cause identify karein; customer se acknowledge karein ki issue repeat hua; escalation threshold samjhein; closure evidence strong rakhein.",
        "scenario": "Same leakage complaint 3 visits mein repeat hui. Employee ko sirf tape/seal nahi, installation alignment aur pressure/root cause evaluate karna hai.",
        "mistakes": "Customer ko har baar same story bolne ko kehna; old notes ignore; quick temporary fix; previous employee ko blame.",
        "practice": "Sample job history read karke root-cause hypothesis, questions aur escalation plan likhein.",
        "takeaway": "Repeat complaint mein history hi starting point hai.",
    },
    {
        "title": "Service Recovery / शिकायत से भरोसा",
        "objective": "Company ya service failure ke baad trust rebuild karna.",
        "concepts": "Issue accept; clear apology when appropriate; what can be fixed today; what needs approval/part; realistic timeline; test with customer; follow-up owner identify; notes transparent.",
        "scenario": "Wrong part laane ki wajah se visit complete nahi ho sakti. Employee ko excuse nahi, recovery plan dena hai.",
        "mistakes": "Galti hide karna; fake completion; 'kal pakka' bina confirmation; customer ko chase karne ke liye chhod dena.",
        "practice": "Bad service scenario ko 5-step recovery plan mein convert karein aur customer closing statement practice karein.",
        "takeaway": "Transparent recovery kabhi-kabhi original perfect service se zyada trust bana sakti hai.",
    },
    {
        "title": "Customer PR / ग्राहक संबंध",
        "objective": "Professional relationship build karna without personal boundary cross kiye.",
        "concepts": "Punctuality; proactive updates; clean work; simple education; promises keep; customer preference remember within authorized data; feedback/referral only after satisfaction; no personal contact misuse.",
        "scenario": "Regular rent customer engineer ko personal WhatsApp par unrelated messages bhejta hai. Employee ko polite business boundary maintain karni hai.",
        "mistakes": "Personal friendship pressure; tip/gift expectation; private social media add; repeated promotional calls without purpose.",
        "practice": "Professional follow-up call aur referral request role-play.",
        "takeaway": "PR reliability se banta hai, familiarity se nahi.",
    },
    {
        "title": "Phone Etiquette / फोन शिष्टाचार",
        "objective": "Har call ko structured, concise aur documented banana.",
        "concepts": "Greeting + identity + verify customer + purpose; active listening; hold permission; background noise control; call notes; callback commitment; professional close; no confidential details before verification.",
        "scenario": "Caller rent due reminder karta hai aur customer bolta hai amount galat hai. Caller ko argue nahi, record verify + callback plan dena hai.",
        "mistakes": "Without introduction call; customer ko hold par silently chhodna; loud office gossip; personal number se unnecessary calls.",
        "practice": "3-minute inbound complaint call aur 2-minute outbound reminder call simulate karein.",
        "takeaway": "Call structure speed ke saath professionalism deta hai.",
    },
    {
        "title": "WhatsApp & Digital Etiquette / डिजिटल शिष्टाचार",
        "objective": "Digital messages ko professional, private aur useful rakhna.",
        "concepts": "Approved account/template; short context; no all-caps; sensitive customer data minimum; photo share only work need; no late-night unnecessary message; message delivery ko acceptance assume na karein.",
        "scenario": "Customer photo bhejkar diagnosis poochta hai. Employee ko limited remote guidance deni hai aur unsafe repair instruction avoid karna hai.",
        "mistakes": "Forwarded jokes; customer list broadcast expose; personal emojis/flirting; confidential screenshot share.",
        "practice": "5 poor WhatsApp examples ko professional message mein rewrite karein.",
        "takeaway": "Digital conversation bhi official service record jaisi professionalism maangti hai.",
    },
    {
        "title": "Appointment Discipline / समय और appointment",
        "objective": "Arrival, delay aur reschedule ko predictable banana.",
        "concepts": "Visit confirm; route/time realistic; delay early communicate; new ETA honest; no-show avoid; customer unavailable ho to app notes; urgent job prioritization.",
        "scenario": "Engineer 45 min late hai aur next 2 jobs bhi pending. Manager/customer ko factual update aur realistic revised schedule dena hai.",
        "mistakes": "Phone off; impossible '5 minute' ETA; delay hide; customer ke ghar bina confirm late pahunchna.",
        "practice": "4-job day ka schedule banayein aur unexpected 60-min delay ka reschedule exercise karein.",
        "takeaway": "Time commitment bhi service quality ka part hai.",
    },
    {
        "title": "Home Visit Etiquette / घर पर सेवा शिष्टाचार",
        "objective": "Customer property, privacy aur cleanliness ka respect.",
        "concepts": "Permission before entry/moving items; shoes/local norms; tools organized; floor/sink protection; only assigned area access; children/pets safety; waste remove; final cleanup.",
        "scenario": "RO kitchen cabinet ke andar hai jahan customer ka personal सामान hai. Employee permission aur safe workspace create kare.",
        "mistakes": "Drawers kholna; personal photos; tools floor par spread; wet area chhodna; unapproved person ko ghar mein lana.",
        "practice": "Mock workstation setup and cleanup checklist complete karein.",
        "takeaway": "Customer ka ghar workshop nahi; protected environment hai.",
    },
    {
        "title": "Safety & Boundaries / सुरक्षा और मर्यादा",
        "objective": "Unsafe electrical, water, aggressive-person ya environmental situations mein correct stop/escalate decision.",
        "concepts": "Personal safety first; live electricity/wet area; unstable ladder; threats; harassment; do not work beyond authorization/skill; manager escalation; emergency services when needed.",
        "scenario": "Wet floor ke paas exposed wire hai aur customer insist karta hai 'jaldi repair karo'. Employee ko work stop karke safety explain karni hai.",
        "mistakes": "Customer pressure mein unsafe work; fight; secret recording without policy; unsafe alone entry.",
        "practice": "10 scenarios ko Safe / Stop & Escalate / Proceed with Control categories mein classify karein.",
        "takeaway": "No job target safety se upar nahi.",
    },
    {
        "title": "Privacy & Confidentiality / गोपनीयता",
        "objective": "Customer/employee data ka authorized use samajhna.",
        "concepts": "Phone/address/payment/photos only work purpose; minimum disclosure; screen privacy; OTP never request outside workflow; no data export to personal apps; report accidental exposure.",
        "scenario": "Friend asks ek customer ka number because he wants to sell product. Employee must refuse.",
        "mistakes": "Screenshots personal gallery; customer list export; OTP chat; public group mein address; shared password.",
        "practice": "Data examples ko Public / Internal / Sensitive classify karein aur allowed action discuss karein.",
        "takeaway": "Access milna ownership nahi hota.",
    },
    {
        "title": "Ethics & Truthful Records / नैतिकता और सही रिकॉर्ड",
        "objective": "App records ko ground reality ka accurate audit trail banana.",
        "concepts": "Attendance/location truthful; parts actually used; photos current job ke; payment exact; completion after work; no fake OTP/signature; mistakes correct/escalate, hide nahi.",
        "scenario": "Target close karne ke liye employee incomplete job complete mark karne ka sochta hai. Correct behavior identify kare.",
        "mistakes": "Old photo reuse; false GPS; unused part consume; payment amount adjust; customer signature imitate.",
        "practice": "5 audit scenarios mein fraud/error difference aur correct escalation likhein.",
        "takeaway": "False record short-term convenience, long-term serious risk.",
    },
    {
        "title": "RO Product Basics / RO उत्पाद की बुनियाद",
        "objective": "Customer ko RO stages simple language mein explain karna aur basic symptom mapping samajhna.",
        "concepts": "Sediment removes larger particles; carbon reduces chlorine/odor; membrane separation; post-carbon taste polishing; optional mineral/alkaline/copper stages model-specific; storage and pump/valves; never claim features not installed.",
        "scenario": "Customer asks 'Is machine mein copper hai?' Employee model/configuration verify karke answer kare, assumption nahi.",
        "mistakes": "Har RO ko same bolna; medical claims; installed stage verify na karna; jargon overload.",
        "practice": "RO flow diagram verbally explain karein in 90 seconds, Hindi + simple English.",
        "takeaway": "Simple accurate explanation sales aur service trust dono improve karta hai.",
    },
    {
        "title": "TDS Explanation / TDS समझाना",
        "objective": "Input/output TDS ko factual way mein explain karna without medical claims.",
        "concepts": "Meter reading method; input vs output difference; membrane performance context; taste alone not proof; source water varies; TDS number ko disease/safety guarantee ke roop mein present na karein; company policy/standards follow.",
        "scenario": "Customer says 'TDS 80 hai to water 100% healthy hai na?' Employee ko careful factual answer dena hai.",
        "mistakes": "Exact health guarantee; meter uncalibrated use; one reading se full diagnosis; arbitrary target claim.",
        "practice": "3 TDS scenarios explain karein and what additional checks needed list karein.",
        "takeaway": "Measurement explain karein, medical diagnosis nahi.",
    },
    {
        "title": "Preventive Maintenance / Preventive Maintenance",
        "objective": "Customer ko approved maintenance habits aur warning signs samjhana.",
        "concepts": "Service schedule usage/source/model dependent; filter condition; leakage/noise/taste changes; tank hygiene as policy; prolonged non-use; genuine/approved parts; early complaint reporting.",
        "scenario": "Customer service skip karna chahta hai because water taste okay. Employee preventive reason simple language mein explain kare.",
        "mistakes": "Fear selling; fixed replacement claim without inspection; unapproved chemical/cleaning advice.",
        "practice": "2-minute maintenance education script + customer questions.",
        "takeaway": "Maintenance education helpful ho, pressure sales nahi.",
    },
    {
        "title": "Diagnose Before Replacing / Part बदलने से पहले जाँच",
        "objective": "Evidence-based diagnosis karna aur unnecessary part replacement avoid karna.",
        "concepts": "Symptom reproduce; visual check; water/electrical/pressure basics; history; measurements; isolate cause; authorization; explain evidence; old/new part tracking.",
        "scenario": "RO start nahi ho raha. Pump replace karne se pehle supply, adapter, switches, valves aur relevant checks sequence.",
        "mistakes": "Trial-and-error parts; customer pressure; expensive part first; no evidence note.",
        "practice": "3 symptoms ke diagnostic decision trees banayein.",
        "takeaway": "Diagnosis customer cost aur inventory dono protect karta hai.",
    },
    {
        "title": "Parts & Inventory Discipline / Parts और Inventory",
        "objective": "Har physical part ko system record se match karna.",
        "concepts": "Issue to bag; serialized scan; request if shortage; used/returned/damaged status; no informal transfer; old part handling policy; stock counts; receipt confirmation.",
        "scenario": "Engineer ko bag mein required SV nahi hai but colleague ke paas hai. Correct transfer/request process follow karna hai.",
        "mistakes": "Unrecorded handover; wrong serial; customer se part collect without record; stock adjustment manually hide.",
        "practice": "Part request → approval → issue → job use → return flow mock karein.",
        "takeaway": "Inventory discipline leakage aur service delay dono kam karta hai.",
    },
    {
        "title": "Installation Excellence / Installation Excellence",
        "objective": "Site readiness se customer handover tak consistent installation.",
        "concepts": "Site/water/electric check; mounting/fitment; tubing; leakage; inlet/outlet; flushing; TDS/functional test; serial/asset data; payment/security/install charge clarity; customer demo.",
        "scenario": "Site mein suitable drain point nahi aur customer alternative unsafe routing insist karta hai. Employee escalate/alternative explain kare.",
        "mistakes": "Testing skip; hidden leakage; incomplete handover; wrong financial breakup; serial not recorded.",
        "practice": "Full installation checklist role-play using mock unit.",
        "takeaway": "Installation quality future complaints ka base set karti hai.",
    },
    {
        "title": "Service Closure / Service Closure",
        "objective": "Job tabhi close karna jab work, evidence, customer explanation aur verification complete ho.",
        "concepts": "Before/after check; parts used; photos where required; notes specific; test; customer confirmation; OTP/signature correct stage; pending item openly mark; no premature completion.",
        "scenario": "Main issue fixed but secondary part approval pending. Employee should not claim all work complete.",
        "mistakes": "Generic note 'done'; OTP before work; customer absent signature; pending issue hide.",
        "practice": "Poor job notes ko audit-ready closure notes mein rewrite karein.",
        "takeaway": "Closure record future technician ke liye instruction hai.",
    },
    {
        "title": "OTP & Signature Integrity / OTP और Signature",
        "objective": "Customer verification evidence ko genuine aur workflow-specific rakhna.",
        "concepts": "OTP customer-visible flow; admin emergency visibility only controlled use; never ask customer to share future OTP; signature actual customer/authorized person; explain what they confirm; no self-entry.",
        "scenario": "Customer phone unavailable and technician asks admin for OTP. Emergency policy follow with audit trail.",
        "mistakes": "OTP guess; engineer own signature; pre-closure OTP; OTP screenshot reuse.",
        "practice": "Normal + emergency verification scenarios execute karein.",
        "takeaway": "OTP/signature trust evidence hai, shortcut nahi.",
    },
    {
        "title": "Payment Conversation / Payment बातचीत",
        "objective": "Dues, security, installation charge, rent aur approved offers transparently explain karna.",
        "concepts": "App amount source; breakup explain; receipt/record; active offer only; no unofficial discount; cash/digital policy; disputed amount escalation; customer pressure avoid.",
        "scenario": "Customer says previous caller promised lower rent but app amount different. Employee verify + escalate, not invent adjustment.",
        "mistakes": "Personal QR; cash without record; verbal discount; confusing security vs installation charges.",
        "practice": "₹3000 example breakup explain karein and disputed-payment role-play.",
        "takeaway": "Money conversation mein clarity + record mandatory.",
    },
    {
        "title": "Handling Price Objections / Price Objection",
        "objective": "Argument ke bina value, policy aur authorized options explain karna.",
        "concepts": "First understand objection; compare approved service/value, not competitor insults; offer scope/validity; payment/rent options if available; manager approval for exceptions; no pressure.",
        "scenario": "Customer says local mechanic half price mein karega. Employee service history, genuine parts/process, warranty/support value explain kare.",
        "mistakes": "Competitor abuse; fake scarcity; unauthorized discount; fear-based claims.",
        "practice": "3 objections: expensive service, rent high, part cost high.",
        "takeaway": "Objection ko information need samjhein, fight nahi.",
    },
    {
        "title": "Referral Request / Referral माँगना",
        "objective": "Satisfaction ke baad ethical referral request karna.",
        "concepts": "First resolve service; ask permission; program terms accurate; no pressure; no fake accounts; referral identity truthful; reward policy; privacy.",
        "scenario": "Satisfied customer ke visit end par 20-second referral explanation.",
        "mistakes": "Complaint unresolved while referral ask; customer phone use to self-refer; reward guarantee outside terms.",
        "practice": "Natural referral script + refusal ko gracefully accept.",
        "takeaway": "Referral earned trust ka extension hai.",
    },
    {
        "title": "Difficult Customer Role-play / कठिन ग्राहक Role-play",
        "objective": "Multiple pressure factors ko ek simulation mein handle karna.",
        "concepts": "Anger + delay + price + repeat complaint; prioritize safety; listen; facts; policy boundaries; options; escalation; documented close.",
        "scenario": "Customer 2-hour delay, repeated leakage aur payment dispute ke saath angry hai. Employee ko structured conversation + technical next step + financial escalation manage karna hai.",
        "mistakes": "Ek issue par stuck; defensive; promise everything; no notes.",
        "practice": "10-minute full simulation, trainer score behaviour/communication/knowledge and replay weak section.",
        "takeaway": "Real service problems mixed hote hain; structure maintain karein.",
    },
    {
        "title": "Communication Under Pressure / दबाव में संवाद",
        "objective": "Time pressure, target pressure aur angry customer ke beech calm decision making.",
        "concepts": "Pause before reply; facts vs assumptions; top priority; one next action; concise escalation; emotion regulation; no rushed unsafe shortcut.",
        "scenario": "Manager calls for next job while current customer still unresolved. Employee current safe closure + realistic status communicate kare.",
        "mistakes": "Customer ke saamne team blame; hurried incomplete work; silent delay; emotional message.",
        "practice": "60-second pressure response drills with changing information.",
        "takeaway": "Pressure mein speed se pehle clarity.",
    },
    {
        "title": "Team Escalation / टीम Escalation",
        "objective": "Manager/Admin ko actionable escalation dena.",
        "concepts": "Who/where/job ID; exact issue; evidence; what tried; risk/urgency; required decision; customer expectation; next update time.",
        "scenario": "Part repeatedly failing, customer angry and same-day approval needed. Escalation message structured format mein bhejna.",
        "mistakes": "'urgent call me'; incomplete facts; emotional blame; no requested action.",
        "practice": "5-line escalation template se 3 cases submit karein.",
        "takeaway": "Good escalation manager ka decision time bachata hai.",
    },
    {
        "title": "Personal Improvement Coaching / व्यक्तिगत सुधार",
        "objective": "Trainer feedback ko measurable improvement plan mein convert karna.",
        "concepts": "Strengths maintain; one/two priority gaps; specific behaviour; practice frequency; evidence; review date; ask for help; defensive response avoid.",
        "scenario": "Employee technically strong but communication score 2/5. 7-day improvement plan banaye.",
        "mistakes": "Generic 'improve communication'; feedback argue; too many goals; no follow-up.",
        "practice": "SMART improvement plan + trainer agreement.",
        "takeaway": "Feedback tab useful hai jab next action measurable ho.",
    },
    {
        "title": "Final Simulation & 30-Day Action Plan / अंतिम Simulation",
        "objective": "Full customer journey demonstrate karna aur next month ka performance plan banana.",
        "concepts": "Appointment; arrival; complaint listening; diagnosis; safe work; parts/payment; customer education; verification; closure; notes; referral only if appropriate; escalation.",
        "scenario": "End-to-end mock customer: repeat complaint + one technical fault + price question + delayed arrival + final verification.",
        "mistakes": "Checklist mechanically read; customer emotion ignore; incomplete record; trainer feedback skip.",
        "practice": "15–20 minute final simulation. Trainer final scores de, employee 3 strengths + 3 improvement actions + review dates document kare.",
        "takeaway": "Training ka result behaviour change hai, sirf completion badge nahi.",
    },
]


QUESTIONS = [
    ("First visit opening mein sabse professional action kya hai?", "Seedha RO kholna", "Introduction, permission aur problem sunna", "Previous engineer ko blame karna", "Customer se OTP maangna", "B", "Professional opening trust aur context establish karti hai."),
    ("Active listening ka best proof kya hai?", "Customer ko interrupt karna", "Problem assume karna", "Facts summarize karke confirmation lena", "Sirf app dekhna", "C", "Summary + confirmation misunderstanding kam karta hai."),
    ("Unauthorized discount request par kya karein?", "Promise kar dein", "Cash discount de dein", "Authority limit explain karke escalate karein", "Ignore karein", "C", "Only authorized commercial commitments allowed hain."),
    ("LAST mein A ka matlab?", "Argue", "Acknowledge", "Avoid", "Approve", "B", "LAST = Listen, Acknowledge, Solve, Thank."),
    ("Repeat complaint mein pehla operational step?", "Customer ko sab dobara bolne ko kahen", "Old history review karein", "Job close karein", "New RO sell karein", "B", "History repeat frustration aur missed root cause reduce karti hai."),
    ("Company mistake hone par professional recovery?", "Hide karein", "Excuse dein", "Acknowledge + realistic corrective plan", "Customer ko blame", "C", "Transparency trust rebuild karti hai."),
    ("Customer PR ka correct base?", "Personal friendship", "Reliable respectful service", "Gifts", "Daily personal calls", "B", "Professional relation consistency se banta hai."),
    ("Phone call start ka correct sequence?", "Price bolo aur cut", "Identity + verification + purpose", "OTP maango", "Hold par daalo", "B", "Structured opening privacy aur clarity protect karti hai."),
    ("Customer data WhatsApp group mein share karna?", "Always allowed", "Only if friend asks", "Unauthorized, avoid", "Customer old ho to okay", "C", "Customer data authorized purpose tak limited hai."),
    ("Delay hone par kya karein?", "Customer call ka wait", "Fake 5-min ETA", "Early realistic update", "Phone off", "C", "Proactive truthful update trust protect karta hai."),
    ("Home visit mein personal cabinet kholna?", "Without asking", "Permission ke saath only if work requires", "Always", "Photo ke liye", "B", "Property/privacy boundaries mandatory hain."),
    ("Unsafe wet electrical area mein?", "Target ke liye continue", "Stop and make safe/escalate", "Customer ko karne dein", "Ignore", "B", "Safety service target se upar hai."),
    ("Customer phone number friend ko dena?", "Allowed", "Not authorized", "Referral ke liye always", "If old customer then allowed", "B", "Access ownership nahi hota."),
    ("False job completion record?", "Target help karta hai", "Minor issue", "Serious integrity violation", "Manager na dekhe to okay", "C", "Records must match reality."),
    ("RO stage explain karte waqt?", "Installed model verify karein", "Har model same bolen", "Medical cure claim karein", "Guess karein", "A", "Configuration-specific factual explanation required hai."),
    ("TDS number se 100% health guarantee?", "Haan", "Nahi, factual measurement explain karein", "Only if below 100", "Customer decide", "B", "TDS alone medical safety guarantee nahi hai."),
    ("Preventive maintenance conversation?", "Fear pressure", "Approved care + warning signs explain", "Fixed part replacement force", "Nothing", "B", "Education should be useful, not coercive."),
    ("Part replace se pehle?", "Evidence-based diagnosis", "Most expensive part", "Customer guess", "Random trial", "A", "Diagnosis unnecessary cost/stock loss avoid karta hai."),
    ("Colleague se unrecorded part lena?", "Okay", "Record/approved transfer process follow", "Cash dekar lein", "Customer ko bill na dein", "B", "Physical stock system record se match hona chahiye."),
    ("Installation close se pehle?", "Testing + leakage + handover", "Arrival", "Payment discussion only", "Photo only", "A", "Functional verification and handover core steps hain."),
    ("Service job complete kab?", "Actual work + verification ke baad", "Before work", "OTP milte hi", "Arrival par", "A", "Completion must reflect real work."),
    ("Customer OTP ka correct use?", "Any future job", "Current authorized workflow only", "Engineer own phone", "Share with team group", "B", "OTP workflow-specific evidence hai."),
    ("Payment dispute mein?", "Invent discount", "Record verify + escalate discrepancy", "Customer ko threaten", "Personal QR use", "B", "Financial discrepancy transparent verification se handle hoti hai."),
    ("Price objection par?", "Competitor insult", "Value/policy/authorized options", "Fake urgency", "Unofficial discount", "B", "Information + authorized options professional response hain."),
    ("Referral kab ask karein?", "Unresolved complaint mein", "After satisfaction without pressure", "Before service", "Reward guarantee karke", "B", "Referral earned satisfaction ke baad ethical hai."),
    ("Difficult mixed scenario mein?", "Ek issue par argue", "Structure: listen, facts, safety, options, escalation", "Promise everything", "Leave notes blank", "B", "Complex case ko structured steps chahiye."),
    ("Pressure mein best communication?", "Fastest answer", "Pause, facts, one clear next action", "Blame", "Silent", "B", "Clarity rushed response se better hai."),
    ("Good escalation mein kya hona chahiye?", "Only 'urgent'", "Facts + evidence + required decision", "Emotional complaint", "No job ID", "B", "Actionable escalation decision speed improve karti hai."),
    ("Trainer feedback ko kaise use karein?", "Ignore", "Specific measurable improvement plan", "Argue", "Generic 'improve'", "B", "Measurable action se feedback behaviour change banta hai."),
    ("Training ka real outcome kya hai?", "Sirf certificate", "Observed behaviour/knowledge improvement", "Quiz attempt count", "App open karna", "B", "Certificate evidence hai; goal capability improvement hai."),
]


def expand_training(apps, schema_editor):
    Course = apps.get_model("employees", "TrainingCourse")
    Lesson = apps.get_model("employees", "TrainingLesson")
    Question = apps.get_model("employees", "TrainingQuestion")

    course = Course.objects.filter(slug="customer-respect-relationship-excellence").first()
    if course is None:
        return

    course.title = "ARI Professional Customer Service, Field Excellence & Ethics Academy / 30-Day"
    course.description = (
        "A practical 30-day corporate academy for ARI SMART RO employees. Every day is designed for "
        "approximately 60 minutes of guided learning: concept, real ARI scenario, trainer demonstration, "
        "employee role-play/practical task, feedback and action note. The programme covers customer PR, "
        "complaint handling, field etiquette, privacy, ethics, RO basics, diagnosis, installation, inventory, "
        "payments, OTP integrity, escalation and professional improvement."
    )
    course.due_days = 35
    course.grace_days = 3
    course.passing_score = 80
    course.certificate_enabled = True
    course.certificate_valid_days = 365
    course.required_trainer_reviews = 30
    course.minimum_trainer_average = 3
    course.is_published = True
    course.save(update_fields=[
        "title", "description", "due_days", "grace_days", "passing_score",
        "certificate_enabled", "certificate_valid_days", "required_trainer_reviews",
        "minimum_trainer_average", "is_published",
    ])

    for day, topic in enumerate(TOPICS, start=1):
        existing = Lesson.objects.filter(course=course, order=day).first()
        video_asset = existing.video_asset if existing else ""
        content = (
            f"DAY {day} — {topic['title']}\n\n"
            f"LEARNING OBJECTIVE / आज क्या सीखेंगे\n{topic['objective']}\n\n"
            f"CORE CONCEPTS / मुख्य बातें\n{topic['concepts']}\n\n"
            f"REAL ARI SMART RO SCENARIO / वास्तविक स्थिति\n{topic['scenario']}\n\n"
            f"COMMON MISTAKES TO AVOID / क्या नहीं करना है\n{topic['mistakes']}\n\n"
            "60-MINUTE LEARNING PLAN / 60 मिनट की योजना\n"
            "• 10 min — पिछले दिन की सीख और आज का objective\n"
            "• 15 min — concept explanation with ARI policy/context\n"
            "• 10 min — trainer demonstrates good vs poor example\n"
            "• 15 min — employee role-play / practical exercise\n"
            "• 5 min — trainer feedback: behaviour, communication, knowledge\n"
            "• 5 min — employee action note: kal se kya badlega\n\n"
            f"PRACTICAL EXERCISE / अभ्यास\n{topic['practice']}\n\n"
            "SELF-CHECK / खुद से पूछें\n"
            "1. Kya maine customer/situation ko bina assumption samjha?\n"
            "2. Kya meri language respectful aur policy-compliant thi?\n"
            "3. Kya maine next action clear kiya?\n"
            "4. Kya app record reality ko accurately show karega?\n"
            "5. Agar risk/authority limit thi to kya maine sahi escalation ki?\n"
        )
        trainer_script = (
            f"Trainer objective: {topic['objective']}\n"
            "1. Employee se pehle apni understanding bulwayein.\n"
            "2. Ek intentionally poor example demonstrate karein aur employee se errors identify karwayein.\n"
            f"3. Scenario run karein: {topic['scenario']}\n"
            "4. Employee se scenario dobara correct way mein perform karwayein.\n"
            "5. Behaviour, communication aur knowledge ko 1–5 score karein.\n"
            "6. Strength, gap aur ek specific coaching action record karein.\n"
            "7. Score 3 se kam ho to same scenario repeat karwayein before moving on."
        )
        practice_task = (
            f"{topic['practice']}\n\n"
            "Employee must write one real action that will be used on the next customer/job. "
            "Trainer should verify the action is specific and observable."
        )
        Lesson.objects.update_or_create(
            course=course,
            order=day,
            defaults={
                "day_number": day,
                "duration_minutes": 60,
                "title": f"Day {day}: {topic['title']}",
                "content": content,
                "key_takeaway": topic["takeaway"][:300],
                "trainer_script": trainer_script,
                "practice_task": practice_task,
                "video_asset": video_asset,
            },
        )

    for order, row in enumerate(QUESTIONS, start=1):
        question, a, b, c, d, correct, explanation = row
        Question.objects.update_or_create(
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

    Question.objects.filter(course=course, order__gt=len(QUESTIONS)).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("employees", "0019_training_academy_builder"),
    ]

    operations = [
        migrations.RunPython(expand_training, migrations.RunPython.noop),
    ]
