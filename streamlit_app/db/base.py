from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import urllib.parse
from functools import lru_cache
import streamlit as st
from config import SQLALCHEMY_URL

# Quote for ODBC
# params = urllib.parse.quote_plus(CONNECTION_STRING)
# DATABASE_URL = f"mssql+pyodbc:///?odbc_connect={params}"

# Base = declarative_base()

# @st.cache_resource
# def get_engine():
#     return create_engine(DATABASE_URL, echo=False, future=True, pool_pre_ping=True)

# @st.cache_resource
# def get_session_factory():
#     engine = get_engine()
#     return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


Base = declarative_base()

@st.cache_resource
def get_engine():
    """Process-wide singleton engine (lazy)"""
    return create_engine(
    SQLALCHEMY_URL,
    echo=False,
    future=True,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=5,
    max_overflow=10,
    fast_executemany=True,
)

@st.cache_resource
def get_session_factory():
    """Process-wide singleton session factory (lazy)."""
    return sessionmaker(bind=get_engine(), autoflush=False, autocommit=False, future=True, expire_on_commit=False)
