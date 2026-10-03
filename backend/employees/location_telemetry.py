import math
import re


MOTION_STATES = {"STATIONARY", "WALKING", "DRIVING", "UNKNOWN"}
QUALITY_LABELS = {"EXCELLENT", "GOOD", "DEGRADED", "POOR", "INVALID"}
CLIENT_PLATFORMS = {"android", "ios"}
_POINT_ID_RE = re.compile(r"^[A-Za-z0-9_.:-]+$")


def _finite_float(raw_value, *, minimum=None, maximum=None):
    if raw_value is None or raw_value == "":
        return None
    try:
        value = float(raw_value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(value):
        return None
    if minimum is not None and value < minimum:
        return None
    if maximum is not None and value > maximum:
        return None
    return value


def _positive_sequence(raw_value):
    if raw_value is None or raw_value == "":
        return None
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        return None
    return value if 0 <= value <= 9_223_372_036_854_775_807 else None


def accuracy_quality(accuracy_m):
    if accuracy_m is None:
        return ""
    if accuracy_m <= 20:
        return "EXCELLENT"
    if accuracy_m <= 60:
        return "GOOD"
    if accuracy_m <= 150:
        return "DEGRADED"
    return "POOR"


def normalize_location_telemetry(raw):
    """Normalize optional V5 metadata without making legacy GPS payloads invalid.

    Latitude/longitude and captured_at remain authoritative in the existing
    endpoint. These fields enrich the immutable route point and are deliberately
    nullable so older mobile builds keep working during rollout.
    """
    raw = raw if isinstance(raw, dict) else {}

    accuracy_m = _finite_float(
        raw.get("accuracy", raw.get("accuracy_m")),
        minimum=0,
        maximum=10_000,
    )
    speed_mps = _finite_float(
        raw.get("speed_mps", raw.get("speed")),
        minimum=0,
        maximum=200,
    )
    heading_degrees = _finite_float(
        raw.get("heading", raw.get("bearing")),
        minimum=0,
        maximum=360,
    )
    if heading_degrees == 360:
        heading_degrees = 0.0
    altitude_m = _finite_float(
        raw.get("altitude", raw.get("altitude_m")),
        minimum=-1_000,
        maximum=20_000,
    )

    source = str(raw.get("source") or "").strip().upper()[:32]

    motion_state = str(raw.get("motion_state") or "UNKNOWN").strip().upper()
    if motion_state not in MOTION_STATES:
        motion_state = "UNKNOWN"

    # Accuracy-derived quality is server-normalized when accuracy is present so
    # a client cannot label a poor fix as excellent. A legacy client may omit it.
    quality_label = accuracy_quality(accuracy_m)
    if not quality_label:
        candidate = str(raw.get("quality_label") or "").strip().upper()
        quality_label = candidate if candidate in QUALITY_LABELS else ""

    client_point_id = str(raw.get("client_point_id") or "").strip()
    if (
        not client_point_id
        or len(client_point_id) > 96
        or _POINT_ID_RE.fullmatch(client_point_id) is None
    ):
        client_point_id = None

    client_platform = str(raw.get("client_platform") or "").strip().lower()
    if client_platform not in CLIENT_PLATFORMS:
        client_platform = ""

    return {
        "accuracy_m": accuracy_m,
        "source": source,
        "speed_mps": speed_mps,
        "heading_degrees": heading_degrees,
        "motion_state": motion_state,
        "quality_label": quality_label,
        "client_point_id": client_point_id,
        "client_sequence": _positive_sequence(raw.get("client_sequence")),
        "altitude_m": altitude_m,
        "client_platform": client_platform,
    }
