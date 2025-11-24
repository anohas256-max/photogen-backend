# app/models.py
from sqlalchemy import (
    Column,
    Integer,
    Text,
    String,
    DateTime,
    ForeignKey,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import relationship

from .db import Base


class Photo(Base):
    __tablename__ = "photos"

    id = Column(Integer, primary_key=True, index=True)
    file_path = Column(Text, nullable=False)  # путь к файлу или ключ
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    generations = relationship(
        "Generation",
        back_populates="photo",
        cascade="all, delete-orphan",
    )


class Generation(Base):
    __tablename__ = "generations"

    id = Column(Integer, primary_key=True, index=True)

    photo_id = Column(
        Integer,
        ForeignKey("photos.id", ondelete="CASCADE"),
        nullable=False,
    )

    description = Column(Text, nullable=False)
    tags = Column(ARRAY(String), nullable=False)  # массив тегов
    style = Column(String(50), nullable=False)
    length = Column(String(20), nullable=False)
    tags_count = Column(Integer, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    photo = relationship("Photo", back_populates="generations")


class Log(Base):
    __tablename__ = "logs"

    id = Column(Integer, primary_key=True, index=True)
    generation_id = Column(
        Integer,
        ForeignKey("generations.id", ondelete="CASCADE"),
        nullable=True,
    )
    level = Column(String(20), nullable=False)   # info / error / warning
    message = Column(Text, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
