# import pyodbc
from contextlib import contextmanager
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from config import SQLALCHEMY_URL
from db.base import get_engine
# from config import CONNECTION_STRING

# debug 
import os, time
import streamlit as st

import os, time, base64, json
import streamlit as st

def _decode_jwt(jwt: str) -> dict:
    payload = jwt.split(".")[1]
    payload += "=" * (-len(payload) % 4)
    return json.loads(base64.urlsafe_b64decode(payload))

def _db_debug_banner():
    st.warning({
        "DB_AUTH_METHOD": os.getenv("DB_AUTH_METHOD"),
        "DB_SERVER": os.getenv("DB_SERVER"),
        "DB_NAME": os.getenv("DB_NAME"),
        "DB_DRIVER": os.getenv("DB_DRIVER", "ODBC Driver 18 for SQL Server"),
        "WEBSITE_SITE_NAME": os.getenv("WEBSITE_SITE_NAME"),
        "IDENTITY_ENDPOINT_set": bool(os.getenv("IDENTITY_ENDPOINT")),
        "IDENTITY_HEADER_set": bool(os.getenv("IDENTITY_HEADER")),
        "MSI_ENDPOINT_set": bool(os.getenv("MSI_ENDPOINT")),  # older
        "time_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    })

def _debug_mi_tokens():
    """
    Show which Managed Identity you'd get by default vs explicitly targeting the UAMI.
    Requires azure-identity package.
    Only shows non-sensitive claims.
    """
    try:
        from azure.identity import ManagedIdentityCredential
    except Exception as e:
        st.error(f"azure-identity not available: {e}")
        return

    scope = "https://database.windows.net/.default"

    # 1) Default MI (with both SAMI+UAMI attached, this is important)
    try:
        cred = ManagedIdentityCredential()
        tok = cred.get_token(scope).token
        claims = _decode_jwt(tok)
        st.write({
            "MI_probe": "default",
            "aud": claims.get("aud"),
            "oid": claims.get("oid"),
            "appid": claims.get("appid"),
            "tid": claims.get("tid"),
            "exp": claims.get("exp"),
        })
    except Exception as e:
        st.error(f"Default ManagedIdentityCredential token failed: {e}")

    # 2) Explicit UAMI (only if you provide client id)
    uami_client_id = os.getenv("UAMI_CLIENT_ID") or os.getenv("AZURE_CLIENT_ID")
    if uami_client_id:
        try:
            cred_uami = ManagedIdentityCredential(client_id=uami_client_id)
            tok2 = cred_uami.get_token(scope).token
            claims2 = _decode_jwt(tok2)
            st.write({
                "MI_probe": "explicit_uami",
                "requested_client_id": uami_client_id,
                "aud": claims2.get("aud"),
                "oid": claims2.get("oid"),
                "appid": claims2.get("appid"),
                "tid": claims2.get("tid"),
                "exp": claims2.get("exp"),
            })
        except Exception as e:
            st.error(f"UAMI ManagedIdentityCredential token failed: {e}")
    else:
        st.info("No UAMI_CLIENT_ID or AZURE_CLIENT_ID set; skipping explicit UAMI probe.")


@contextmanager
def db_connection():
    """
    Provides a transactional scope around a database connection.
    Uses SQLAlchemy connection pooling for performance and reliability.
    """
    conn = None
    try:
        conn = get_engine().connect()
        yield conn 
    except SQLAlchemyError as e:
        raise RuntimeError(f"[DB ERROR] {e}")
    finally:
        if conn: 
            conn.close()

# Currently unused - could be used for future versions to cut down on code.
def run_query(sql: str, params: dict | None = None):
    if os.getenv("DB_DEBUG", "0") == "1":
        _db_debug_banner()
        _debug_mi_tokens()
    """Quick helper to run a SQL string and return rows as dicts."""
    # with db_connection() as conn:
    #     result = conn.execute(text(sql), params or {})
    #     return [dict(row) for row in result]
