SYMPTOM_GUIDANCE = {
    "WATER_NOT_COMING": {
        "label": "Water not coming",
        "complaint_type": "RO_NOT_WORKING",
        "priority": "NORMAL",
        "checks": [
            "Check whether inlet water is available.",
            "Check that the external inlet valve is in its normal open position.",
            "Check whether the RO power plug and wall switch are on.",
        ],
    },
    "SLOW_FLOW": {
        "label": "Water flow is slow",
        "complaint_type": "LOW_WATER_FLOW",
        "priority": "NORMAL",
        "checks": [
            "Check whether inlet water pressure appears unusually low.",
            "Check that the external inlet valve is fully open.",
            "Check the RO Health screen for a service-due alert.",
        ],
    },
    "BAD_TASTE": {
        "label": "Bad taste",
        "complaint_type": "BAD_TASTE",
        "priority": "NORMAL",
        "checks": [
            "Stop using the water if the taste seems unsafe or suddenly unusual.",
            "Check the RO Health screen for due or overdue filter service.",
            "Raise a complaint for water-quality inspection if the taste remains unusual.",
        ],
    },
    "BAD_SMELL": {
        "label": "Bad smell",
        "complaint_type": "OTHER",
        "priority": "NORMAL",
        "checks": [
            "Stop using the water if the smell seems unsafe or suddenly unusual.",
            "Check whether the smell is present only at the RO tap or also in inlet water.",
            "Raise a complaint for water-quality inspection if the smell continues.",
        ],
    },
    "HIGH_TDS": {
        "label": "High TDS",
        "complaint_type": "FILTER_PROBLEM",
        "priority": "NORMAL",
        "checks": [
            "Confirm the reading with a clean TDS meter if one is safely available.",
            "Check the RO Health screen for membrane or filter service alerts.",
            "Raise a complaint for an engineer to verify water quality and the RO system.",
        ],
    },
    "LEAKAGE": {
        "label": "Leakage",
        "complaint_type": "WATER_LEAKAGE",
        "priority": "EMERGENCY",
        "checks": [
            "Keep people and electrical items away from visible leaking water.",
            "If it is safe and easily accessible, turn off the external inlet water valve.",
            "Do not open the RO cabinet, filter housings, pump, wiring, or pressurized parts.",
        ],
    },
    "UNUSUAL_SOUND": {
        "label": "Unusual sound",
        "complaint_type": "OTHER",
        "priority": "NORMAL",
        "checks": [
            "Check whether inlet water is available and the external valve is open.",
            "Note when the sound occurs so the engineer can reproduce it.",
            "Do not open the pump, motor, electrical parts, or RO cabinet.",
        ],
    },
    "PUMP_NOT_WORKING": {
        "label": "Pump not working",
        "complaint_type": "PUMP_PROBLEM",
        "priority": "NORMAL",
        "checks": [
            "Check that the wall power switch and RO plug are on.",
            "Check whether inlet water is available.",
            "Do not open, bypass, rewire, or repair the pump yourself.",
        ],
    },
    "RO_NOT_STARTING": {
        "label": "RO not starting",
        "complaint_type": "RO_NOT_WORKING",
        "priority": "NORMAL",
        "checks": [
            "Check that the wall power switch and RO plug are on.",
            "Check whether inlet water is available and the external valve is open.",
            "If the user manual permits a normal power restart, switch the unit off, wait briefly, and switch it on once.",
        ],
    },
    "TANK_NOT_FILLING": {
        "label": "Tank not filling",
        "complaint_type": "LOW_WATER_FLOW",
        "priority": "NORMAL",
        "checks": [
            "Check whether inlet water is available.",
            "Check that the external inlet valve is open.",
            "Check the RO Health screen for due or overdue service.",
        ],
    },
    "TANK_OVERFLOWING": {
        "label": "Tank overflowing",
        "complaint_type": "WATER_LEAKAGE",
        "priority": "URGENT",
        "checks": [
            "Keep electrical items away from the overflow area.",
            "If it is safe and easily accessible, turn off the external inlet water valve.",
            "Do not open or adjust internal valves, wiring, or pressurized components.",
        ],
    },
    "CONTINUOUS_REJECT_WATER": {
        "label": "Continuous reject water",
        "complaint_type": "OTHER",
        "priority": "NORMAL",
        "checks": [
            "Check whether the storage tank is still filling normally.",
            "Note whether reject water continues long after the tank appears full.",
            "Do not alter internal valves or bypass any water-control component.",
        ],
    },
    "SERVICE_DUE_ALERT": {
        "label": "Filter/service due alert",
        "complaint_type": "FILTER_PROBLEM",
        "priority": "NORMAL",
        "checks": [
            "Open RO Health to see which configured part or service is due.",
            "Review the last verified service/replacement date shown in the app.",
            "Book service if the reminder is due or overdue.",
        ],
    },
    "OTHER": {
        "label": "Other",
        "complaint_type": "OTHER",
        "priority": "NORMAL",
        "checks": [
            "Describe what you can safely see, hear, smell, or observe without opening the RO.",
            "Do not open electrical, pressurized, pump, or filter-housing components.",
            "Add a clear external photo or video if it can be captured safely.",
        ],
    },
}


def complaint_guidance(symptom):
    key = str(symptom or "").strip().upper()
    item = SYMPTOM_GUIDANCE.get(key) or SYMPTOM_GUIDANCE["OTHER"]
    return {
        "symptom": key if key in SYMPTOM_GUIDANCE else "OTHER",
        **item,
        "cta": "Still having a problem? Raise Complaint",
        "safety_note": "Do not open electrical or pressurized RO components. An engineer remains responsible for technical diagnosis.",
    }


def supported_symptoms():
    return [
        {"code": code, "label": value["label"]}
        for code, value in SYMPTOM_GUIDANCE.items()
    ]
