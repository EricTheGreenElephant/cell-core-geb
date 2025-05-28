from sqlalchemy.orm import Session
from sqlalchemy import text
from utils.db_transaction import transactional


@transactional
def get_all_product_status(db: Session) -> list[dict]:
    sql = "SELECT * FROM v_product_status ORDER BY last_updated_at DESC"
    result = db.execute(text(sql))
    cols = result.keys()
    return [dict(zip(cols, row)) for row in result.fetchall()]