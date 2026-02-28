from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from portal_core.core.deps import get_current_user_id, require_admin
from portal_core.core.exceptions import DuplicateError, NotFoundError
from portal_core.crud import menu as crud_menu
from portal_core.database import get_db
from portal_core.schemas.menu import MenuCreate, MenuResponse, MenuUpdate

router = APIRouter(prefix="/api/menus", tags=["menus"])


@router.get("/my", response_model=List[MenuResponse])
def get_my_menus(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Return menus visible to the current user (used by frontend nav rendering)."""
    return crud_menu.get_visible_menus_for_user(db, user_id)


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
def get_menu(menu_id: int, db: Session = Depends(get_db), _: int = Depends(require_admin)):
    menu = crud_menu.get_menu(db, menu_id)
    if not menu:
        raise NotFoundError("Menu not found")
    return menu


@router.put("/{menu_id}", response_model=MenuResponse)
def update_menu(
    menu_id: int,
    data: MenuUpdate,
    db: Session = Depends(get_db),
    _: int = Depends(require_admin),
):
    menu = crud_menu.update_menu(db, menu_id, data)
    if not menu:
        raise NotFoundError("Menu not found")
    db.commit()
    db.refresh(menu)
    return menu


@router.delete("/{menu_id}", status_code=204)
def delete_menu(menu_id: int, db: Session = Depends(get_db), _: int = Depends(require_admin)):
    if not crud_menu.get_menu(db, menu_id):
        raise NotFoundError("Menu not found")
    crud_menu.delete_menu(db, menu_id)
    db.commit()
