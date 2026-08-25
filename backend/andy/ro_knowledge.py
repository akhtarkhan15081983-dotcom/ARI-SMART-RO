import re


def _normalize(text):
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _has(q, *phrases):
    return any(phrase in q for phrase in phrases)


def answer_ro_question(text):
    """Return bounded, practical RO guidance for common customer symptoms."""
    q = _normalize(text)

    if _has(
        q,
        "pani kam", "water kam", "low flow", "slow water", "paani kam",
        "पानी कम", "पानी धीरे", "flow kam", "pressure kam",
    ):
        return (
            "RO ka pani kam aaye to pehle inlet pressure aur sediment/pre-carbon filters check karein. "
            "Phir booster pump, RO membrane, flow restrictor aur tank air-pressure technician se check karayein."
        )

    if _has(q, "tds high", "high tds", "tds badh", "tds zyada", "टीडीएस", "टीडीएस ज्यादा"):
        return (
            "Output TDS zyada ho to membrane condition, membrane housing seal aur TDS controller setting check karein. "
            "Input/output TDS meter se naap kar hi controller adjust ya membrane replace karayein."
        )

    if _has(
        q,
        "bad taste", "taste kharab", "smell", "badbu", "बदबू", "स्वाद खराब",
        "pani ka taste", "paani ka taste",
    ):
        return (
            "Taste ya smell kharab ho to storage tank sanitize karein aur post-carbon filter ki age check karein. "
            "Purane filters badlein aur servicing ke baad tank ko flush karke hi pani use karein."
        )

    if _has(q, "leak", "leakage", "pani tapak", "पानी टपक", "लीकेज"):
        return (
            "Leakage mein pehle RO ki water supply aur power band karein. "
            "Pipe fitting, elbow, filter housing O-ring aur tank valve check karke damaged part replace karayein."
        )

    if _has(
        q,
        "pump nahi", "pump band", "motor nahi", "start nahi", "चालू नहीं",
        "machine nahi chal", "ro nahi chal",
    ):
        return (
            "RO start na ho to socket, adapter/SMPS, low-pressure switch aur inlet water supply check karein. "
            "Supply sahi ho to booster pump, wiring aur solenoid valve technician se test karayein."
        )

    if _has(
        q,
        "tank nahi bhar", "tank fill nahi", "टैंक नहीं भर", "tank khali",
        "storage tank",
    ):
        return (
            "Tank na bhare to inlet pressure, clogged filters, booster pump aur membrane flow check karein. "
            "Tank valve khula ho aur tank air-pressure sahi ho; over-pressure mein pani store nahi hota."
        )

    if _has(
        q,
        "waste water", "drain water", "pani waste", "continuous drain",
        "reject water", "वेस्ट पानी",
    ):
        return (
            "RO band hone ke baad bhi waste water chale to auto shut-off valve, solenoid valve aur tank pressure check karein. "
            "Flow restrictor ko bypass na karein; faulty valve technician se replace karayein."
        )

    if _has(q, "filter kab", "filter change", "service kab", "फिल्टर बदल", "service due"):
        return (
            "Filter replacement fixed date se nahi, water quality aur usage se decide hota hai. "
            "Flow, taste, smell aur TDS check karayein; sediment/pre-carbon aam taur par membrane se pehle badalte hain."
        )

    return None
