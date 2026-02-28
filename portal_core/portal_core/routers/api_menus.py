from typing import List

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from portal_core.core.deps import get_current_user_id, require_admin
from portal_core.core.exceptions import DuplicateError, NotFoundError
from portal_core.crud import menu as crud_menu
from portal_core.crud.menu import (
    get_department_menu_visibility,
    get_my_menu_visibility,
    get_role_menu_visibility,
    get_user_menu_visibility,
    reset_my_menu_visibility,
    set_department_menu_visibility,
    set_my_menu_visibility,
    set_role_menu_visibility,
    set_user_menu_visibility,
)
from portal_core.database import get_db
from portal_core.schemas.menu import (
    DepartmentVisibilityEntry,
    MenuCreate,
    MenuResponse,
    MenuUpdate,
    MyVisibilityEntry,
    MyVisibilityUpdate,
    RoleVisibilityEntry,
    UserVisibilityEntry,
    VisibilityBatchUpdate,
)

router = APIRouter(prefix="/api/menus", tags=["menus"])


def _get_menu_or_404(db: Session, menu_id: int):
    """Fetch a menu by ID or raise NotFoundError."""
    menu = crud_menu.get_menu(db, menu_id)
    if not menu:
        raise NotFoundError("Menu not found")
    return menu


@router.get("/my", response_model=List[MenuResponse])
def get_my_menus(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Return menus visible to the current user (used by frontend nav rendering)."""
    return crud_menu.get_visible_menus_for_user(db, user_id)


@router.get("/my-visibility", response_model=List[MyVisibilityEntry])
def get_my_visibility(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Return the current user's personal menu visibility overrides."""
    return get_my_menu_visibility(db, user_id)


@router.put("/my-visibility", response_model=MyVisibilityEntry)
def update_my_visibility(
    data: MyVisibilityUpdate,
    request: Request,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Set/update current user's visibility override for one menu."""
    _get_menu_or_404(db, data.menu_id)
    set_my_menu_visibility(db, user_id=user_id, menu_id=data.menu_id, kino_kbn=data.kino_kbn)
    db.commit()
    portal = getattr(request.app.state, "portal", None)
    if portal:
        portal.invalidate_nav_cache([user_id])
    return {"menu_id": data.menu_id, "kino_kbn": data.kino_kbn}


@router.delete("/my-visibility/{menu_id}", status_code=204)
def reset_my_visibility(
    menu_id: int,
    request: Request,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Delete current user's visibility override → falls back to dept/role/RBAC."""
    reset_my_menu_visibility(db, user_id=user_id, menu_id=menu_id)
    db.commit()
    portal = getattr(request.app.state, "portal", None)
    if portal:
        portal.invalidate_nav_cache([user_id])


@router.get("/", response_model=List[MenuResponse])
def list_menus(db: Session = Depends(get_db), _: int = Depends(require_admin)):
    return crud_menu.get_menus(db)


@router.post("/", response_model=MenuResponse, status_code=201)
def create_menu(data: MenuCreate, db: Session = Depends(get_db), _: int = Depends(require_admin)):
    if crud_menu.get_menu_by_name(db, data.name):
        raise DuplicateError(f"Menu '{data.name}' already exists")
    menu = crud_menu.create_menu(db, data)
    db.commit()
    db.refresh(menu)
    return menu


@router.get("/{menu_id}", response_model=MenuResponse)
def get_menu_by_id(menu_id: int, db: Session = Depends(get_db), _: int = Depends(require_admin)):
    return _get_menu_or_404(db, menu_id)


@router.put("/{menu_id}", response_model=MenuResponse)
def update_menu(
    menu_id: int,
    data: MenuUpdate,
    request: Request,
    db: Session = Depends(get_db),
    _: int = Depends(require_admin),
):
    menu = crud_menu.update_menu(db, menu_id, data)
    if not menu:
        raise NotFoundError("Menu not found")
    db.commit()
    db.refresh(menu)
    portal = getattr(request.app.state, "portal", None)
    if portal:
        portal.invalidate_nav_cache(None)
    return menu


@router.delete("/{menu_id}", status_code=204)
def delete_menu(
    menu_id: int,
    request: Request,
    db: Session = Depends(get_db),
    _: int = Depends(require_admin),
):
    _get_menu_or_404(db, menu_id)
    crud_menu.delete_menu(db, menu_id)
    db.commit()
    portal = getattr(request.app.state, "portal", None)
    if portal:
        portal.invalidate_nav_cache(None)


# ----- Admin: role visibility -----


@router.get("/{menu_id}/role-visibility", response_model=List[RoleVisibilityEntry])
def get_role_visibility(
    menu_id: int,
    db: Session = Depends(get_db),
    _: int = Depends(require_admin),
):
    _get_menu_or_404(db, menu_id)
    return get_role_menu_visibility(db, menu_id)


@router.put("/{menu_id}/role-visibility", status_code=200, response_model=List[RoleVisibilityEntry])
def update_role_visibility(
    menu_id: int,
    data: VisibilityBatchUpdate,
    request: Request,
    db: Session = Depends(get_db),
    _: int = Depends(require_admin),
):
    _get_menu_or_404(db, menu_id)
    for item in data.items:
        set_role_menu_visibility(db, menu_id=menu_id, role_id=item.id, kino_kbn=item.kino_kbn)
    db.commit()
    portal = getattr(request.app.state, "portal", None)
    if portal:
        portal.invalidate_nav_cache(None)
    return get_role_menu_visibility(db, menu_id)


# ----- Admin: department visibility -----


@router.get("/{menu_id}/department-visibility", response_model=List[DepartmentVisibilityEntry])
def get_department_visibility(
    menu_id: int,
    db: Session = Depends(get_db),
    _: int = Depends(require_admin),
):
    _get_menu_or_404(db, menu_id)
    return get_department_menu_visibility(db, menu_id)


@router.put("/{menu_id}/department-visibility", status_code=200, response_model=List[DepartmentVisibilityEntry])
def update_department_visibility(
    menu_id: int,
    data: VisibilityBatchUpdate,
    request: Request,
    db: Session = Depends(get_db),
    _: int = Depends(require_admin),
):
    _get_menu_or_404(db, menu_id)
    for item in data.items:
        set_department_menu_visibility(db, menu_id=menu_id, department_id=item.id, kino_kbn=item.kino_kbn)
    db.commit()
    portal = getattr(request.app.state, "portal", None)
    if portal:
        portal.invalidate_nav_cache(None)
    return get_department_menu_visibility(db, menu_id)


# ----- Admin: user visibility -----


@router.get("/{menu_id}/user-visibility", response_model=List[UserVisibilityEntry])
def get_user_visibility(
    menu_id: int,
    db: Session = Depends(get_db),
    _: int = Depends(require_admin),
):
    _get_menu_or_404(db, menu_id)
    return get_user_menu_visibility(db, menu_id)


@router.put("/{menu_id}/user-visibility", status_code=200, response_model=List[UserVisibilityEntry])
def update_user_visibility(
    menu_id: int,
    data: VisibilityBatchUpdate,
    request: Request,
    db: Session = Depends(get_db),
    _: int = Depends(require_admin),
):
    _get_menu_or_404(db, menu_id)
    for item in data.items:
        set_user_menu_visibility(db, menu_id=menu_id, user_id=item.id, kino_kbn=item.kino_kbn)
    db.commit()
    portal = getattr(request.app.state, "portal", None)
    if portal:
        portal.invalidate_nav_cache([item.id for item in data.items])
    return get_user_menu_visibility(db, menu_id)
