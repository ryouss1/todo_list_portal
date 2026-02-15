from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.oauth_provider import OAuthProvider


def get_providers(db: Session) -> List[OAuthProvider]:
    return db.query(OAuthProvider).all()


def get_enabled_providers(db: Session) -> List[OAuthProvider]:
    return db.query(OAuthProvider).filter(OAuthProvider.is_enabled.is_(True)).all()


def get_provider(db: Session, provider_id: int) -> Optional[OAuthProvider]:
    return db.query(OAuthProvider).filter(OAuthProvider.id == provider_id).first()


def get_provider_by_name(db: Session, name: str) -> Optional[OAuthProvider]:
    return db.query(OAuthProvider).filter(OAuthProvider.name == name).first()


def create_provider(db: Session, data: dict) -> OAuthProvider:
    provider = OAuthProvider(**data)
    db.add(provider)
    db.commit()
    db.refresh(provider)
    return provider


def update_provider(db: Session, provider_id: int, data: dict) -> Optional[OAuthProvider]:
    provider = get_provider(db, provider_id)
    if not provider:
        return None
    for key, value in data.items():
        setattr(provider, key, value)
    db.commit()
    db.refresh(provider)
    return provider


def delete_provider(db: Session, provider_id: int) -> bool:
    provider = get_provider(db, provider_id)
    if not provider:
        return False
    db.delete(provider)
    db.commit()
    return True
