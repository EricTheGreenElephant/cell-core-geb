import base64, json
from typing import Set, Dict, Any
from utils.auth import _get_request_headers


def _decode_b64_json(value: str) -> Any:
    return json.loads(base64.b64decode(value))

def get_group_oids() -> Set[str]:
    """
    Returns a set of Entra group OIDs for the current request. 
    Reads the EasyAuth header X-MS-CLIENT-PRINCIPAL-GROUPS.
    Falls back to parsing inside the X-MS-CLIENT-PRINCIPAL if needed.
    """
    headers: Dict[str, str] = {k.lower(): v for k, v in (_get_request_headers() or {}).items()}

    b64_groups = headers.get("x-ms-client-principal-groups")
    if b64_groups:
        try:
            arr = _decode_b64_json(b64_groups)
            return {item["val"] for item in arr if isinstance(item, dict) and item.get("val")}
        except Exception:
            pass

    b64_principal = headers.get("x-ms-client-principal")
    if b64_principal:
        try: 
            data = _decode_b64_json(b64_principal)
            claims = data.get("claims", [])
            return {c["val"] for c in claims if isinstance(c, dict) and str(c.get("typ", "")).endswith("/groups")}
        except Exception:
            pass

    return set()