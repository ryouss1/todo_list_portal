import logging
from typing import List

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.crud import group as crud_group
from app.schemas.group import GroupCreate, GroupResponse, GroupUpdate

logger = logging.getLogger("app.services.group")


def list_groups(db: Session) -> List[GroupResponse]:
    groups = crud_group.get_groups(db)
    result = []
    for g in groups:
        count = crud_group.count_members(db, g.id)
        result.append(
            GroupResponse(
                id=g.id,
                name=g.name,
                description=g.description,
                sort_order=g.sort_order,
                member_count=count,
                created_at=g.created_at,
            )
        )
    return result


def create_group(db: Session, data: GroupCreate) -> GroupResponse:
    logger.info("Creating group: name=%s", data.name)
    try:
        group = crud_group.create_group(db, name=data.name, description=data.description, sort_order=data.sort_order)
    except IntegrityError:
        db.rollback()
        raise ConflictError("Group name already exists")
    logger.info("Group created: id=%d", group.id)
    return GroupResponse(
        id=group.id,
        name=group.name,
        description=group.description,
        sort_order=group.sort_order,
        member_count=0,
        created_at=group.created_at,
    )


def update_group(db: Session, group_id: int, data: GroupUpdate) -> GroupResponse:
    group = crud_group.get_group(db, group_id)
    if not group:
        raise NotFoundError("Group not found")
    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        count = crud_group.count_members(db, group.id)
        return GroupResponse(
            id=group.id,
            name=group.name,
            description=group.description,
            sort_order=group.sort_order,
            member_count=count,
            created_at=group.created_at,
        )
    try:
        group = crud_group.update_group(db, group, update_data)
    except IntegrityError:
        db.rollback()
        raise ConflictError("Group name already exists")
    logger.info("Group updated: id=%d", group_id)
    count = crud_group.count_members(db, group.id)
    return GroupResponse(
        id=group.id,
        name=group.name,
        description=group.description,
        sort_order=group.sort_order,
        member_count=count,
        created_at=group.created_at,
    )


def delete_group(db: Session, group_id: int) -> None:
    group = crud_group.get_group(db, group_id)
    if not group:
        raise NotFoundError("Group not found")
    crud_group.delete_group(db, group)
    logger.info("Group deleted: id=%d", group_id)
