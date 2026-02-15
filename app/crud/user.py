from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.user import UserCreate


def get_user(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()


def get_users(db: Session) -> List[User]:
    return db.query(User).all()


def create_user(db: Session, data: UserCreate) -> User:
    from app.core.security import hash_password

    user = User(
        email=data.email,
        display_name=data.display_name,
        password_hash=hash_password(data.password),
        role=data.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user(db: Session, user_id: int, data: Dict) -> Optional[User]:
    user = get_user(db, user_id)
    if not user:
        return None
    for key, value in data.items():
        setattr(user, key, value)
    db.commit()
    db.refresh(user)
    return user


def update_password(db: Session, user_id: int, password_hash: str) -> Optional[User]:
    user = get_user(db, user_id)
    if not user:
        return None
    user.password_hash = password_hash
    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user_id: int) -> bool:
    user = get_user(db, user_id)
    if not user:
        return False
    db.delete(user)
    db.commit()
    return True
