from contextlib import contextmanager
from db.base import SessionLocal


@contextmanager
def get_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()