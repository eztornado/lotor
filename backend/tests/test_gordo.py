"""Tests del módulo de El Gordo (datos, generador y API)."""

from __future__ import annotations

import datetime as dt

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import gordo as gordo_api
from app.services.gordo_data import (
    Draw,
    GordoDataManager,
    get_gordo_data_manager,
    next_gordo_date,
)
from app.services.gordo_generator import (
    GordoConfig,
    PRIZE_COUNTS,
    STRATEGIES,
    TOTAL_COMBINATIONS,
    generate_gordo,
    get_gordo_model,
)


@pytest.fixture(scope="module")
def manager() -> GordoDataManager:
    return get_gordo_data_manager()


@pytest.fixture(scope="module")
def draws(manager: GordoDataManager) -> list[Draw]:
    data = manager.load()
    assert data, "El dataset de El Gordo no debe estar vacío"
    return data


@pytest.fixture(scope="module")
def fast_config() -> GordoConfig:
    return GordoConfig(
        candidate_count=4_000,
        pool_size=400,
        simulations=4_000,
        local_search_candidates=150,
        local_search_passes=1,
    )


@pytest.fixture(scope="module")
def client() -> TestClient:
    app = FastAPI()
    app.include_router(gordo_api.router, prefix="/api/v1/gordo")
    return TestClient(app)


def test_dataset_is_valid(draws: list[Draw]) -> None:
    assert len(draws) > 1_100
    assert draws[0].date > draws[-1].date  # orden descendente
    assert draws[-1].date == dt.date(2005, 2, 6)
    for draw in draws[:200]:
        assert len(draw.numbers) == 5
        assert len(set(draw.numbers)) == 5
        assert all(1 <= number <= 54 for number in draw.numbers)
        assert draw.key_number is not None
        assert 0 <= draw.key_number <= 9


def test_prize_math() -> None:
    assert TOTAL_COMBINATIONS == 31_625_100
    assert sum(PRIZE_COUNTS.values()) == 1_962_460
    assert PRIZE_COUNTS["1"] == 1
    assert PRIZE_COUNTS["8"] == 1_658_160


def test_next_draw_is_sunday() -> None:
    monday = dt.date(2026, 10, 19)
    assert next_gordo_date(None, dt.datetime(2026, 10, 19, 10, 0)) == dt.date(
        2026, 10, 25
    )
    sunday = dt.date(2026, 10, 25)
    # Antes de la hora del sorteo, el próximo es hoy.
    assert next_gordo_date(None, dt.datetime(2026, 10, 25, 10, 0)) == sunday
    # Después de la hora del sorteo, el siguiente domingo.
    assert next_gordo_date(None, dt.datetime(2026, 10, 25, 22, 0)) == dt.date(
        2026, 11, 1
    )
    # Si el dataset ya tiene el sorteo de hoy, avanzamos una semana.
    assert next_gordo_date(sunday, dt.datetime(2026, 10, 25, 10, 0)) == dt.date(
        2026, 11, 1
    )
    assert monday.weekday() == 0


def test_single_ticket_exact_probabilities(
    draws: list[Draw], fast_config: GordoConfig
) -> None:
    result = generate_gordo(
        count=1, strategy="big_prize", seed=1, draws=draws, config=fast_config
    )
    theoretical = result["portfolio"]["theoretical"]
    assert theoretical["exact"] is True
    assert theoretical["prob_1"] == pytest.approx(1 / TOTAL_COMBINATIONS)
    assert theoretical["prob_2"] == pytest.approx(9 / TOTAL_COMBINATIONS)
    assert theoretical["prob_3"] == pytest.approx(245 / TOTAL_COMBINATIONS)
    assert theoretical["prob_4"] == pytest.approx(2_205 / TOTAL_COMBINATIONS)
    assert theoretical["prob_5"] == pytest.approx(11_760 / TOTAL_COMBINATIONS)
    assert theoretical["prob_6"] == pytest.approx(105_840 / TOTAL_COMBINATIONS)
    assert theoretical["prob_7"] == pytest.approx(184_240 / TOTAL_COMBINATIONS)
    assert theoretical["prob_8"] == pytest.approx(1_658_160 / TOTAL_COMBINATIONS)
    assert theoretical["prob_any_prize"] == pytest.approx(1_962_460 / TOTAL_COMBINATIONS)
    assert theoretical["prob_any_prize_one_in"] == pytest.approx(16.12, abs=0.01)
    assert theoretical["prob_reintegro"] == pytest.approx(0.1)
    assert theoretical["prob_any_return"] == pytest.approx(
        1.0 - (1.0 - 1_962_460 / TOTAL_COMBINATIONS) * 0.9
    )
    assert theoretical["reintegro_eur"] == pytest.approx(1.5)


def test_generate_ten_is_disjoint_and_covers_keys(
    draws: list[Draw], fast_config: GordoConfig
) -> None:
    result = generate_gordo(
        count=10, strategy="big_prize", seed=123, draws=draws, config=fast_config
    )
    assert len(result["combinations"]) == 10
    tickets = [set(combo["numbers"]) for combo in result["combinations"]]
    assert all(len(ticket) == 5 for ticket in tickets)
    for left in range(len(tickets)):
        for right in range(left + 1, len(tickets)):
            assert not tickets[left].intersection(tickets[right])

    numbers = [number for ticket in tickets for number in ticket]
    assert len(numbers) == len(set(numbers)) == 50
    assert result["portfolio"]["coverage"]["unique_numbers"] == 50
    assert result["portfolio"]["coverage"]["numbers_pct"] == pytest.approx(92.59)
    assert result["portfolio"]["coverage"]["numbers_possible_pct"] == 100.0

    keys = [combo["key_number"] for combo in result["combinations"]]
    assert sorted(keys) == list(range(10))
    assert result["portfolio"]["keys"]["distinct"] == 10
    assert result["portfolio"]["keys"]["guaranteed_match"] is True
    assert result["portfolio"]["theoretical"]["prob_key_match"] == 1.0
    assert result["portfolio"]["theoretical"]["prob_reintegro"] == 1.0
    assert result["portfolio"]["theoretical"]["prob_any_return"] == 1.0
    assert result["portfolio"]["theoretical"]["expected_reintegro_eur"] == pytest.approx(
        1.5
    )
    assert result["portfolio"]["theoretical"]["jackpot_one_in"] == pytest.approx(
        TOTAL_COMBINATIONS / 10
    )


def test_portfolio_probabilities_are_consistent(
    draws: list[Draw], fast_config: GordoConfig
) -> None:
    result = generate_gordo(
        count=10, strategy="coverage", seed=55, draws=draws, config=fast_config
    )
    theoretical = result["portfolio"]["theoretical"]
    total = sum(theoretical[f"prob_{category}"] for category in range(1, 9))
    assert total == pytest.approx(theoretical["prob_any_prize"])
    assert theoretical["prob_5_plus"] == pytest.approx(
        theoretical["prob_1"] + theoretical["prob_2"]
    )
    assert theoretical["prob_2_plus"] == pytest.approx(total)
    assert 0.55 < theoretical["prob_any_prize"] < 0.56
    assert theoretical["prob_any_return"] == pytest.approx(1.0)
    simulation = result["portfolio"]["simulation"]
    assert abs(simulation["prob_any_prize"] - theoretical["prob_any_prize"]) < 0.02
    assert abs(simulation["prob_any_return"] - theoretical["prob_any_return"]) < 0.01
    assert abs(simulation["prob_reintegro"] - theoretical["prob_reintegro"]) < 0.01


@pytest.mark.parametrize("count", [1, 2, 3, 5, 8, 9, 10])
def test_generate_counts(
    draws: list[Draw], fast_config: GordoConfig, count: int
) -> None:
    result = generate_gordo(
        count=count, strategy="balanced", seed=7, draws=draws, config=fast_config
    )
    assert len(result["combinations"]) == count
    tickets = [tuple(combo["numbers"]) for combo in result["combinations"]]
    assert len(set(tickets)) == count
    for combo in result["combinations"]:
        assert len(combo["numbers"]) == 5
        assert len(set(combo["numbers"])) == 5
        assert all(1 <= number <= 54 for number in combo["numbers"])
        assert 0 <= combo["key_number"] <= 9
    assert result["portfolio"]["coverage"]["unique_numbers"] == 5 * count
    assert result["portfolio"]["keys"]["distinct"] == count
    assert result["portfolio"]["theoretical"]["exact"] is True


@pytest.mark.parametrize("strategy", list(STRATEGIES))
def test_all_strategies(
    draws: list[Draw], fast_config: GordoConfig, strategy: str
) -> None:
    result = generate_gordo(
        count=6, strategy=strategy, seed=99, draws=draws, config=fast_config
    )
    assert len(result["combinations"]) == 6
    assert result["strategy"] == strategy
    assert result["portfolio"]["theoretical"]["prob_any_prize"] > 0
    assert result["portfolio"]["theoretical"]["exact"] is True


def test_generate_is_reproducible(
    draws: list[Draw], fast_config: GordoConfig
) -> None:
    first = generate_gordo(
        count=5, strategy="big_prize", seed=2024, draws=draws, config=fast_config
    )
    second = generate_gordo(
        count=5, strategy="big_prize", seed=2024, draws=draws, config=fast_config
    )
    assert [combo["numbers"] for combo in first["combinations"]] == [
        combo["numbers"] for combo in second["combinations"]
    ]
    assert [combo["key_number"] for combo in first["combinations"]] == [
        combo["key_number"] for combo in second["combinations"]
    ]


def test_generate_rejects_invalid(draws: list[Draw]) -> None:
    with pytest.raises(ValueError):
        generate_gordo(count=0, draws=draws)
    with pytest.raises(ValueError):
        generate_gordo(count=11, draws=draws)
    with pytest.raises(ValueError):
        generate_gordo(count=5, strategy="no-existe", draws=draws)


def test_model_cache_is_shared() -> None:
    model_a = get_gordo_model()
    model_b = get_gordo_model()
    assert model_a is model_b


def test_api_meta_and_strategies(client: TestClient) -> None:
    response = client.get("/api/v1/gordo/meta")
    assert response.status_code == 200
    payload = response.json()
    assert payload["game"]["name"] == "El Gordo de la Primitiva"
    assert payload["game"]["max_number"] == 54
    assert payload["game"]["key_range"] == [0, 9]
    assert set(payload["strategies"]) == set(STRATEGIES)
    assert payload["dataset"]["total_draws"] > 1_100
    assert payload["dataset"]["last_draw"]["key_number"] is not None


def test_api_next_draw(client: TestClient) -> None:
    response = client.get("/api/v1/gordo/next-draw")
    assert response.status_code == 200
    payload = response.json()
    assert dt.date.fromisoformat(payload["next_draw"]).weekday() == 6


def test_api_history(client: TestClient) -> None:
    response = client.get("/api/v1/gordo/history?limit=10")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 10
    assert len(payload[0]["numbers"]) == 5
    assert 0 <= payload[0]["key_number"] <= 9


def test_api_stats(client: TestClient) -> None:
    response = client.get("/api/v1/gordo/stats")
    assert response.status_code == 200
    payload = response.json()
    assert "hot_numbers" in payload["analysis"]
    assert "key" in payload["analysis"]
    assert payload["dataset"]["total_draws"] > 1_100
    assert payload["model"]["total_combinations"] == TOTAL_COMBINATIONS
    assert payload["model"]["ticket_odds"]["reintegro"] == pytest.approx(0.1)
    assert payload["model"]["ticket_odds"]["any_return"] == pytest.approx(
        1.0 - (1.0 - 1_962_460 / TOTAL_COMBINATIONS) * 0.9
    )
    assert payload["model"]["reintegro_plays"] == 3_162_510


def test_api_generate_post(client: TestClient) -> None:
    response = client.post(
        "/api/v1/gordo/generate",
        json={"count": 10, "strategy": "big_prize", "seed": 42},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 10
    assert len(payload["combinations"]) == 10
    assert payload["portfolio"]["coverage"]["unique_numbers"] == 50
    assert payload["portfolio"]["theoretical"]["exact"] is True
    assert payload["dataset"]["next_draw"]


def test_api_generate_validation(client: TestClient) -> None:
    response = client.post(
        "/api/v1/gordo/generate",
        json={"count": 11, "strategy": "big_prize"},
    )
    assert response.status_code == 422
    response = client.get("/api/v1/gordo/generate?count=10&strategy=invalida")
    assert response.status_code == 400
