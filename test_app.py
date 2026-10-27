"""Автоматические тесты DevEnglish API."""
import copy
import pytest
from fastapi.testclient import TestClient
import app_final


@pytest.fixture(autouse=True)
def reset_data():
    app_final._phrases.clear()
    app_final._phrases.extend(copy.deepcopy(app_final._INITIAL_PHRASES))
    app_final._attempts.clear()
    yield
    app_final._phrases.clear()
    app_final._phrases.extend(copy.deepcopy(app_final._INITIAL_PHRASES))
    app_final._attempts.clear()


@pytest.fixture
def client():
    with TestClient(app_final.app) as test_client:
        yield test_client


def test_health_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_version_returns_configured_version(client):
    response = client.get("/version")
    assert response.status_code == 200
    assert response.json()["version"] == app_final.APP_VERSION


def test_filter_by_category_and_level(client):
    response = client.get("/phrases", params={"category": "code_review", "level": "intermediate"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 2
    assert all(item["category"] == "code_review" and item["level"] == "intermediate" for item in payload["items"])


def test_search_finds_phrase(client):
    response = client.get("/phrases", params={"q": "breaking change"})
    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert response.json()["items"][0]["id"] == "de-002"


def test_phrase_public_view_does_not_leak_quiz_answer_options(client):
    response = client.get("/phrases/de-001")
    assert response.status_code == 200
    assert "correct_answer" not in response.json()
    assert "options" not in response.json()


def test_quiz_question_returns_options_without_correct_answer(client):
    response = client.get("/quiz/question", params={"phrase_id": "de-001"})
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["options"]) == 4
    assert "correct_answer" not in payload


def test_correct_answer_updates_stats(client):
    response = client.post("/quiz/answer", json={"phrase_id": "de-001", "answer": "Можешь посмотреть это?"})
    assert response.status_code == 200
    assert response.json()["correct"] is True
    stats = client.get("/stats").json()
    assert stats["total_attempts"] == 1
    assert stats["correct_answers"] == 1
    assert stats["accuracy_percent"] == 100.0


def test_wrong_answer_is_recorded(client):
    response = client.post("/quiz/answer", json={"phrase_id": "de-001", "answer": "Давайте выпустим релиз."})
    assert response.status_code == 200
    assert response.json()["correct"] is False
    assert client.get("/stats").json()["incorrect_answers"] == 1


def test_duplicate_phrase_is_rejected(client):
    response = client.post("/phrases", json={
        "phrase": "Could you take a look at this?", "meaning_ru": "Можешь посмотреть это?",
        "category": "code_review", "level": "beginner", "example": "Could you take a look at this?",
        "example_ru": "Можешь посмотреть это?", "options": ["Можешь посмотреть это?", "Нет", "Да", "Позже"]
    })
    assert response.status_code == 409


def test_unknown_phrase_returns_404(client):
    response = client.get("/phrases/unknown")
    assert response.status_code == 404


def test_invalid_category_is_rejected(client):
    response = client.get("/phrases", params={"category": "music"})
    assert response.status_code == 422


def test_create_phrase_requires_correct_answer_inside_options(client):
    response = client.post("/phrases", json={
        "phrase": "The build failed.", "meaning_ru": "Сборка завершилась с ошибкой.",
        "category": "bugs", "level": "beginner", "example": "The build failed in CI.",
        "example_ru": "Сборка завершилась с ошибкой в CI.",
        "options": ["Авария устранена.", "Тесты прошли.", "Ветка удалена.", "Релиз опубликован."]
    })
    assert response.status_code == 422


def test_categories_lists_counts(client):
    response = client.get("/categories")
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 5
    by_id = {item["id"]: item for item in payload["items"]}
    assert by_id["code_review"]["phrase_count"] == 4


def test_quiz_empty_filter_returns_404(client):
    response = client.get("/quiz/question", params={"category": "meetings", "level": "advanced"})
    assert response.status_code == 404
