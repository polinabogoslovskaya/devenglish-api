"""DevEnglish API — английский для разработчиков."""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from time import perf_counter
from typing import Literal

from fastapi import FastAPI, HTTPException, Query, Request
from pydantic import BaseModel, Field, model_validator
from starlette.responses import Response

APP_NAME = os.getenv("APP_NAME", "DevEnglish API")
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
APP_ENV = os.getenv("APP_ENV", "development")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO),
                    format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("devenglish")
Category = Literal["code_review", "meetings", "bugs", "documentation", "git"]
Level = Literal["beginner", "intermediate", "advanced"]

_INITIAL_PHRASES: list[dict] = [
    {"id":"de-001","phrase":"Could you take a look at this?","meaning_ru":"Можешь посмотреть это?","category":"code_review","level":"beginner","example":"Could you take a look at this pull request?","example_ru":"Можешь посмотреть этот pull request?","options":["Можешь посмотреть это?","Я уже исправил это.","Давайте выпустим релиз.","Я не могу воспроизвести ошибку."],"correct_answer":"Можешь посмотреть это?"},
    {"id":"de-002","phrase":"This change is a breaking change.","meaning_ru":"Это изменение нарушает обратную совместимость.","category":"code_review","level":"intermediate","example":"This change is a breaking change for existing clients.","example_ru":"Это изменение нарушает обратную совместимость для существующих клиентов.","options":["Это изменение ускоряет сборку.","Это изменение нарушает обратную совместимость.","Это изменение только для документации.","Это изменение уже отменено."],"correct_answer":"Это изменение нарушает обратную совместимость."},
    {"id":"de-003","phrase":"Could you add a test for this edge case?","meaning_ru":"Можешь добавить тест для этого граничного случая?","category":"code_review","level":"intermediate","example":"Could you add a test for this edge case before merging?","example_ru":"Можешь добавить тест для этого граничного случая перед слиянием?","options":["Можешь обновить версию Python?","Можешь добавить тест для этого граничного случая?","Можешь удалить эту ветку?","Можешь задеплоить приложение?"],"correct_answer":"Можешь добавить тест для этого граничного случая?"},
    {"id":"de-004","phrase":"I am blocked by an external dependency.","meaning_ru":"Я не могу продолжить из-за внешней зависимости.","category":"meetings","level":"intermediate","example":"I am blocked by an external dependency, so the task is on hold.","example_ru":"Я не могу продолжить из-за внешней зависимости, поэтому задача приостановлена.","options":["Я закончил задачу раньше срока.","Я не могу продолжить из-за внешней зависимости.","Я обновил зависимости проекта.","Я провёл код-ревью."],"correct_answer":"Я не могу продолжить из-за внешней зависимости."},
    {"id":"de-005","phrase":"I will pick this up tomorrow.","meaning_ru":"Я займусь этим завтра.","category":"meetings","level":"beginner","example":"I will pick this up tomorrow morning.","example_ru":"Я займусь этим завтра утром.","options":["Я займусь этим завтра.","Я уже сделал это вчера.","Я передам это заказчику.","Я удалю эту задачу."],"correct_answer":"Я займусь этим завтра."},
    {"id":"de-006","phrase":"The issue is reproducible on the latest build.","meaning_ru":"Проблему можно воспроизвести на последней сборке.","category":"bugs","level":"intermediate","example":"The issue is reproducible on the latest build of the application.","example_ru":"Проблему можно воспроизвести на последней сборке приложения.","options":["Проблема решена в последней сборке.","Проблему можно воспроизвести на последней сборке.","Сборка не была опубликована.","Проблема касается только дизайна."],"correct_answer":"Проблему можно воспроизвести на последней сборке."},
    {"id":"de-007","phrase":"The root cause was a race condition.","meaning_ru":"Первопричиной была гонка данных.","category":"bugs","level":"advanced","example":"The root cause was a race condition in the cache update logic.","example_ru":"Первопричиной была гонка данных в логике обновления кэша.","options":["Первопричиной была гонка данных.","Первопричиной была ошибка перевода.","Причиной было отсутствие документации.","Причиной была нехватка дискового пространства."],"correct_answer":"Первопричиной была гонка данных."},
    {"id":"de-008","phrase":"The workaround is documented below.","meaning_ru":"Обходное решение описано ниже.","category":"documentation","level":"intermediate","example":"The workaround is documented below until the permanent fix is released.","example_ru":"Обходное решение описано ниже, пока не будет выпущено постоянное исправление.","options":["Исправление уже удалено.","Обходное решение описано ниже.","Инструкция устарела.","Этот раздел необязателен."],"correct_answer":"Обходное решение описано ниже."},
    {"id":"de-009","phrase":"This endpoint returns a paginated response.","meaning_ru":"Этот эндпоинт возвращает постраничный ответ.","category":"documentation","level":"advanced","example":"This endpoint returns a paginated response when the limit is provided.","example_ru":"Этот эндпоинт возвращает постраничный ответ, если указан limit.","options":["Этот эндпоинт возвращает постраничный ответ.","Этот эндпоинт удаляет запись.","Этот эндпоинт требует пароль.","Этот эндпоинт работает только локально."],"correct_answer":"Этот эндпоинт возвращает постраничный ответ."},
    {"id":"de-010","phrase":"I have opened a pull request.","meaning_ru":"Я создал pull request.","category":"git","level":"beginner","example":"I have opened a pull request with the proposed fix.","example_ru":"Я создал pull request с предлагаемым исправлением.","options":["Я создал pull request.","Я переключил репозиторий в архив.","Я откатил последний коммит.","Я закрыл issue без ответа."],"correct_answer":"Я создал pull request."},
    {"id":"de-011","phrase":"Could you rebase your branch?","meaning_ru":"Можешь перебазировать свою ветку?","category":"git","level":"advanced","example":"Could you rebase your branch on top of the latest main?","example_ru":"Можешь перебазировать свою ветку поверх последней версии main?","options":["Можешь удалить удалённый репозиторий?","Можешь перебазировать свою ветку?","Можешь переименовать пакет?","Можешь запустить линтер?"],"correct_answer":"Можешь перебазировать свою ветку?"},
    {"id":"de-012","phrase":"The implementation is not backward compatible.","meaning_ru":"Реализация не обеспечивает обратную совместимость.","category":"code_review","level":"advanced","example":"The implementation is not backward compatible with the previous API version.","example_ru":"Реализация не совместима с предыдущей версией API.","options":["Реализация не обеспечивает обратную совместимость.","Реализация требует меньше памяти.","Реализация уже покрыта тестами.","Реализация устарела только визуально."],"correct_answer":"Реализация не обеспечивает обратную совместимость."},
]
_phrases = [item.copy() for item in _INITIAL_PHRASES]
_attempts: list[dict] = []


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("Starting %s version=%s environment=%s", APP_NAME, APP_VERSION, APP_ENV)
    yield
    logger.info("Stopping %s", APP_NAME)


app = FastAPI(title=APP_NAME, version=APP_VERSION,
              description="Карточки английского для разработчиков: code review, встречи, баги, документация и Git.",
              lifespan=lifespan)


@app.middleware("http")
async def log_requests(request: Request, call_next) -> Response:
    started = perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("request failed method=%s path=%s", request.method, request.url.path)
        raise
    elapsed_ms = (perf_counter() - started) * 1000
    logger.info("request method=%s path=%s status=%s elapsed_ms=%.2f",
                request.method, request.url.path, response.status_code, elapsed_ms)
    return response


def _public_phrase(item: dict) -> dict:
    return {key: value for key, value in item.items() if key not in {"options", "correct_answer"}}


def _find_phrase(phrase_id: str) -> dict:
    for item in _phrases:
        if item["id"] == phrase_id:
            return item
    raise HTTPException(status_code=404, detail="Фраза не найдена")


@app.get("/", tags=["service"])
def root() -> dict:
    return {"service": APP_NAME, "message": "Английский для разработчиков: фразы для рабочих ситуаций", "environment": APP_ENV}


@app.get("/health", tags=["service"])
def health() -> dict:
    return {"status": "ok"}


@app.get("/version", tags=["service"])
def version() -> dict:
    return {"service": APP_NAME, "version": APP_VERSION, "environment": APP_ENV}


@app.get("/phrases", tags=["phrasebook"])
def list_phrases(
    category: Category | None = Query(default=None),
    level: Level | None = Query(default=None),
    q: str | None = Query(default=None, min_length=1, max_length=100, description="Поиск по английской фразе, переводу или примеру"),
) -> dict:
    items = _phrases
    if category is not None:
        items = [item for item in items if item["category"] == category]
    if level is not None:
        items = [item for item in items if item["level"] == level]
    if q is not None:
        needle = q.casefold()
        items = [item for item in items if any(needle in str(item[field]).casefold()
                 for field in ("phrase", "meaning_ru", "example", "example_ru"))]
    return {"count": len(items), "items": [_public_phrase(item) for item in items]}


@app.get("/phrases/{phrase_id}", tags=["phrasebook"])
def get_phrase(phrase_id: str) -> dict:
    return _public_phrase(_find_phrase(phrase_id))



class PhraseCreate(BaseModel):
    phrase: str = Field(min_length=3, max_length=180)
    meaning_ru: str = Field(min_length=2, max_length=240)
    category: Category
    level: Level = "intermediate"
    example: str = Field(min_length=3, max_length=300)
    example_ru: str = Field(min_length=2, max_length=400)
    options: list[str] = Field(min_length=4, max_length=4, description="Четыре варианта перевода для викторины")

    @model_validator(mode="after")
    def validate_options(self) -> "PhraseCreate":
        normalized = {option.strip().casefold() for option in self.options}
        if len(normalized) != 4:
            raise ValueError("Варианты ответа должны быть уникальными")
        if self.meaning_ru.strip().casefold() not in normalized:
            raise ValueError("Варианты options должны содержать meaning_ru")
        return self


class AnswerSubmission(BaseModel):
    phrase_id: str = Field(min_length=1, max_length=20)
    answer: str = Field(min_length=1, max_length=240)


@app.post("/phrases", status_code=201, tags=["phrasebook"])
def create_phrase(payload: PhraseCreate) -> dict:
    if any(item["phrase"].casefold() == payload.phrase.casefold() for item in _phrases):
        raise HTTPException(status_code=409, detail="Такая английская фраза уже есть в справочнике")
    next_id = max((int(item["id"].split("-")[-1]) for item in _phrases), default=0) + 1
    item = {"id": f"de-{next_id:03d}", **payload.model_dump(), "correct_answer": payload.meaning_ru}
    _phrases.append(item)
    logger.info("phrase created id=%s category=%s level=%s", item["id"], item["category"], item["level"])
    return _public_phrase(item)


@app.get("/quiz/question", tags=["quiz"])
def quiz_question(
    category: Category | None = Query(default=None),
    level: Level | None = Query(default=None),
    phrase_id: str | None = Query(default=None),
) -> dict:
    if phrase_id is not None:
        item = _find_phrase(phrase_id)
        if category is not None and item["category"] != category:
            raise HTTPException(status_code=404, detail="Фраза не найдена в выбранной категории")
        if level is not None and item["level"] != level:
            raise HTTPException(status_code=404, detail="Фраза не найдена для выбранного уровня")
    else:
        candidates = [item for item in _phrases
                      if (category is None or item["category"] == category)
                      and (level is None or item["level"] == level)]
        if not candidates:
            raise HTTPException(status_code=404, detail="Для выбранных фильтров нет фраз")
        # Round-robin by attempt count so that repeated calls are predictable for testing.
        item = candidates[len(_attempts) % len(candidates)]
    return {
        "phrase_id": item["id"],
        "prompt": f"Выберите перевод фразы: {item['phrase']}",
        "options": item["options"],
        "category": item["category"],
        "level": item["level"],
    }


@app.post("/quiz/answer", tags=["quiz"])
def quiz_answer(payload: AnswerSubmission) -> dict:
    item = _find_phrase(payload.phrase_id)
    is_correct = payload.answer.strip().casefold() == item["correct_answer"].strip().casefold()
    attempt = {"phrase_id": item["id"], "answer": payload.answer, "correct": is_correct}
    _attempts.append(attempt)
    logger.info("quiz answer phrase_id=%s correct=%s", item["id"], is_correct)
    return {
        "phrase_id": item["id"],
        "correct": is_correct,
        "correct_answer": item["correct_answer"],
        "explanation": f"{item['phrase']} — {item['meaning_ru']}",
        "attempt_number": len(_attempts),
    }


@app.get("/categories", tags=["phrasebook"])
def list_categories() -> dict:
    """Вернуть категории карточек и число фраз в каждой."""
    labels = {
        "code_review": "Code review",
        "meetings": "Meetings and stand-ups",
        "bugs": "Bug reports and debugging",
        "documentation": "Technical documentation",
        "git": "Git and pull requests",
    }
    counts = {category: sum(1 for item in _phrases if item["category"] == category)
              for category in labels}
    return {"count": len(labels), "items": [
        {"id": category, "label": labels[category], "phrase_count": counts[category]}
        for category in labels
    ]}


@app.get("/stats", tags=["progress"])
def stats() -> dict:
    total = len(_attempts)
    correct = sum(1 for attempt in _attempts if attempt["correct"])
    return {
        "phrase_count": len(_phrases),
        "total_attempts": total,
        "correct_answers": correct,
        "incorrect_answers": total - correct,
        "accuracy_percent": round(correct / total * 100, 2) if total else 0.0,
    }
