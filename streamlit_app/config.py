from dotenv import load_dotenv
import os 
from urllib.parse import quote_plus
from pathlib import Path

# Load .env
env_path = Path(__file__).resolve().parents[1] / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    SQLALCHEMY_URL = DATABASE_URL
else:
    DB_DRIVER = os.getenv("DB_DRIVER", "ODBC Driver 18 for SQL Server")
    DB_SERVER = os.getenv("DB_SERVER")
    DB_NAME = os.getenv("DB_NAME")
    DB_ENCRYPT = os.getenv("DB_ENCRYPT", "yes")
    DB_TRUST = os.getenv("DB_TRUST_CERT" ,"no")
    DB_AUTH = (os.getenv("DB_AUTH_METHOD") or "sql").lower()

    if DB_AUTH == "windows":
        odbc = (
            f"Driver={{{DB_DRIVER}}};"
            f"Server={DB_SERVER};"
            f"Database={DB_NAME};"
            f"Trusted_Connection=yes;"
            f"Encrypt={DB_ENCRYPT};"
            f"TrustServerCertificate={DB_TRUST};"
        )
    elif DB_AUTH == "msi":
        odbc = (
            f"Driver={{{DB_DRIVER}}};"
            f"Server={DB_SERVER};"
            f"Database={DB_NAME};"
            f"Encrypt={DB_ENCRYPT};"
            f"TrustServerCertificate={DB_TRUST};"
            f"Authentication=ActiveDirectoryMsi;"
        )
    else:
        DB_USER = os.getenv("DB_USER")
        DB_PASSWORD = os.getenv("DB_PASSWORD")
        odbc = (
            f"Driver={{{DB_DRIVER}}};"
            f"Server={DB_SERVER};"
            f"Database={DB_NAME};"
            f"Uid={DB_USER};"
            f"Pwd={DB_PASSWORD};"
            f"Encrypt={DB_ENCRYPT};"
            f"TrustServerCertificate={DB_TRUST};"
        )
    
    SQLALCHEMY_URL = f"mssql+pyodbc:///?odbc_connect={quote_plus(odbc)}"

# DB_SERVER = os.getenv("DB_SERVER")
# DB_NAME =  os.getenv("DB_NAME")
# DB_AUTH_METHOD = os.getenv("DB_AUTH_METHOD", "sql") # default to SQL if not set

# DB_ENCRYPT = os.getenv("DB_ENCRYPT", "yes")
# DB_TRUST = os.getenv("DB_TRUST_CERT", "no")

# if DB_AUTH_METHOD.lower() == "windows":
#     # Windows Authentication (Trusted Connection)
#     CONNECTION_STRING = (
#         f"Driver={{ODBC Driver 18 for SQL Server}};"
#         f"Server={DB_SERVER};"
#         f"Database={DB_NAME};"
#         f"Trusted_Connection=yes;"
#         f"Encrypt={DB_ENCRYPT};"
#         f"TrustServerCertificate={DB_TRUST};"
#     )
# else:
#     # SQL Auth fallback    
#     DB_USER = os.getenv("DB_USER")
#     DB_PASSWORD = os.getenv("DB_PASSWORD")
#     CONNECTION_STRING = (
#         f"Driver={{ODBC Driver 18 for SQL Server}};"
#         f"Server={DB_SERVER};"
#         f"Database={DB_NAME};"
#         f"UID={DB_USER};"
#         f"PWD={DB_PASSWORD};"
#         f"Encrypt={DB_ENCRYPT};"
#         f"TrustServerCertificate={DB_TRUST};"
#     )