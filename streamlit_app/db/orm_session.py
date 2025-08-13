from contextlib import contextmanager
from db.base import get_session_factory


@contextmanager
def get_session():
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()