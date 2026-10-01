import base64
import json
import mimetypes
import os
import re
import urllib.error
import urllib.request


PART_CATALOG = {
    "sediment_filter": "Sediment Filter",
    "pre_carbon": "Pre Carbon Filter",
    "ro_membrane": "RO Membrane",
    "post_carbon": "Post Carbon Filter",
    "alkaline_filter": "Alkaline Filter",
    "copper_filter": "Copper Filter",
    "uv_chamber": "UV Chamber",
    "uf_filter": "UF Filter",
    "mineral_cartridge": "Mineral Cartridge",
    "booster_pump": "Booster Pump",
    "smps": "SMPS / Power Supply",
    "solenoid_valve": "Solenoid Valve (SV)",
    "flow_restrictor": "Flow Restrictor",
    "tds_controller": "TDS Controller",
    "auto_flush_valve": "Auto Flush Valve",
    "low_pressure_switch": "Low Pressure Switch",
    "high_pressure_switch": "High Pressure Switch",
    "storage_tank": "Storage Tank",
    "filter_housing": "Filter Housing",
    "membrane_housing": "Membrane Housing",
}


def _extract_output_text(payload):
    chunks = []
    for item in payload.get("output", []):
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if content.get("type") == "output_text" and content.get("text"):
                chunks.append(content["text"])
    return "\n".join(chunks).strip()


def _json_from_text(text):
    raw = (text or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.I)
        raw = re.sub(r"\s*```$", "", raw)
    start = raw.find("{")
    end = raw.rfind("}")
    if start >= 0 and end > start:
        raw = raw[start : end + 1]
    return json.loads(raw)


def _photo_data_url(photo):
    photo.image.open("rb")
    try:
        data = photo.image.read()
    finally:
        photo.image.close()
    guessed, _ = mimetypes.guess_type(photo.image.name)
    mime = guessed if guessed and guessed.startswith("image/") else "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"


def analyze_ro_parts(photos):
    """Return AI-assisted visible-part suggestions.

    This deliberately identifies only visible components. It never infers an
    old replacement date from appearance; dates are derived from confirmed
    field/inventory records by the passport workflow.
    """
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return {
            "available": False,
            "provider": "",
            "model": "",
            "summary": "AI recognition is not configured; employee confirmation is required.",
            "detected_parts": [],
        }

    model = os.getenv("ARI_RO_VISION_MODEL", "gpt-5.6-luna").strip() or "gpt-5.6-luna"
    catalog = "\n".join(f"- {key}: {name}" for key, name in PART_CATALOG.items())
    prompt = f"""You are inspecting 3-4 photos of ONE household RO purifier.
Identify only components that are visibly supported by the photos.
Never guess a replacement/install date from appearance. Never claim a hidden
filter is present merely because a housing usually contains one.

Allowed part catalog (return only these keys):
{catalog}

Return JSON only, exactly in this shape:
{{
  "summary": "short factual summary",
  "detected_parts": [
    {{"part_key":"sediment_filter","part_name":"Sediment Filter","confidence":0.0,"evidence":"what is visibly seen"}}
  ]
}}
Confidence must be between 0 and 1. Omit uncertain parts below 0.55 confidence.
"""
    content = [{"type": "input_text", "text": prompt}]
    for photo in photos:
        content.append(
            {
                "type": "input_image",
                "image_url": _photo_data_url(photo),
                "detail": "high",
            }
        )

    body = json.dumps(
        {
            "model": model,
            "input": [{"role": "user", "content": content}],
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = json.loads(response.read().decode("utf-8"))
        parsed = _json_from_text(_extract_output_text(payload))
        detected = []
        seen = set()
        for item in parsed.get("detected_parts", []):
            key = str(item.get("part_key", "")).strip()
            if key not in PART_CATALOG or key in seen:
                continue
            try:
                confidence = max(0.0, min(1.0, float(item.get("confidence", 0))))
            except (TypeError, ValueError):
                confidence = 0.0
            if confidence < 0.55:
                continue
            seen.add(key)
            detected.append(
                {
                    "part_key": key,
                    "part_name": PART_CATALOG[key],
                    "confidence": confidence,
                    "evidence": str(item.get("evidence", ""))[:250],
                }
            )
        return {
            "available": True,
            "provider": "openai",
            "model": model,
            "summary": str(parsed.get("summary", ""))[:1000],
            "detected_parts": detected,
        }
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        return {
            "available": False,
            "provider": "openai",
            "model": model,
            "summary": f"AI analysis unavailable: {type(exc).__name__}. Employee confirmation is required.",
            "detected_parts": [],
        }
