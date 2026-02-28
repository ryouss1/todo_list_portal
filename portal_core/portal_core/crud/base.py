from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union

from pydantic import BaseModel
from sqlalchemy.orm import Session

from portal_core.database import Base

ModelType = TypeVar("ModelType", bound=Base)


class CRUDBase(Generic[ModelType]):
    """Generic CRUD base class for SQLAlchemy models.

    Provides standard get/create/update/delete operations.
    Accepts both Pydantic BaseModel and plain dict for create/update data.
    """

    def __init__(self, model: Type[ModelType]):
        self.model = model

    def get(self, db: Session, id: int) -> Optional[ModelType]:
        return db.query(self.model).filter(self.model.id == id).first()

    def get_all(self, db: Session) -> List[ModelType]:
        return db.query(self.model).all()

    def create(
        self,
        db: Session,
        data: Union[BaseModel, Dict[str, Any]],
        *,
        commit: bool = True,
        **extra_fields: Any,
    ) -> ModelType:
        if isinstance(data, BaseModel):
            obj_data = data.model_dump()
        else:
            obj_data = dict(data)
        obj_data.update(extra_fields)
        obj = self.model(**obj_data)
        db.add(obj)
        if commit:
            db.commit()
            db.refresh(obj)
        else:
            db.flush()
        return obj

    def update(
        self,
        db: Session,
        obj: ModelType,
        data: Union[BaseModel, Dict[str, Any]],
        *,
        commit: bool = True,
    ) -> ModelType:
        if isinstance(data, BaseModel):
            update_data = data.model_dump(exclude_unset=True)
        else:
            update_data = dict(data)
        for key, value in update_data.items():
            setattr(obj, key, value)
        if commit:
            db.commit()
            db.refresh(obj)
        else:
            db.flush()
        return obj

    def delete(self, db: Session, obj: ModelType, *, commit: bool = True) -> None:
        db.delete(obj)
        if commit:
            db.commit()
        else:
            db.flush()
