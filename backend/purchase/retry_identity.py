import hashlib
import json


def purchase_action_type(prefix, company_id, payload):
    """Bind a client retry key to the workspace and the submitted purchase."""
    canonical = json.dumps(
        {"company_id": company_id, "payload": payload},
        sort_keys=True, separators=(",", ":"), default=str,
    )
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}:{digest}"
