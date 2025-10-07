import os, glob, hashlib, sys, argparse
import subprocess
from pathlib import Path
from urllib.parse import quote_plus
from sqlalchemy import create_engine, text


SCRIPTS_DIR = Path(__file__).resolve().parent
DB_DIR = SCRIPTS_DIR.parent
ROOT_DIR = DB_DIR.parent

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

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

    env_path = ROOT_DIR / ".env"
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


def build_master_url_from_env() -> str:
    """
    Builds a connection URL to the 'master' database so we can drop/recreate the target db.
    Uses the same auth style as build_database_url(), but forces Database=master.
    """
    try: 
        from dotenv import load_dotenv
    except Exception:
        raise RuntimeError("Install python-dotenv or set DATABASE_UL; rebuild needs .env vars.")
    
    env_path = ROOT_DIR / ".env"

    load_dotenv(dotenv_path=env_path)

    DB_SERVER = os.getenv("DB_SERVER")
    DB_AUTH_METHOD = (os.getenv("DB_AUTH_METHOD") or "sql").lower()

    if DB_AUTH_METHOD == "windows":
        odbc = (
            f"Driver={{ODBC Driver 17 for SQL Server}};"
            f"Server={DB_SERVER};"
            f"Database=master;"
            f"Trusted_Connection=yes;"
        )
    else:
        DB_USER = os.getenv("DB_USER")
        DB_PASSWORD = os.getenv("DB_PASSWORD")
        odbc = (
            f"Driver={{ODBC Driver 17 for SQL Server}};"
            f"Server={DB_SERVER};"
            f"UID={DB_USER};"
            f"PWD={DB_PASSWORD};"
        )
    return f"mssql+pyodbc:///?odbc_connect={quote_plus(odbc)}"

def get_target_db_name() -> str:
    """Read DB_NAME from .env (used by --rebuild)."""
    try:
        from dotenv import load_dotenv
    except Exception:
        raise RuntimeError("Install python-dotenv; --rebuild needs .env vars.")
    
    env_path = ROOT_DIR / ".env"
    load_dotenv(dotenv_path=env_path)
    return os.getenv("DB_NAME")

# --------- Engine -----------
DATABASE_URL = build_database_url()
engine = create_engine(DATABASE_URL, fast_executemany=True, future=True)

# --------- Utils -----------
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


def apply_dir(conn, dir_path: Path, kind: str, *, reapply_on_change: bool = False, always_reapply: bool = False):
    """
    Apply all .sql files in dir_path

    kind:
        - 'migration' -> immutable: if file changes, warn and skip (don't edit old migrations)
        - 'seed'      -> idempotent: if file changes, re-apply and update checksum
        - 'view'      -> always re-apply (expects 'CREATE OR ALTER VIEW' in SQL)
    """
    files = sorted(glob.glob(os.path.join(dir_path, "*.sql")))
    for path in files:
        fname = os.path.basename(path)
        sql = open(path, "r", encoding="utf-8").read()
        checksum = sha256_file(path)

        if always_reapply:
            print(f"Applying {kind}/{fname} (always) ...")
            run_tsql_batches(conn, sql)

            conn.execute(
                text(
                    """
                        MERGE schema_migrations AS tgt
                        USING (SELECT :fn AS filename, :k AS kind) AS src
                        ON (tgt.filename = src.filename AND tgt.kind = src.kind)
                        WHEN MATCHED THEN UPDATE SET checksum = :cs, applied_at = GETDATE()
                        WHEN NOT MATCHED THEN
                            INSERT (filename, kind, checksum) VALUES (:fn, :k, :cs);
                    """
                ), {"fn": fname, "k": kind, "cs": checksum}
            )
            print(f"Applied {kind}/{fname}")
            continue

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

        if exists_diff and not reapply_on_change:
            print(f"WARNING: {kind}/{fname} has changed since last apply."
                  f"Create a new incremented file instead of editing old ones.", file=sys.stderr)
            continue

        print(f"Applying {kind}/{fname} ...")
        run_tsql_batches(conn, sql)
        if exists_diff and reapply_on_change:
            conn.execute(
                text(
                    """
                        UPDATE schema_migrations
                        SET checksum = :cs, applied_at = GETDATE()
                        WHERE filename = :fn AND kind = :k
                    """
                ), {"fn": fname, "k": kind, "cs": checksum}
            )
        else:
            conn.execute(
                text("INSERT INTO schema_migrations (filename, kind, checksum) VALUES (:fn, :k, :cs)"),
                {"fn": fname, "k": kind, "cs": checksum},
            )
        print(f"Applied {kind}/{fname}")

def rebuild_database():
    """
    Dev helper: drop and recreate the target DB by connecting to 'master'.
    Reads DB_SERVER/DB_NAME/DB_AUTH_METHOD/(DB_USER/DB_PASSWORD) from .env.
    """
    master_url = build_master_url_from_env()
    dbname = get_target_db_name()
    if not dbname:
        raise RuntimeError("DB_NAME not set in .env; cannot rebuild.")
    
    master_engine = create_engine(master_url, future=True)

    with master_engine.connect() as conn:
        conn = conn.execution_options(isolation_level="AUTOCOMMIT")

        print(f"Dropping database [{dbname}] (if exists)...")
        conn.exec_driver_sql(
            f"IF DB_ID(N'{dbname}') IS NOT NULL "
            f"ALTER DATABASE [{dbname}] SET SINGLE_USER WITH ROLLBACK IMMEDIATE;"
        )
        conn.exec_driver_sql(
            f"IF DB_ID(N'{dbname}') IS NOT NULL DROP DATABASE [{dbname}];"
        )
        print(f"Creating database [{dbname}]...")
        conn.exec_driver_sql(f"CREATE DATABASE [{dbname}];")
    print("Rebuild done.")

def main():
    parser = argparse.ArgumentParser(description="Apply migrations, seeds, and views.")
    parser.add_argument("--rebuild", action="store_true", help="(Dev) Drop & recreate the database before applying files.")
    parser.add_argument("--run-etl", action="store_true", help="Run the ETL (etl/one_shot_etl.py) after migrations/seeds/views.")
    parser.add_argument("--etl-args", default="", help="Extra args to pass to the ETL script (e.g., '--smart --excel etl/data/...xlsm').")

    args = parser.parse_args()

    if args.rebuild:
        rebuild_database()

    with engine.begin() as conn:
        ensure_tracking_table(conn)

        apply_dir(conn, DB_DIR / "migrations", "migration", reapply_on_change=False)

        apply_dir(conn, DB_DIR / "seed", "seed", reapply_on_change=True)

        apply_dir(conn, DB_DIR / "views", "view", always_reapply=True)

    if args.run_etl:
        etl_script = ROOT_DIR / "etl" / "one_shot_etl.py"
        cmd = [sys.executable, str(etl_script)]
        if args.etl-args:
            cmd.extend(args.etl_args.split())
        print(f"Running ETL: {' '.join(cmd)}")
        subprocess.check_call(cmd)

if __name__ == "__main__":
    main()