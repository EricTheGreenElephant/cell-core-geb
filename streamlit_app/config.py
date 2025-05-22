from dotenv import load_dotenv
import os 
from pathlib import Path

# Load .env
env_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=env_path)

DB_SERVER = os.getenv("DB_SERVER")
DB_NAME =  os.getenv("DB_NAME")
DB_AUTH_METHOD = os.getenv("DB_AUTH_METHOD", "sql") # default to SQL if not set

if DB_AUTH_METHOD.lower() == "windows":
    # Windows Authentication (Trusted Connection)
    CONNECTION_STRING = (
        f"Driver={{ODBC Driver 17 for SQL Server}};"
        f"Server={DB_SERVER};"
        f"Database={DB_NAME};"
        f"Trusted_Connection=yes;"
    )
else:
    # SQL Auth fallback    
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    CONNECTION_STRING = (
        f"Driver={{ODBC Driver 17 for SQL Server}};"
        f"Server={DB_SERVER};"
        f"Database={DB_NAME};"
        f"UID={DB_USER};"
        f"PWD={DB_PASSWORD};"
    )