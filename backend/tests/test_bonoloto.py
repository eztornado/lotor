"""Tests del módulo de Bonoloto (datos, generador y API)."""

from __future__ import annotations

import datetime as dt

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import bonoloto as bonoloto_api
from app.services.bonoloto_data import (
    BonolotoDataManager,
    Draw,
    get_bonoloto_data_manager,
    next_bonoloto_date,
)
from app.services.bonoloto_generator import (
    STRATEGIES,
    BonolotoConfig,
    get_bonoloto_model,
    generate_bonoloto,
)


@pytest.fixture(scope="module")
def manager() -> BonolotoDataManager:
    return get_bonoloto_data_manager()


@pytest.fixture(scope="module")
def draws(manager: BonolotoDataManager) -> list[Draw]:
    data = manager.load()
    assert data, "El dataset de Bonoloto no debe estar vacío"
    return data


@pytest.fixture(scope="module")
def client() -> TestClient:
    app = FastAPI()
    app.include_router(bonoloto_api.router, prefix="/api/v1/bonoloto")
    return TestClient(app)


def test_dataset_is_valid(draws: list[Draw]) -> None:
    assert len(draws) > 9_000
    assert draws[0].date > draws[-1].date  # orden descendente
    for draw in draws[:200]:
        assert len(draw.numbers) == 6
        assert len(set(draw.numbers)) == 6
        assert all(1 <= number <= 49 for number in draw.numbers)
        assert draw.reintegro is None or 0 <= draw.reintegro <= 9


def test_next_draw_never_is_sunday() -> None:
    monday = dt.date(2026, 10, 19)
    assert next_bonoloto_date(monday, dt.datetime(2026, 10, 19, 10, 0)).weekday() != 6
    saturday = dt.date(2026, 10, 17)
    assert next_bonoloto_date(saturday, dt.datetime(2026, 10, 19, 10, 0)) == dt.date(2026, 10, 19)
    # Después de la hora de sorteo, el siguiente día.
    assert next_bonoloto_date(monday, dt.datetime(2026, 10, 19, 23, 0)) == dt.date(2026, 10, 20)


def test_generate_covers_all_numbers_for_ten(draws: list[Draw]) -> None:
    result = generate_bonoloto(count=10, strategy="big_prize", seed=123, draws=draws)
    numbers = [number for combo in result["combinations"] for number in combo["numbers"]]
    assert len(set(numbers)) == 49
    assert result["portfolio"]["coverage"]["unique_numbers"] == 49
    assert result["portfolio"]["coverage"]["numbers_pct"] == 100.0
    # Con 10 apuestas se cubren los 10 reintegros.
    assert result["portfolio"]["reintegros"]["distinct"] == 10
    assert result["portfolio"]["reintegros"]["guaranteed_match"] is True
    assert result["portfolio"]["theoretical"]["jackpot_one_in"] == pytest.approx(
        13_983_816 / 10
    )


@pytest.mark.parametrize("count", [1, 2, 3, 5, 8, 9, 10])
def test_generate_counts(draws: list[Draw], count: int) -> None:
    result = generate_bonoloto(count=count, strategy="balanced", seed=7, draws=draws)
    assert len(result["combinations"]) == count
    tickets = [tuple(combo["numbers"]) for combo in result["combinations"]]
    assert len(set(tickets)) == count
    for combo in result["combinations"]:
        assert len(combo["numbers"]) == 6
        assert len(set(combo["numbers"])) == 6
        assert all(1 <= number <= 49 for number in combo["numbers"])
        assert 0 <= combo["reintegro"] <= 9
    target = min(49, 6 * count)
    assert result["portfolio"]["coverage"]["unique_numbers"] == target
    assert result["portfolio"]["reintegros"]["distinct"] == count


@pytest.mark.parametrize("strategy", list(STRATEGIES))
def test_all_strategies(draws: list[Draw], strategy: str) -> None:
    result = generate_bonoloto(count=6, strategy=strategy, seed=99, draws=draws)
    assert len(result["combinations"]) == 6
    assert result["strategy"] == strategy
    assert result["portfolio"]["theoretical"]["prob_3_plus"] > 0


def test_generate_is_reproducible(draws: list[Draw]) -> None:
    first = generate_bonoloto(count=5, strategy="big_prize", seed=2024, draws=draws)
    second = generate_bonoloto(count=5, strategy="big_prize", seed=2024, draws=draws)
    assert [combo["numbers"] for combo in first["combinations"]] == [
        combo["numbers"] for combo in second["combinations"]
    ]


def test_generate_rejects_invalid(draws: list[Draw]) -> None:
    with pytest.raises(ValueError):
        generate_bonoloto(count=0, draws=draws)
    with pytest.raises(ValueError):
        generate_bonoloto(count=11, draws=draws)
    with pytest.raises(ValueError):
        generate_bonoloto(count=5, strategy="no-existe", draws=draws)


def test_model_cache_is_shared() -> None:
    model_a = get_bonoloto_model()
    model_b = get_bonoloto_model()
    assert model_a is model_b


def test_api_meta_and_strategies(client: TestClient) -> None:
    response = client.get("/api/v1/bonoloto/meta")
    assert response.status_code == 200
    payload = response.json()
    assert payload["game"]["name"] == "Bonoloto"
    assert payload["game"]["max_number"] == 49
    assert set(payload["strategies"]) == set(STRATEGIES)
    assert payload["dataset"]["total_draws"] > 9_000


def test_api_history(client: TestClient) -> None:
    response = client.get("/api/v1/bonoloto/history?limit=10")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 10
    assert len(payload[0]["numbers"]) == 6


def test_api_stats(client: TestClient) -> None:
    response = client.get("/api/v1/bonoloto/stats")
    assert response.status_code == 200
    payload = response.json()
    assert "hot_numbers" in payload["analysis"]
    assert payload["dataset"]["total_draws"] > 9_000


def test_api_generate_post(client: TestClient) -> None:
    response = client.post(
        "/api/v1/bonoloto/generate",
        json={"count": 10, "strategy": "big_prize", "seed": 42},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 10
    assert len(payload["combinations"]) == 10
    assert payload["portfolio"]["coverage"]["unique_numbers"] == 49
    assert payload["dataset"]["next_draw"]


def test_api_generate_validation(client: TestClient) -> None:
    response = client.post(
        "/api/v1/bonoloto/generate",
        json={"count": 11, "strategy": "big_prize"},
    )
    assert response.status_code == 422
    response = client.get(
        "/api/v1/bonoloto/generate?count=10&strategy=invalida"
    )
    assert response.status_code == 400
