# app/schemas.py
from typing import List, Optional
from datetime import datetime

from pydantic import BaseModel


# ---------- PHOTO ----------

class PhotoBase(BaseModel):
    file_path: str


class PhotoCreate(PhotoBase):
    pass


class PhotoOut(PhotoBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- GENERATION ----------

class GenerationBase(BaseModel):
    photo_id: int
    description: str
    tags: List[str]
    style: str
    length: str
    tags_count: int


class GenerationCreate(GenerationBase):
    pass


class GenerationUpdate(BaseModel):
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    style: Optional[str] = None
    length: Optional[str] = None
    tags_count: Optional[int] = None


class GenerationOut(GenerationBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- Лог (опционально) ----------

class LogBase(BaseModel):
    level: str
    message: str
    generation_id: Optional[int] = None


class LogCreate(LogBase):
    pass


class LogOut(LogBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- ОТВЕТ /generate ----------

class GenerationResponse(BaseModel):
    description: str
    tags: List[str]
    generated_image: Optional[bytes] = None  # или List[int]

    class Config:
        from_attributes = True
