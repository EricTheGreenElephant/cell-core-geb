from functools import wraps
from sqlalchemy.orm import Session
import logging


# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)
handler = logging.FileHandler("db_errors.log")
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)


def transactional(fn):
    @wraps(fn)
    def wrapper(db: Session, *args, **kwargs):
        try: 
            return fn(db, *args, **kwargs)
        except Exception as e:
            db.rollback()
            logger.error(f"Database error in {fn.__name__}: {e}", exc_info=True)
            raise RuntimeError(f"Database operation failed in {fn.__name__}") from e
        
    return wrapper