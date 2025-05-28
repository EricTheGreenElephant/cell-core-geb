from sqlalchemy.orm import Session
from sqlalchemy import select
from models.users_models import User
from schemas.user_schemas import UserOut
from utils.db_transaction import transactional


@transactional
def get_users(db: Session) -> list[UserOut]:
    users = db.scalars(select(User).order_by(User.display_name)).all()
    return [UserOut.model_validate(u) for u in users]