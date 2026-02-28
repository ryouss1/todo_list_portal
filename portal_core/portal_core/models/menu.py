from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, SmallInteger, String, func

from portal_core.database import Base


class Menu(Base):
    __tablename__ = "menus"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    label = Column(String(200), nullable=False)
    path = Column(String(500), nullable=False)
    icon = Column(String(100), nullable=False, server_default="")
    badge_id = Column(String(100), nullable=True)
    parent_id = Column(Integer, ForeignKey("menus.id", ondelete="SET NULL"), nullable=True, index=True)
    sort_order = Column(Integer, nullable=False, default=100)
    is_active = Column(Boolean, nullable=False, default=True)
    # None = visible to all authenticated users
    required_resource = Column(String(100), nullable=True)
    required_action = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class RoleMenu(Base):
    """Role-level menu visibility override."""

    __tablename__ = "role_menus"

    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    menu_id = Column(Integer, ForeignKey("menus.id", ondelete="CASCADE"), primary_key=True, index=True)
    kino_kbn = Column(SmallInteger, nullable=False, default=1)


class UserMenu(Base):
    """Per-user menu visibility override (highest priority)."""

    __tablename__ = "user_menus"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    menu_id = Column(Integer, ForeignKey("menus.id", ondelete="CASCADE"), primary_key=True, index=True)
    kino_kbn = Column(SmallInteger, nullable=False, default=1)


class DepartmentMenu(Base):
    """Department-level menu visibility override."""

    __tablename__ = "department_menus"

    department_id = Column(Integer, ForeignKey("departments.id", ondelete="CASCADE"), primary_key=True)
    menu_id = Column(Integer, ForeignKey("menus.id", ondelete="CASCADE"), primary_key=True)
    kino_kbn = Column(SmallInteger, nullable=False, default=1)
