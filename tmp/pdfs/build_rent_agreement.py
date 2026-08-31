from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

root = Path(__file__).resolve().parents[2]
out = root / "output" / "pdf" / "ARI_SMART_RO_Rental_Agreement_Draft_v1.pdf"
out.parent.mkdir(parents=True, exist_ok=True)

W, H, M = 1654, 2339, 120
NAVY, BLUE, INK, MUTED, LINE = "#07315E", "#0868D7", "#172033", "#5E6B7C", "#CCD7E4"
FONT = r"C:\Windows\Fonts\Nirmala.ttc"

def ff(size, bold=False):
    return ImageFont.truetype(FONT, size=size, index=1 if bold else 0)

BRAND, H1, H2, H3 = ff(52, True), ff(41, True), ff(31, True), ff(25, True)
BODY, BODY_B, SMALL, TINY = ff(24), ff(24, True), ff(19), ff(16)

def wrap(draw, text, font, width):
    result = []
    for para in text.split("\n"):
        words, line = para.split(), ""
        for word in words:
            test = (line + " " + word).strip()
            if draw.textbbox((0, 0), test, font=font)[2] <= width:
                line = test
            else:
                if line:
                    result.append(line)
                line = word
        result.append(line)
    return result

def text(draw, y, value, font=BODY, color=INK, indent=0, gap=8):
    for line in wrap(draw, value, font, W - 2 * M - indent):
        draw.text((M + indent, y), line, font=font, fill=color)
        y += int(font.size * 1.48)
    return y + gap

def bullet(draw, y, value, positive=True):
    draw.ellipse((M, y + 8, M + 16, y + 24), fill="#0C9B67" if positive else "#D94452")
    return text(draw, y, value, indent=34, gap=3)

def new_page(number):
    image = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((M, 70, W - M, 200), radius=28, fill=NAVY)
    draw.ellipse((M + 30, 92, M + 104, 166), fill="white")
    draw.text((M + 43, 112), "ARI", font=ff(20, True), fill=BLUE)
    draw.text((M + 130, 92), "ARI SMART RO", font=BRAND, fill="white")
    draw.text((M + 132, 151), "RO SYSTEM RENTAL AGREEMENT", font=SMALL, fill="#35C4E8")
    draw.text((W - M - 160, 112), f"PAGE {number}", font=TINY, fill="white")
    return image, draw

def footer(draw, number):
    draw.line((M, H - 105, W - M, H - 105), fill=LINE, width=2)
    draw.text((M, H - 82), "ARI Bulky Seller | ARI SMART RO | Draft for legal review", font=TINY, fill=MUTED)
    draw.text((W - M - 210, H - 82), f"Version 1.0 | {number}/5", font=TINY, fill=MUTED)

pages = []

img, d = new_page(1)
y = 250
d.text((M, y), "किराया अनुबंध / RENTAL AGREEMENT", font=H1, fill=NAVY)
y += 72
y = text(d, y, "यह अनुबंध दिनांक ____ / ____ / 20____ को ARI Bulky Seller (ARI SMART RO) और नीचे वर्णित ग्राहक के बीच किया जा रहा है।", color=MUTED)
d.rounded_rectangle((M, y, W - M, y + 120), radius=18, fill="#EAF5FF")
d.text((M + 24, y + 18), "महत्वपूर्ण / IMPORTANT", font=H3, fill=BLUE)
d.text((M + 24, y + 63), "यह Version 1.0 operational draft है। Production उपयोग से पहले legal review आवश्यक है।", font=BODY, fill=INK)
y += 155
d.text((M, y), "1. ग्राहक विवरण", font=H2, fill=NAVY)
y += 58
for label in ["ग्राहक का नाम", "पिता/पति/अभिभावक", "पंजीकृत मोबाइल नंबर", "पूरा इंस्टॉलेशन पता", "आधार नंबर (वैकल्पिक)"]:
    d.text((M, y), label, font=BODY_B, fill=INK)
    d.line((M + 550, y + 30, W - M, y + 30), fill=LINE, width=2)
    y += 64
d.text((M, y + 8), "2. योजना एवं शुल्क", font=H2, fill=NAVY)
y += 70
for i, (a, b) in enumerate([("इंस्टॉलेशन / सिक्योरिटी राशि", "₹3,000"), ("मासिक किराया", "₹300 प्रति माह"), ("नियमित सर्विस", "शर्तों के अनुसार निःशुल्क"), ("सामान्य covered parts", "शर्तों के अनुसार निःशुल्क")]):
    top = y + i * 74
    d.rectangle((M, top, W - M, top + 69), fill="#F8FAFD" if i % 2 == 0 else "white", outline=LINE, width=2)
    d.text((M + 22, top + 18), a, font=BODY_B, fill=INK)
    d.text((W - M - 470, top + 18), b, font=BODY, fill=BLUE)
y += 340
y = text(d, y, "RO सिस्टम का स्वामित्व कंपनी के पास रहेगा। ग्राहक केवल अधिकृत उपयोगकर्ता होगा।", font=BODY_B)
footer(d, 1)
pages.append(img)

img, d = new_page(2)
y = 250
d.text((M, y), "3. ARI Referral & Wallet Program", font=H1, fill=NAVY)
y += 78
y = text(d, y, "पुराना 30-day / 2-referral / 10-month free offer इस agreement का हिस्सा नहीं है। केवल app में उपलब्ध ARI referral program लागू होगा।", font=BODY_B, color=BLUE)
for value in [
    "Self-referral मान्य नहीं है और एक referred customer केवल एक referral attribution claim कर सकता है।",
    "Reward केवल account/lead बनने पर नहीं, बल्कि company द्वारा qualifying rent installation या purchase पूरा होने की पुष्टि के बाद मिलेगा।",
    "Rent customer द्वारा सफल rent customer referral पर ₹600 wallet reward मिलेगा: अधिकतम ₹50 प्रति rent month, कुल 12 months के लिए।",
    "Rent customer द्वारा successful purchase referral पर qualifying purchase amount का 15% reward rent category में credit हो सकता है।",
    "Rent bill में wallet उपयोग के बाद customer को कम-से-कम ₹100 स्वयं देना होगा।",
    "Rent referral reward की validity 365 days है; unused amount expiry पर समाप्त हो सकता है।",
    "Reward cash withdrawal या cash conversion के लिए उपलब्ध नहीं है। Credit, debit, expiry और reversal wallet ledger में दर्ज होंगे।",
]:
    y = bullet(d, y, value)
y += 28
d.line((M, y, W - M, y), fill=LINE, width=2)
y += 38
d.text((M, y), "4. सर्विस एवं covered parts", font=H2, fill=NAVY)
y += 58
y = text(d, y, "समय पर किराया भुगतान और उचित उपयोग की स्थिति में नियमित service visit तथा plan में covered सामान्य wear-and-tear parts उपलब्ध कराए जा सकते हैं।")
for value in ["Pipe, elbow और fittings", "Filter housing leakage repair", "Routine service visit", "अन्य parts - आवश्यकता, compatibility और selected plan के अनुसार"]:
    y = bullet(d, y, value)
y = text(d, y + 14, "Membrane, pump, SMPS, consumables या major assemblies केवल तभी free होंगे जब selected plan/work order में स्पष्ट रूप से शामिल हों।", font=BODY_B, color=BLUE)
footer(d, 2)
pages.append(img)

img, d = new_page(3)
y = 250
d.text((M, y), "5. नुकसान एवं अपवाद", font=H1, fill=NAVY)
y += 76
y = text(d, y, "निम्न स्थितियों में free repair/replacement लागू नहीं होगा और वास्तविक cost customer को बताकर charge की जा सकती है:")
for value in ["मशीन टूटना या जानबूझकर नुकसान", "आग, जलना, पानी में डूबना या बाहरी दुर्घटना", "गलत voltage, unauthorized connection या misuse", "बिना अनुमति machine खोलना, स्थान बदलना या third-party repair", "चोरी, गुम होना या inspection access न देना"]:
    y = bullet(d, y, value, False)
y += 30
d.line((M, y, W - M, y), fill=LINE, width=2)
y += 40
d.text((M, y), "6. सिक्योरिटी राशि वापसी", font=H2, fill=NAVY)
y += 60
y = text(d, y, "₹3,000 security amount निम्न शर्तों पर refund review के लिए पात्र होगा:")
for value in ["कम-से-कम 3 वर्ष की योजना अवधि पूरी हो", "RO system और company accessories वापस किए जाएँ", "सामान्य wear-and-tear को छोड़कर machine उचित condition में हो", "सभी rent/charges clear हों", "Company inspection और final settlement पूरा हो"]:
    y = bullet(d, y, value)
y = text(d, y + 15, "Damage, missing accessories, unpaid dues या approved repair cost final settlement से काटी जा सकती है; deduction details customer record में दी जानी चाहिए।", font=BODY_B, color=BLUE)
footer(d, 3)
pages.append(img)

img, d = new_page(4)
y = 250
d.text((M, y), "7. भुगतान एवं मशीन वापसी", font=H1, fill=NAVY)
y += 76
for value in [
    "मासिक किराया निर्धारित due date तक देना आवश्यक है।",
    "लगातार 3 माह किराया न मिलने पर company notice देकर RO वापस लेने की प्रक्रिया शुरू कर सकती है।",
    "वापसी/termination पर unpaid dues, damage और applicable charges का final settlement होगा।",
    "सभी disputes के लिए source agreement में Agra jurisdiction प्रस्तावित है; legal review आवश्यक है।",
]:
    y = bullet(d, y, value)
y += 30
d.line((M, y, W - M, y), fill=LINE, width=2)
y += 40
d.text((M, y), "8. ग्राहक की जिम्मेदारियाँ", font=H2, fill=NAVY)
y += 60
for value in ["सही contact/address देना और बदलाव की सूचना देना", "सुरक्षित बिजली और पानी connection उपलब्ध रखना", "Service engineer को उचित access देना", "Leak, abnormal sound या खराबी की तुरंत सूचना देना", "RO को sell, sublet या बिना अनुमति स्थानांतरित न करना"]:
    y = bullet(d, y, value)
y += 30
d.line((M, y, W - M, y), fill=LINE, width=2)
y += 40
d.text((M, y), "9. Company service record", font=H2, fill=NAVY)
y += 60
y = text(d, y, "Installation, service visits, parts usage, rent payments, referral wallet activity और agreement acceptance ARI SMART RO system में दर्ज किए जा सकते हैं। Customer को अपने account में उपलब्ध records देखने की सुविधा दी जाएगी।")
footer(d, 4)
pages.append(img)

img, d = new_page(5)
y = 250
d.text((M, y), "10. डिजिटल स्वीकृति एवं घोषणा", font=H1, fill=NAVY)
y += 80
y = text(d, y, "मैं पुष्टि करता/करती हूँ कि मैंने इस agreement के सभी पृष्ठ पढ़े और समझे हैं। शुल्क, referral wallet, service coverage, exclusions, payment default और security refund conditions मुझे समझाई गई हैं। मैं Version 1.0 की शर्तें स्वीकार करता/करती हूँ।", font=BODY_B)
y += 20
for value in ["Agreement version: ____________________", "Customer account ID: ____________________", "Registered mobile: ____________________", "Acceptance date & time: ____________________", "OTP verification reference: ____________________", "Device/audit reference: ____________________"]:
    d.rounded_rectangle((M, y, W - M, y + 58), radius=12, outline=LINE, width=2)
    d.text((M + 18, y + 13), value, font=BODY, fill=INK)
    y += 72
y += 12
d.text((M, y), "ग्राहक हस्ताक्षर", font=H3, fill=NAVY)
d.rounded_rectangle((M, y + 48, M + 610, y + 300), radius=16, outline=LINE, width=2)
d.text((M + 28, y + 152), "Sign here / यहाँ हस्ताक्षर करें", font=SMALL, fill=MUTED)
d.text((M + 690, y), "कंपनी प्रतिनिधि", font=H3, fill=NAVY)
d.rounded_rectangle((M + 690, y + 48, W - M, y + 300), radius=16, outline=LINE, width=2)
y += 350
y = text(d, y, "Acceptance के बाद agreement copy customer account में उपलब्ध कराई जाएगी। नई contract version लागू होने पर fresh consent लिया जाएगा।", font=BODY_B, color=BLUE)
d.rounded_rectangle((M, y + 15, W - M, y + 135), radius=16, fill="#FFF6E6")
d.text((M + 22, y + 36), "LEGAL REVIEW NOTE", font=H3, fill="#A45F00")
d.text((M + 22, y + 78), "यह operational draft है, legal advice नहीं। Amounts और core terms source PDF से लिए गए हैं।", font=SMALL, fill=INK)
footer(d, 5)
pages.append(img)

pages[0].save(out, "PDF", resolution=200.0, save_all=True, append_images=pages[1:])
print(out)
