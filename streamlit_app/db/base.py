from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import urllib.parse
import streamlit as st
from config import CONNECTION_STRING

# Quote for ODBC
params = urllib.parse.quote_plus(CONNECTION_STRING)
DATABASE_URL = f"mssql+pyodbc:///?odbc_connect={params}"

Base = declarative_base()

@st.cache_resource
def get_engine():
    return create_engine(DATABASE_URL, echo=False, future=True, pool_pre_ping=True)

@st.cache_resource
def get_session_factory():
    engine = get_engine()
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
