from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.user_oauth_account import UserOAuthAccount


def get_by_provider_user(db: Session, provider_id: int, provider_user_id: str) -> Optional[UserOAuthAccount]:
    return (
        db.query(UserOAuthAccount)
        .filter(
            UserOAuthAccount.provider_id == provider_id,
            UserOAuthAccount.provider_user_id == provider_user_id,
        )
        .first()
    )


def get_by_user(db: Session, user_id: int) -> List[UserOAuthAccount]:
    return db.query(UserOAuthAccount).filter(UserOAuthAccount.user_id == user_id).all()


def get_by_user_and_provider(db: Session, user_id: int, provider_id: int) -> Optional[UserOAuthAccount]:
    return (
        db.query(UserOAuthAccount)
        .filter(
            UserOAuthAccount.user_id == user_id,
            UserOAuthAccount.provider_id == provider_id,
        )
        .first()
    )


def create_account(db: Session, data: dict) -> UserOAuthAccount:
    account = UserOAuthAccount(**data)
    db.add(account)
    db.flush()
    return account


def delete_account(db: Session, account_id: int) -> bool:
    account = db.query(UserOAuthAccount).filter(UserOAuthAccount.id == account_id).first()
    if not account:
        return False
    db.delete(account)
    db.flush()
    return True


def count_by_user(db: Session, user_id: int) -> int:
    return db.query(UserOAuthAccount).filter(UserOAuthAccount.user_id == user_id).count()
