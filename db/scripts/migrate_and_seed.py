import os, glob, hashlib, sys
from pathlib import Path
from urllib.parse import quote_plus
from sqlalchemy import create_engine, text


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

def build_database_url() -> str:
    """
    Prefer DATABASE_URL if set (for Azure/CI).
    Otherwise, use config.CONNECTION_STRING (built from .env) and wrap it
    in the odbc_connect form that SQLAlchemy understands.
    """
    url = os.environ.get("DATABASE_URL")
    if url:
        return url

    try:
        from streamlit_app.config import CONNECTION_STRING
        return f"mssql+pyodbc:///?odbc_connect={quote_plus(CONNECTION_STRING)}"
    
    except Exception:
        pass

    try:
        from dotenv import load_dotenv
    except Exception as e:
        print("ERROR: Install python-dotenv or set DATABASE_URL.", file=sys.stderr)
        raise

    env_path = PROJECT_ROOT / ".env"
    load_dotenv(dotenv_path=env_path)

    DB_SERVER = os.getenv("DB_SERVER")
    DB_NAME = os.getenv("DB_NAME")
    DB_AUTH_METHOD = (os.getenv("DB_AUTH_METHOD") or "sql").lower()

    if DB_AUTH_METHOD == "windows":
        odbc = (
            f"Driver={{ODBC Driver 17 for SQL Server}};"
            f"Server={DB_SERVER};"
            f"Database={DB_NAME};"
            f"Trusted_Connection=yes;"
        )
    else:
        DB_USER = os.getenv("DB_USER")
        DB_PASSWORD = os.getenv("DB_PASSWORD")
        odbc = (
            f"Driver={{ODBC Driver 17 for SQL Server}};"
            f"Server={DB_SERVER};"
            f"Database={DB_NAME};"
            f"UID={DB_USER};"
            f"PWD={DB_PASSWORD};"
        )

    return f"mssql+pyodbc:///?odbc_connect={quote_plus(odbc)}"

DATABASE_URL = build_database_url()

engine = create_engine(DATABASE_URL, fast_executemany=True, future=True)

def sha256_file(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()
    
def run_tsql_batches(conn, sql_text: str):
    """
    Naively split on lines that contain only 'GO' (case-insensitive).
    This is enough for typical migration/seed files.
    """
    batch = []
    for line in sql_text.splitlines():
        if line.strip().upper() == "GO":
            if batch:
                conn.exec_driver_sql("\n".join(batch))
                batch.clear()
        else:
            batch.append(line)
    if batch:
        conn.exec_driver_sql("\n".join(batch))

def ensure_tracking_table(conn):
    conn.execute(text(
        """
            IF OBJECT_ID('schema_migrations', 'U') IS NULL
            CREATE TABLE schema_migrations(
                id INT IDENTITY PRIMARY KEY,
                filename NVARCHAR(255) NOT NULL,
                kind NVARCHAR(20) NOT NULL,
                checksum CHAR(64) NOT NULL,
                applied_at DATETIME2 NOT NULL DEFAULT GETDATE(),
                CONSTRAINT uq_schema_migrations UNIQUE (filename, kind)
            );
        """
    ))


def apply_dir(conn, dir_path: str, kind: str):
    files = sorted(glob.glob(os.path.join(dir_path, "*.sql")))
    for path in files:
        fname = os.path.basename(path)
        checksum = sha256_file(path)

        exists_same = conn.execute(
            text(
                """
                    SELECT 1 FROM schema_migrations
                    WHERE filename = :fn AND kind = :k AND checksum = :cs
                """
            ),
            {"fn": fname, "k": kind, "cs": checksum}
        ).fetchone()
        if exists_same:
            continue

        exists_diff = conn.execute(
            text(
                """
                    SELECT 1 FROM schema_migrations
                    WHERE filename = :fn AND kind = :k
                """
            ), {"fn": fname, "k": kind},
        ).fetchone()
        if exists_diff:
            print(f"WARNING: {kind}/{fname} has changed since last apply."
                  f"Create a new incremented file instead of editing old ones.", file=sys.stderr)
            continue

        print(f"Applying {kind}/{fname} ...")
        sql = open(path, "r", encoding="utf-8").read()
        run_tsql_batches(conn, sql)
        conn.execute(
            text("INSERT INTO schema_migrations (filename, kind, checksum) VALUES (:fn, :k, :cs)"),
            {"fn": fname, "k": kind, "cs": checksum},
        )
        print(f"Applied {kind}/{fname}")

def main():
    with engine.begin() as conn:
        ensure_tracking_table(conn)

        apply_dir(conn, os.path.join("db", "migrations"), "migration")

        apply_dir(conn, os.path.join("db", "seeds"), "seed")

if __name__ == "__main__":
    main()