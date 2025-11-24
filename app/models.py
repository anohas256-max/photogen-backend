# app/models.py
import json

from sqlalchemy import (
    Column,
    Integer,
    Text,
    String,
    DateTime,
    ForeignKey,
    func,
)
from sqlalchemy.orm import relationship
from sqlalchemy.types import TypeDecorator

from .db import Base


class StringArray(TypeDecorator):
    """
    Универсальный тип: list[str] <-> TEXT (JSON).
    Работает и с SQLite, и с Postgres.
    Для остального кода tags остаётся обычным списком строк.
    """
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        # Python -> БД
        if value is None:
            return None
        return json.dumps(value, ensure_ascii=False)

    def process_result_value(self, value, dialect):
        # БД -> Python
        if value is None:
            return None
        return json.loads(value)


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
    # ВАЖНО: раньше было ARRAY(String), теперь наш кросс-БД тип
    tags = Column(StringArray, nullable=False)  # массив тегов
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
