"""Tests de La Quiniela: datos, modelo, generador y API."""

from __future__ import annotations

import datetime as dt
import math

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import quiniela as quiniela_api
from app.services.quiniela_data import (
    LEAGUE_LABELS,
    TOTAL_MATCHES,
    get_quiniela_data_manager,
)
from app.services.quiniela_generator import (
    GAME_INFO,
    MAX_EXPANDED_COLUMNS,
    STRATEGIES,
    build_ticket,
    generate_prediction,
    generate_quiniela,
    poisson_binomial,
)
from app.services.quiniela_model import (
    SIGNS,
    QuinielaModel,
    get_quiniela_model,
)


@pytest.fixture(scope="module")
def manager():
    return get_quiniela_data_manager()


@pytest.fixture(scope="module")
def matches(manager):
    data = manager.load_matches()
    assert data, "El dataset de La Quiniela no debe estar vacío"
    return data


@pytest.fixture(scope="module")
def model(matches) -> QuinielaModel:
    return get_quiniela_model(matches)


@pytest.fixture(scope="module")
def jornada(manager):
    selected = manager.next_jornada(dt.date(2026, 10, 22))
    assert selected is not None
    return selected


@pytest.fixture(scope="module")
def predictions(model, jornada):
    return model.predict_jornada(jornada)


@pytest.fixture(scope="module")
def client() -> TestClient:
    app = FastAPI()
    app.include_router(quiniela_api.router, prefix="/api/v1/quiniela")
    return TestClient(app)


# ----------------------------------------------------------------------
# Datos
# ----------------------------------------------------------------------
def test_dataset_is_valid(matches) -> None:
    assert len(matches) > 15_000
    assert matches[0].date < matches[-1].date
    for match in matches[:300]:
        assert match.home_team != match.away_team
        assert 0 <= match.home_goals <= 20
        assert 0 <= match.away_goals <= 20
        assert match.result in {"H", "D", "A"}
        assert match.league in LEAGUE_LABELS


def test_jornada_is_complete(jornada) -> None:
    assert len(jornada.fixtures) == TOTAL_MATCHES
    assert any(fixture.is_pleno for fixture in jornada.fixtures)
    numbers = [fixture.match_number for fixture in jornada.fixtures]
    assert numbers == list(range(1, TOTAL_MATCHES + 1))


def test_dataset_has_multiple_competitions(manager) -> None:
    summary = manager.summary()
    assert summary["total_matches"] > 15_000
    assert summary["total_teams"] > 100
    assert summary["next_jornada"]["matches"] == TOTAL_MATCHES


def test_fixture_competition_inference(jornada) -> None:
    assert all(fixture.competition for fixture in jornada.fixtures)
    assert jornada.competitions


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("AT.MADRID", "ATLETICO MADRID"),
        ("ATH.CLUB", "ATHLETIC CLUB"),
        ("R.MADRID", "REAL MADRID"),
        ("R.SOCIEDAD", "REAL SOCIEDAD"),
        ("R.OVIEDO", "REAL OVIEDO"),
        ("R.ZARAGOZA", "REAL ZARAGOZA"),
        ("REC.HUELVA", "RECREATIVO HUELVA"),
    ],
)
def test_source_abbreviations_resolve(manager, raw, expected) -> None:
    team, known = manager.resolver().resolve(raw)
    assert known, f"{raw} debería resolver a un equipo del histórico"
    assert team == expected


def test_cross_border_matches_are_european(manager) -> None:
    fixtures = {
        (fixture.home_team, fixture.away_team): fixture
        for fixture in manager.load_fixtures()
    }
    for pair in (("BARCELONA", "ASTON VILLA"), ("VILLARREAL", "PSG")):
        if pair in fixtures:
            assert fixtures[pair].competition == "Europea"


def test_mixed_jornada_is_labelled(manager) -> None:
    for selected in manager.jornadas():
        if len(selected.competitions) > 1:
            assert selected.competition == "Mixta"
        elif selected.competitions:
            assert selected.competition == selected.competitions[0]


# ----------------------------------------------------------------------
# Modelo
# ----------------------------------------------------------------------
def test_predictions_have_valid_probabilities(predictions) -> None:
    assert len(predictions) == TOTAL_MATCHES
    for prediction in predictions:
        assert set(prediction.probabilities) == set(SIGNS)
        assert sum(prediction.probabilities.values()) == pytest.approx(1.0, abs=1e-9)
        assert all(0.0 <= value <= 1.0 for value in prediction.probabilities.values())
        assert prediction.most_likely_score
        assert 0.0 <= prediction.confidence <= 1.0
        assert prediction.data_quality in {"alta", "media", "baja", "sin datos"}
        assert prediction.expected_goals["home"] >= 0
        assert prediction.expected_goals["away"] >= 0
        assert len(prediction.score_options) == 5
        assert prediction.home["name"]
        assert prediction.away["name"]


def test_known_teams_are_resolved(predictions) -> None:
    # Al menos los equipos de Primera/Segunda deben tener histórico.
    known = [
        prediction
        for prediction in predictions
        if prediction.home["known"] or prediction.away["known"]
    ]
    assert known, "La jornada debe tener equipos con histórico"
    for prediction in known:
        if prediction.home["known"]:
            assert prediction.home["matches"] > 0
            assert prediction.home["elo"] is not None
        if prediction.away["known"]:
            assert prediction.away["matches"] > 0
            assert prediction.away["elo"] is not None


def test_pleno_is_last_and_has_scores(predictions) -> None:
    pleno = next(prediction for prediction in predictions if prediction.is_pleno)
    assert pleno.match_number == 15
    assert pleno.most_likely_score
    assert 0.0 < pleno.score_probability <= 1.0


def test_model_summary_and_teams(model) -> None:
    summary = model.dataset_summary()
    assert summary["total_matches"] > 15_000
    assert summary["teams"] > 100
    assert 0.0 < summary["home_advantage"] < 1.0
    teams = model.top_teams(5)
    assert len(teams) == 5
    assert all(team["team"] for team in teams)
    league_stats = model.league_stats()
    assert league_stats
    assert all(0 <= league["home_win_pct"] <= 100 for league in league_stats)


# ----------------------------------------------------------------------
# Distribuciones y boletos
# ----------------------------------------------------------------------
def test_poisson_binomial_matches_binomial() -> None:
    distribution = poisson_binomial([0.5] * 4)
    expected = [1, 4, 6, 4, 1]
    for probability, count in zip(distribution, expected):
        assert probability == pytest.approx(count / 16, abs=1e-12)


def test_poisson_binomial_certain_hits() -> None:
    assert poisson_binomial([1.0, 1.0, 0.0]) == pytest.approx([0.0, 0.0, 1.0, 0.0])


def test_single_ticket_metrics() -> None:
    probabilities = [{"1": 0.5, "X": 0.3, "2": 0.2} for _ in range(14)]
    ticket = build_ticket(
        [("1",) for _ in range(14)], probabilities, (1, 0), 0.1
    )
    assert ticket.columns == 1
    assert ticket.cost == pytest.approx(0.75)
    assert ticket.expected_hits == pytest.approx(7.0)
    assert ticket.guaranteed_hits == 0
    assert sum(ticket.hits_14_distribution) == pytest.approx(1.0)
    assert sum(ticket.hit_distribution) == pytest.approx(1.0)
    assert ticket.category_probabilities["10"] > 0


def test_multiple_cost_and_expansion() -> None:
    probabilities = [{"1": 0.5, "X": 0.3, "2": 0.2} for _ in range(14)]
    signs = [("1",)] * 12 + [("1", "X"), ("1", "X", "2")]
    ticket = build_ticket(signs, probabilities, (1, 0), 0.1)
    assert ticket.doubles == 1
    assert ticket.triples == 1
    assert ticket.columns == 6
    assert ticket.cost == pytest.approx(4.5)
    assert ticket.guaranteed_hits == 1
    assert ticket.coverage[-1] == pytest.approx(1.0)
    assert ticket.coverage[-2] == pytest.approx(0.8)


# ----------------------------------------------------------------------
# Generador
# ----------------------------------------------------------------------
@pytest.mark.parametrize("strategy", list(STRATEGIES))
def test_generate_multiple_respects_budget(strategy: str) -> None:
    result = generate_quiniela(
        jornada=17,
        mode="multiple",
        budget=20,
        max_doubles=4,
        max_triples=2,
        strategy=strategy,
        seed=123,
    )
    ticket = result["tickets"][0]
    assert ticket["cost"] <= 20 + 1e-9
    assert ticket["doubles"] <= 4
    assert ticket["triples"] <= 2
    assert ticket["columns"] >= 1
    assert result["portfolio"]["method"] == "exact_poisson_binomial"
    assert sum(ticket["hit_distribution"]) == pytest.approx(1.0)
    assert sum(ticket["category_probabilities"].values()) <= 1.0 + 1e-9
    assert result["jornada"]["jornada"] == 17
    assert len(result["matches"]) == TOTAL_MATCHES


def test_generate_multiple_normalizes_strategy() -> None:
    result = generate_quiniela(
        jornada=17,
        mode="multiple",
        budget=20,
        max_doubles=4,
        max_triples=2,
        strategy="jackpot",
        seed=7,
    )
    assert result["strategy"] == "balanced"
    assert result["strategy_label"] == "Equilibrada"


def test_generate_multiple_with_minimum_budget() -> None:
    result = generate_quiniela(
        jornada=17,
        mode="multiple",
        budget=0.75,
        max_doubles=0,
        max_triples=0,
        seed=1,
    )
    ticket = result["tickets"][0]
    assert ticket["columns"] == 1
    assert ticket["cost"] == pytest.approx(0.75)
    assert ticket["doubles"] == 0
    assert ticket["triples"] == 0


def test_generate_multiple_can_use_budget_above_legacy_cap() -> None:
    result = generate_quiniela(
        jornada=17,
        mode="multiple",
        budget=100,
        max_doubles=7,
        max_triples=4,
        seed=5,
    )
    assert result["budget"]["max_columns"] > 64
    assert result["tickets"][0]["cost"] > 48


def test_generate_multiple_expansion_matches_columns() -> None:
    result = generate_quiniela(
        jornada=17, mode="multiple", budget=20, max_doubles=4, max_triples=2, seed=2
    )
    ticket = result["tickets"][0]
    if ticket["columns"] <= MAX_EXPANDED_COLUMNS:
        assert ticket["expanded_columns"] is not None
        assert len(ticket["expanded_columns"]) == ticket["columns"]


def test_generate_simple_portfolio() -> None:
    result = generate_quiniela(
        jornada=17,
        mode="simple",
        count=5,
        budget=10,
        strategy="balanced",
        seed=9,
    )
    portfolio = result["portfolio"]
    assert portfolio["tickets"] == 5
    assert portfolio["columns"] == 5
    assert portfolio["cost"] == pytest.approx(3.75)
    assert portfolio["method"] == "monte_carlo"
    assert len(result["tickets"]) == 5
    assert sum(portfolio["hit_distribution"]) == pytest.approx(1.0)
    for ticket in result["tickets"]:
        assert ticket["columns"] == 1
        assert ticket["cost"] == pytest.approx(0.75)


def test_generate_simple_budget_caps_count() -> None:
    result = generate_quiniela(
        jornada=17, mode="simple", count=10, budget=3, seed=3
    )
    assert result["portfolio"]["tickets"] == 4
    assert result["portfolio"]["cost"] <= 3


def test_generate_is_reproducible() -> None:
    first = generate_quiniela(
        jornada=17, mode="multiple", budget=20, seed=2026
    )
    second = generate_quiniela(
        jornada=17, mode="multiple", budget=20, seed=2026
    )
    assert first["tickets"] == second["tickets"]
    assert first["seed"] == second["seed"]


def test_generate_simple_is_reproducible() -> None:
    first = generate_quiniela(
        jornada=17, mode="simple", count=5, budget=10, seed=2026
    )
    second = generate_quiniela(
        jornada=17, mode="simple", count=5, budget=10, seed=2026
    )
    assert first["tickets"] == second["tickets"]
    assert first["portfolio"] == second["portfolio"]


def test_generate_rejects_invalid_input() -> None:
    with pytest.raises(ValueError):
        generate_quiniela(jornada=17, mode="invalid")
    with pytest.raises(ValueError):
        generate_quiniela(jornada=17, mode="multiple", budget=0.5)
    with pytest.raises(ValueError):
        generate_quiniela(jornada=17, mode="multiple", max_doubles=9)
    with pytest.raises(ValueError):
        generate_quiniela(jornada=17, mode="simple", count=11)


def test_generate_unknown_jornada() -> None:
    with pytest.raises(ValueError):
        generate_quiniela(jornada=999)


def test_game_info_and_disclaimer() -> None:
    result = generate_quiniela(jornada=17, mode="multiple", seed=4)
    assert result["game"]["matches"] == 15
    assert result["game"]["ticket_price_eur"] == 0.75
    assert "azar" in result["disclaimer"].lower()
    assert result["recommendations"]


def test_pleno_probability_is_consistent(predictions) -> None:
    pleno = next(prediction for prediction in predictions if prediction.is_pleno)
    scores = [option["score"] for option in pleno.score_options]
    assert pleno.most_likely_score in scores
    assert all(0.0 < option["probability"] <= 1.0 for option in pleno.score_options)
    assert sum(option["probability"] for option in pleno.score_options) <= 1.0 + 1e-6


def test_prediction_targets_top_prize() -> None:
    result = generate_prediction(
        jornada=17,
        budget=20,
        max_doubles=4,
        max_triples=2,
        seed=42,
    )
    ticket = result["tickets"][0]
    balanced = generate_quiniela(
        jornada=17,
        mode="multiple",
        budget=20,
        max_doubles=4,
        max_triples=2,
        seed=42,
    )["tickets"][0]
    assert result["strategy"] == "jackpot"
    assert result["target"]["objective"] == "max_probability_pleno_15"
    assert ticket["category_probabilities"]["15"] == pytest.approx(
        result["target"]["top_prize_probability"], abs=1e-6
    )
    # El objetivo es P(15), así que no puede ser peor que el boleto equilibrado.
    assert (
        ticket["category_probabilities"]["15"]
        >= balanced["category_probabilities"]["15"] - 1e-12
    )
    assert ticket["cost"] <= 20 + 1e-9
    assert result["reasoning"]
    assert result["model"]["type"].startswith("ensemble")


def test_prediction_alternatives_and_budget() -> None:
    result = generate_prediction(
        jornada=17,
        budget=10,
        max_doubles=3,
        max_triples=1,
        seed=7,
    )
    ticket = result["tickets"][0]
    assert ticket["cost"] <= 10 + 1e-9
    assert ticket["doubles"] <= 3
    assert ticket["triples"] <= 1
    assert isinstance(result["alternatives"], list)
    assert all(
        alternative["cost"] <= 10 + 1e-9 for alternative in result["alternatives"]
    )


# ----------------------------------------------------------------------
# API
# ----------------------------------------------------------------------
def test_api_meta(client) -> None:
    response = client.get("/api/v1/quiniela/meta")
    assert response.status_code == 200
    payload = response.json()
    assert payload["game"]["name"] == "La Quiniela"
    assert payload["next_jornada"]["matches"] == TOTAL_MATCHES
    assert set(payload["strategies"]) == set(STRATEGIES)


def test_api_jornadas(client) -> None:
    response = client.get("/api/v1/quiniela/jornadas")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) >= 3
    assert all(item["matches"] == TOTAL_MATCHES for item in payload)


def test_api_jornada(client) -> None:
    for path in ("/api/v1/quiniela/jornada", "/api/v1/quiniela/jornada/17"):
        response = client.get(path)
        assert response.status_code == 200
        payload = response.json()
        assert len(payload["matches"]) == TOTAL_MATCHES
        assert payload["jornada"]["jornada"] == 17
        assert payload["pleno"]["match_number"] == 15


def test_api_generate(client) -> None:
    response = client.post(
        "/api/v1/quiniela/generate",
        json={
            "mode": "multiple",
            "budget": 10,
            "max_doubles": 3,
            "max_triples": 1,
            "strategy": "balanced",
            "seed": 5,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["tickets"]
    assert payload["portfolio"]["cost"] <= 10
    assert payload["mode"] == "multiple"


def test_api_generate_get(client) -> None:
    response = client.get(
        "/api/v1/quiniela/generate?mode=simple&count=3&budget=5&seed=6"
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["portfolio"]["tickets"] == 3
    assert payload["portfolio"]["cost"] == pytest.approx(2.25)


def test_api_prediction(client) -> None:
    response = client.get(
        "/api/v1/quiniela/prediction?jornada=17&budget=10"
        "&max_doubles=3&max_triples=1&seed=11"
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "multiple"
    assert payload["strategy_label"] == "Máxima probabilidad del pleno"
    assert payload["tickets"][0]["cost"] <= 10 + 1e-9
    assert payload["target"]["objective"] == "max_probability_pleno_15"
    assert payload["target"]["top_prize_probability"] > 0
    assert payload["reasoning"]
    assert "backtest" in payload["model"]
    assert payload["jornada"]["jornada"] == 17


def test_api_generate_validation(client) -> None:
    response = client.post(
        "/api/v1/quiniela/generate",
        json={"mode": "multiple", "budget": 0.1},
    )
    assert response.status_code == 422
    response = client.get(
        "/api/v1/quiniela/generate?strategy=unknown"
    )
    assert response.status_code == 400


def test_api_history_and_stats(client) -> None:
    history = client.get("/api/v1/quiniela/history?limit=10")
    assert history.status_code == 200
    assert len(history.json()) == 10

    stats = client.get("/api/v1/quiniela/stats")
    assert stats.status_code == 200
    payload = stats.json()
    assert payload["dataset"]["total_matches"] > 15_000
    assert payload["leagues"]
    assert payload["top_teams"]
    assert "log_loss" in payload["backtest"]


def test_api_team(client) -> None:
    response = client.get("/api/v1/quiniela/teams/Real Madrid")
    assert response.status_code == 200
    payload = response.json()
    assert payload["team"]["known"] is True
    assert payload["team"]["matches"] > 0
    assert payload["recent"]


def test_api_team_unknown(client) -> None:
    response = client.get("/api/v1/quiniela/teams/CD.Inventado")
    assert response.status_code == 404


def test_api_unknown_jornada(client) -> None:
    response = client.get("/api/v1/quiniela/jornada/999")
    assert response.status_code == 404
