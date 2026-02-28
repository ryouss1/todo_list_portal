from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.log_source_path import LogSourcePath


def create_path(
    db: Session,
    source_id: int,
    base_path: str,
    file_pattern: str = "*.log",
    is_enabled: bool = True,
) -> LogSourcePath:
    path = LogSourcePath(
        source_id=source_id,
        base_path=base_path,
        file_pattern=file_pattern,
        is_enabled=is_enabled,
    )
    db.add(path)
    db.flush()
    return path


def get_path(db: Session, path_id: int) -> Optional[LogSourcePath]:
    return db.query(LogSourcePath).filter(LogSourcePath.id == path_id).first()


def get_paths_by_source(db: Session, source_id: int) -> List[LogSourcePath]:
    return db.query(LogSourcePath).filter(LogSourcePath.source_id == source_id).order_by(LogSourcePath.id).all()


def get_paths_by_source_ids(db: Session, source_ids: List[int]) -> Dict[int, List[LogSourcePath]]:
    """Get all paths for multiple sources in a single query."""
    if not source_ids:
        return {}
    paths = (
        db.query(LogSourcePath)
        .filter(LogSourcePath.source_id.in_(source_ids))
        .order_by(LogSourcePath.source_id, LogSourcePath.id)
        .all()
    )
    result: Dict[int, List[LogSourcePath]] = {}
    for p in paths:
        result.setdefault(p.source_id, []).append(p)
    return result


def get_enabled_paths_by_source(db: Session, source_id: int) -> List[LogSourcePath]:
    return (
        db.query(LogSourcePath)
        .filter(LogSourcePath.source_id == source_id, LogSourcePath.is_enabled.is_(True))
        .order_by(LogSourcePath.id)
        .all()
    )


def update_path(db: Session, path: LogSourcePath, update_data: dict) -> LogSourcePath:
    for key, value in update_data.items():
        setattr(path, key, value)
    db.flush()
    return path


def delete_path(db: Session, path: LogSourcePath) -> None:
    db.delete(path)
    db.flush()


def delete_paths_by_source(db: Session, source_id: int) -> None:
    db.query(LogSourcePath).filter(LogSourcePath.source_id == source_id).delete()
    db.flush()


def count_paths_by_source(db: Session, source_id: int) -> int:
    return db.query(LogSourcePath).filter(LogSourcePath.source_id == source_id).count()
