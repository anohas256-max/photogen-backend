# app/crud.py
from typing import List, Optional

from sqlalchemy.orm import Session

from . import models, schemas


# ---------- PHOTO ----------

def create_photo(db: Session, file_path: str) -> models.Photo:
    db_photo = models.Photo(file_path=file_path)
    db.add(db_photo)
    db.commit()
    db.refresh(db_photo)
    return db_photo


def get_photo(db: Session, photo_id: int) -> Optional[models.Photo]:
    return db.query(models.Photo).filter(models.Photo.id == photo_id).first()


def get_photos(db: Session, skip: int = 0, limit: int = 100) -> List[models.Photo]:
    return (
        db.query(models.Photo)
        .order_by(models.Photo.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def delete_photo(db: Session, photo_id: int) -> bool:
    photo = get_photo(db, photo_id)
    if not photo:
        return False
    db.delete(photo)
    db.commit()
    return True


# ---------- GENERATION ----------

def create_generation(
    db: Session,
    data: schemas.GenerationCreate,
) -> models.Generation:
    db_gen = models.Generation(
        photo_id=data.photo_id,
        description=data.description,
        tags=data.tags,
        style=data.style,
        length=data.length,
        tags_count=data.tags_count,
    )
    db.add(db_gen)
    db.commit()
    db.refresh(db_gen)
    return db_gen


def get_generation(db: Session, gen_id: int) -> Optional[models.Generation]:
    return db.query(models.Generation).filter(models.Generation.id == gen_id).first()


def get_generations(
    db: Session,
    skip: int = 0,
    limit: int = 100,
) -> List[models.Generation]:
    return (
        db.query(models.Generation)
        .order_by(models.Generation.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def update_generation(
    db: Session,
    gen: models.Generation,
    data: schemas.GenerationUpdate,
) -> models.Generation:
    if data.description is not None:
        gen.description = data.description
    if data.tags is not None:
        gen.tags = data.tags
    if data.style is not None:
        gen.style = data.style
    if data.length is not None:
        gen.length = data.length
    if data.tags_count is not None:
        gen.tags_count = data.tags_count

    db.add(gen)
    db.commit()
    db.refresh(gen)
    return gen


def delete_generation(db: Session, gen_id: int) -> bool:
    gen = get_generation(db, gen_id)
    if not gen:
        return False
    db.delete(gen)
    db.commit()
    return True


# ---------- LOG ----------

def create_log(db: Session, data: schemas.LogCreate) -> models.Log:
    db_log = models.Log(
        level=data.level,
        message=data.message,
        generation_id=data.generation_id,
    )
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log


def get_logs(db: Session, skip: int = 0, limit: int = 100) -> List[models.Log]:
    return (
        db.query(models.Log)
        .order_by(models.Log.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
