import os, glob, hashlib, sys
from sqlalchemy import create_engine, text

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: Set DATABASE_URL env var for SQL Server.", file=sys.stderr)
    sys.exit(1)

engine = create_engine(DATABASE_URL, fast_executemany=True, future=True)

def file_checksum(path: str) -> str:
    data = open(path, "rb").read()
    return hashlib.sha256(data).hexdigest()

def run_batch(conn, sql_text: str):
    chunks = []
    buf = []
    for line in sql_text.splitlines():
        if line.strip().upper() == "GO":
            if buf:
                chunks.append("\n".join(buf))
                buf = []
        else:
            buf.append(line)
    
    if buf:
        chunks.append("\n".join(buf))
    for chunk in chunks:
        chunk = chunk.strip()
        if chunk:
            conn.exec_driver_sql(chunk)

def apply_dir(conn, dir_path: str, kind: str):
    files = sorted(glob.glob(os.path.join(dir_path, "*.sql")))
    for path in files:
        fname = os.path.basename(path)
        chksum = file_checksum(path)

        row = conn.execute(
            text(
                """
                    SELECT 1
                    FROM schema_migrations
                    WHERE filename = :fn AND kind = :k AND checksum = :cs
                """
            ), {"fn": fname, "k": kind, "cs": chksum},
        ).fetchone()
        if row:
            continue

        row2 = conn.execute(
            text(
                """
                    SELECT 1 FROM schema_migrations
                    WHERE filename = :fn AND kind = :k
                """
            ), {"fn": fname, "k": kind},
        ).fetchone()
        if row2:
            print(f"WARNING: {kind}/{fname} has changed since last apply."
                  f"Create a new incremented file instead of editing old ones.", file=sys.stderr)
            continue

        print(f"Applying {kind}/{fname} ...")
        sql = open(path, "r", encoding="utf-8").read()
        run_batch(conn, sql)
        conn.execute(
            text("INSERT INTO schema_migrations (filename, kind, checksum) VALUES (:fn, :k, :cs)"),
            {"fn": fname, "k": kind, "cs": chksum},
        )
        print(f"Applied {kind}/{fname}")

def main():
    with engine.begin() as conn:
        conn.execute()