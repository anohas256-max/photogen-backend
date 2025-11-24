from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker, declarative_base

# ⚠️ ВПИШИ В ТАКОМ ВИДЕ — БЕЗ КАВЫЧЕК, ПРОБЕЛОВ, РУССКИХ СИМВОЛОВ

DB_USER = "postgres"
DB_PASSWORD = "pg12345"   # твой пароль
DB_HOST = "localhost"
DB_PORT = 5433            # ВАЖНО — ИМЕННО 5433, как на твоём скрине!
DB_NAME = "photogen_db"

DATABASE_URL = URL.create(
    drivername="postgresql+pg8000",
    username=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT,
    database=DB_NAME,
)

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
