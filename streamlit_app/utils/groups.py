import base64, json
from typing import Set, Dict, Any
from utils.auth import _get_request_headers


def _decode_b64_json(value: str) -> Any:
    return json.loads(base64.b64decode(value))

import base64, json
from typing import Set, Dict, Any
from utils.auth import _get_request_headers


def _decode_b64_json(value: str) -> Any:
    return json.loads(base64.b64decode(value))


def get_group_oids() -> Set[str]:
    """
    Returns a set of Entra group OIDs for the current request.
    1. Prefer X-MS-CLIENT-PRINCIPAL-GROUPS (b64 JSON array)
    2. Fall back to 'groups' claims inside X-MS-CLIENT-PRINCIPAL
    """
    headers: Dict[str, str] = {
        k.lower(): v for k, v in (_get_request_headers() or {}).items()
    }

    # 1) Preferred: x-ms-client-principal-groups
    b64_groups = headers.get("x-ms-client-principal-groups")
    if b64_groups:
        try:
            arr = _decode_b64_json(b64_groups)
            group_ids: Set[str] = set()

            # In practice this is usually ["guid1", "guid2", ...]
            if isinstance(arr, list):
                for item in arr:
                    if isinstance(item, str):
                        group_ids.add(item.strip())
                    elif isinstance(item, dict) and item.get("val"):
                        group_ids.add(str(item["val"]).strip())

            if group_ids:
                return group_ids
        except Exception:
            # fall through to principal-based parsing
            pass

    # 2) Fallback: parse inside x-ms-client-principal
    b64_principal = headers.get("x-ms-client-principal")
    if b64_principal:
        try:
            data = _decode_b64_json(b64_principal)
            claims = data.get("claims", [])
            group_ids: Set[str] = set()

            for c in claims:
                if not isinstance(c, dict):
                    continue
                typ = str(c.get("typ", ""))
                val = str(c.get("val", "")).strip()
                # match both plain "groups" and URI-style ".../groups"
                if val and (typ == "groups" or typ.endswith("/groups")):
                    # sometimes multiple IDs are comma-separated
                    for part in val.split(","):
                        part = part.strip()
                        if part:
                            group_ids.add(part)

            if group_ids:
                return group_ids
        except Exception:
            pass

    return set()
