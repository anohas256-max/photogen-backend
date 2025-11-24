# app/main.py

from typing import List

import os
import base64
import json

from fastapi import (
    FastAPI,
    UploadFile,
    File,
    Form,
    HTTPException,
    Depends,
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from sqlalchemy.orm import Session

from openai import OpenAI

from . import db, models, schemas, crud


# ---------- .env и клиент OpenAI ----------

load_dotenv()  # backend/.env

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("OPENAI_API_KEY не найден в .env (backend/.env)")

client = OpenAI(api_key=api_key)


# ---------- ИНИЦИАЛИЗАЦИЯ FASTAPI И БАЗЫ ----------

app = FastAPI(
    title="PhotoGen API",
    description="API для генерации описаний по изображениям и CRUD по историям",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

models.Base.metadata.create_all(bind=db.engine)


def get_db():
    """Зависимость для получения Session."""
    yield from db.get_db()


# ---------- ВСПОМОГАТЕЛЬНАЯ СХЕМА ДЛЯ /generate ----------


class GenerationResponse(BaseModel):
    description: str
    tags: list[str]
    generated_image: list[int] | None = None


# ---------- ВСПОМОГАТЕЛЬНЫЙ ПАРСЕР JSON ОТ МОДЕЛИ ----------


def _parse_model_json(raw_text: str) -> dict:
    """
    Пытаемся выжать валидный JSON даже если модель
    вернула его в ```блоке``` или с префиксами/суффиксами.
    """
    text = raw_text.strip()

    # 1) убираем ```json ... ``` если есть
    if text.startswith("```"):
        parts = text.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("{") and part.endswith("}"):
                text = part
                break

    # 2) если всё ещё не с { ... } — вырезаем от первого { до последней }
    if not (text.startswith("{") and text.endswith("}")):
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            text = text[start : end + 1]

    # 3) финальная попытка распарсить
    try:
        return json.loads(text)
    except Exception as e:
        raise ValueError(f"Модель вернула невалидный JSON: {e}. Текст: {raw_text!r}")


# ---------- /health ----------


@app.get("/health")
def health():
    return {"status": "ok"}


# ---------- /generate ----------


@app.post("/generate", response_model=GenerationResponse)
async def generate(
    image: UploadFile = File(...),
    style: str = Form("Default"),
    length: str = Form("Medium"),
    tags_count: int = Form(5),
    db_session: Session = Depends(get_db),
):
    """
    Генерация описания и тегов по загруженному изображению (OpenAI gpt-4o-mini)
    + запись Photo и Generation в БД.
    """

    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="Нужно отправить файл-изображение",
        )

    image_bytes = await image.read()

    b64_image = base64.b64encode(image_bytes).decode("utf-8")
    data_url = f"data:{image.content_type};base64,{b64_image}"

    # --- подсказка по длине ---
    if length == "Short":
        length_hint = (
            "Для текущего параметра длины ('Short') напиши строго 1–2 коротких предложения."
        )
    elif length == "Medium":
        length_hint = (
            "Для текущего параметра длины ('Medium') напиши примерно 5–6 предложений."
        )
    elif length == "Long":
        length_hint = (
            "Для текущего параметра длины ('Long') напиши примерно 10–15 предложений."
        )
    elif length == "VeryLong":
        length_hint = (
            "Для текущего параметра длины ('VeryLong') напиши большой рассказ "
            "объёмом не меньше 40 предложений (можно 40–60), текст должен быть связным."
        )
    else:
        length = "Medium"
        length_hint = (
            "Для текущего параметра длины ('Medium') напиши примерно 5–6 предложений."
        )

    # --- блок про теги: если 0, просим пустой массив ---
    if tags_count <= 0:
        tags_instruction = """
Теги:
- Поле "tags" в JSON должно быть пустым массивом [].
- Не добавляй никаких тегов, просто верни "tags": [].
"""
    else:
        tags_instruction = f"""
Теги:
- Должно быть РОВНО {tags_count} тегов.
- Теги — отдельные слова или короткие фразы.
- Без решеток (#) и без запятых внутри тегов.
- Теги должны точно соответствовать объектам и смыслу сцены.
"""

    system_instruction = f"""
Ты — помощник приложения PhotoGen.
Пользователь загрузил изображение.

Твоя задача — вернуть СТРОГО ЧИСТЫЙ JSON без лишнего текста, формата:
{{
  "description": "краткое описание изображения",
  "tags": ["тег1", "тег2", "..."]
}}

Язык:
- Пиши по-русски.

Стили описания (поле style):
- Default      — нейтральное, обычное описание.
- Art          — более художественное, образное, с эмоциями.
- Realistic    — сухое, фактическое, как техническое описание.
- Scientific   — как в научной/технической статье, с точными терминами.
- Informative  — максимально информативно: что изображено, из чего состоит,
                 где используется, какие важные детали.
- Funny        — максимально весёлое и абсурдное описание с гиперболами,
                 шутками и мемными фразами, но всё равно основанное на том,
                 что реально есть на изображении, без мата.
- Dialogue     — рассказ, где большая часть текста — диалоги персонажей.
                 Используй формат реплик с тире, можно добавлять авторские
                 вставки между диалогами.

Длина описания (поле length):
- Short      — 1–2 предложения.
- Medium     — 5–6 предложений.
- Long       — 10–15 предложений.
- VeryLong   — большой рассказ (40+ предложений).

{length_hint}

Дополнительные указания для стиля Funny:
- используй преувеличения, неожиданные сравнения и лёгкий абсурд;
- можно аккуратно вставлять популярные мемные выражения без мата;
- описание всё равно должно быть связано с содержимым картинки.

Дополнительные указания для стиля Dialogue:
- делай упор на диалог персонажей, как сцена из фильма или визуальной новеллы;
- реплики начинай с тире;
- можно добавить немного описаний между репликами, чтобы связать сцену.

ВАЖНО:
- Не используй фразы вроде:
  "на изображении показано", "на фото видно", "на картинке представлено",
  "изображён/представлен" и т.п.
  Сразу начинай с описания сцены или объекта.
- Описание должно быть связным и логичным.

{tags_instruction}

Текущие параметры запроса:
- Стиль: {style}
- Параметр длины: {length}
- Количество тегов: {tags_count}
"""

    try:
        response = client.responses.create(
            model="gpt-4o-mini",
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": system_instruction},
                        {"type": "input_image", "image_url": data_url},
                    ],
                }
            ],
            max_output_tokens=2000,
        )

        raw_text = response.output_text

        # устойчивый парсер
        try:
            data = _parse_model_json(raw_text)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Модель вернула не JSON: {e}")

        description = data.get("description", "") or ""
        tags = data.get("tags", [])

        if not isinstance(tags, list):
            tags = []

        # --------- ЧАСТЬ CRUD: СОХРАНЯЕМ В БД ---------
        photo = crud.create_photo(
            db_session,
            file_path="generated_via_openai",
        )

        gen_in = schemas.GenerationCreate(
            photo_id=photo.id,
            description=description,
            tags=tags,
            style=style,
            length=length,
            tags_count=tags_count,
        )
        crud.create_generation(db_session, gen_in)

        return GenerationResponse(
            description=description,
            tags=tags,
            generated_image=None,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenAI error: {e}")


# ======================================================
#                       CRUD: PHOTOS
# ======================================================


@app.post("/photos", response_model=schemas.PhotoOut)
def create_photo(
    data: schemas.PhotoCreate,
    db_session: Session = Depends(get_db),
):
    photo = crud.create_photo(db_session, data.file_path)
    return photo


@app.get("/photos", response_model=List[schemas.PhotoOut])
def list_photos(
    skip: int = 0,
    limit: int = 100,
    db_session: Session = Depends(get_db),
):
    photos = crud.get_photos(db_session, skip=skip, limit=limit)
    return photos


@app.get("/photos/{photo_id}", response_model=schemas.PhotoOut)
def get_photo(
    photo_id: int,
    db_session: Session = Depends(get_db),
):
    photo = crud.get_photo(db_session, photo_id)
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    return photo


@app.delete("/photos/{photo_id}")
def delete_photo(
    photo_id: int,
    db_session: Session = Depends(get_db),
):
    ok = crud.delete_photo(db_session, photo_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Photo not found")
    return {"status": "deleted"}


# ======================================================
#                    CRUD: GENERATIONS
# ======================================================


@app.post("/generations", response_model=schemas.GenerationOut)
def create_generation(
    data: schemas.GenerationCreate,
    db_session: Session = Depends(get_db),
):
    photo = crud.get_photo(db_session, data.photo_id)
    if not photo:
        raise HTTPException(status_code=400, detail="Photo not found")

    gen = crud.create_generation(db_session, data)
    return gen


@app.get("/generations", response_model=List[schemas.GenerationOut])
def list_generations(
    skip: int = 0,
    limit: int = 100,
    db_session: Session = Depends(get_db),
):
    gens = crud.get_generations(db_session, skip=skip, limit=limit)
    return gens


@app.get("/generations/{gen_id}", response_model=schemas.GenerationOut)
def get_generation(
    gen_id: int,
    db_session: Session = Depends(get_db),
):
    gen = crud.get_generation(db_session, gen_id)
    if not gen:
        raise HTTPException(status_code=404, detail="Generation not found")
    return gen


@app.put("/generations/{gen_id}", response_model=schemas.GenerationOut)
def update_generation(
    gen_id: int,
    data: schemas.GenerationUpdate,
    db_session: Session = Depends(get_db),
):
    gen = crud.get_generation(db_session, gen_id)
    if not gen:
        raise HTTPException(status_code=404, detail="Generation not found")

    gen = crud.update_generation(db_session, gen, data)
    return gen


@app.delete("/generations/{gen_id}")
def delete_generation(
    gen_id: int,
    db_session: Session = Depends(get_db),
):
    ok = crud.delete_generation(db_session, gen_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Generation not found")
    return {"status": "deleted"}
