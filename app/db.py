import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

# Загружаем .env локально (на Render его просто не будет — это не страшно)
load_dotenv()

# 1) Пытаемся взять строку подключения из переменной окружения
DATABASE_URL = os.getenv("DATABASE_URL")

# 2) Если переменная не задана (например, у тебя локально) — используем старый Postgres-конфиг
if not DATABASE_URL:
    from sqlalchemy.engine import URL

    # ⚠️ тут всё как у тебя было
    DB_USER = "postgres"
    DB_PASSWORD = "pg12345"
    DB_HOST = "localhost"
    DB_PORT = 5433
    DB_NAME = "photogen_db"

    DATABASE_URL = URL.create(
        drivername="postgresql+pg8000",
        username=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
    )

# 3) Создаём engine по строке подключения (это может быть и postgres://, и sqlite:///)
engine = create_engine(
    DATABASE_URL,
    echo=True,
    future=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
