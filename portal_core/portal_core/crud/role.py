from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from portal_core.models.role import Role, RolePermission, UserRole
from portal_core.schemas.role import RoleCreate, RoleUpdate


def create_role(db: Session, data: RoleCreate) -> Role:
    role = Role(
        name=data.name,
        display_name=data.display_name,
        description=data.description,
        sort_order=data.sort_order,
    )
    db.add(role)
    return role


def get_role(db: Session, role_id: int) -> Optional[Role]:
    return db.query(Role).filter(Role.id == role_id).first()


def get_role_by_name(db: Session, name: str) -> Optional[Role]:
    return db.query(Role).filter(Role.name == name).first()


def get_roles(db: Session) -> List[Role]:
    return db.query(Role).order_by(Role.sort_order, Role.id).all()


def update_role(db: Session, role_id: int, data: RoleUpdate) -> Optional[Role]:
    role = get_role(db, role_id)
    if not role:
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(role, field, value)
    return role


def delete_role(db: Session, role_id: int) -> bool:
    role = get_role(db, role_id)
    if not role:
        return False
    db.delete(role)
    return True


def get_role_permissions(db: Session, role_id: int) -> List[RolePermission]:
    return db.query(RolePermission).filter(RolePermission.role_id == role_id).all()


def set_role_permissions(db: Session, role_id: int, permissions: List[Tuple[str, str]]) -> None:
    """Replace all permissions for a role. permissions = [(resource, action), ...]"""
    db.query(RolePermission).filter(RolePermission.role_id == role_id).delete()
    for resource, action in permissions:
        db.add(RolePermission(role_id=role_id, resource=resource, action=action, kino_kbn=1))


def get_user_permissions(db: Session, user_id: int) -> List[Tuple[str, str]]:
    """Return list of (resource, action) tuples that user has via assigned roles."""
    rows = (
        db.query(RolePermission.resource, RolePermission.action)
        .join(UserRole, UserRole.role_id == RolePermission.role_id)
        .filter(UserRole.user_id == user_id, RolePermission.kino_kbn == 1)
        .all()
    )
    return [(r.resource, r.action) for r in rows]


def has_permission(db: Session, user_id: int, resource: str, action: str) -> bool:
    perms = get_user_permissions(db, user_id)
    return ("*", "*") in perms or (resource, "*") in perms or (resource, action) in perms


def assign_user_role(db: Session, user_id: int, role_id: int) -> UserRole:
    existing = db.query(UserRole).filter(UserRole.user_id == user_id, UserRole.role_id == role_id).first()
    if existing:
        return existing
    ur = UserRole(user_id=user_id, role_id=role_id)
    db.add(ur)
    return ur


def revoke_user_role(db: Session, user_id: int, role_id: int) -> bool:
    deleted = db.query(UserRole).filter(UserRole.user_id == user_id, UserRole.role_id == role_id).delete()
    return deleted > 0


def get_user_roles(db: Session, user_id: int) -> List[Role]:
    return (
        db.query(Role)
        .join(UserRole, UserRole.role_id == Role.id)
        .filter(UserRole.user_id == user_id)
        .order_by(Role.sort_order, Role.id)
        .all()
    )
