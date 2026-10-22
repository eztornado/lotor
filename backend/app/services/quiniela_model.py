"""
Modelo estadístico para La Quiniela.

Combina tres señales complementarias:

1. **Poisson Dixon-Coles con pesos temporales.** Estima ataque y defensa de
   cada equipo, la ventaja de jugar en casa y el nivel medio de cada liga.
   Los partidos recientes pesan más (vida media configurable) y los equipos
   con pocos datos se contraen hacia la media (regularización L2).
2. **Elo con diferencia de goles.** Rating incremental que funciona bien
   cuando dos equipos de ligas distintas se enfrentan (Copa, competiciones
   europeas) y como contraste del modelo Poisson.
3. **Prior de liga/competición.** Para equipos sin histórico (divisiones
   inferiores, Liga F, rivales europeos) se usa la media de su liga y un
   ajuste de nivel, con una confianza explícitamente baja.

La salida es una distribución completa de marcadores 0-8 goles por equipo.
De ella se derivan P(1), P(X), P(2), el marcador más probable del pleno y
las probabilidades de cada resultado. El modelo no "adivina" el fútbol:
estima probabilidades calibradas y las declara con su incertidumbre.
"""

from __future__ import annotations

import datetime as dt
import math
import threading
from collections import Counter
from dataclasses import dataclass, field
from typing import Iterable, Optional, Sequence

import numpy as np
from loguru import logger

from app.services.quiniela_data import (
    LEAGUE_LABELS,
    LEAGUE_OFFSETS,
    Match,
    TeamResolver,
    canonical_team,
    get_quiniela_data_manager,
    is_women_team,
)

MAX_GOALS = 8
SIGNS = ("1", "X", "2")


@dataclass(frozen=True, slots=True)
class QuinielaModelConfig:
    max_age_days: int = 2_400       # ~6,5 años de histórico
    half_life_days: float = 420.0   # los partidos pierden la mitad de peso cada ~14 meses
    elo_max_age_days: int = 3_000
    elo_k: float = 20.0
    elo_home_advantage: float = 65.0
    regularization: float = 0.06
    epochs: int = 260
    learning_rate: float = 0.045
    draw_rho: float = -0.08
    max_goals: int = MAX_GOALS
    simulations: int = 30_000


@dataclass(slots=True)
class TeamRating:
    team: str
    league: str
    league_name: str
    tier: int
    matches: int
    attack: float
    defense: float
    elo: float
    goals_for: float
    goals_against: float
    last_match: Optional[dt.date] = None
    form: list[str] = field(default_factory=list)

    @property
    def strength(self) -> float:
        return self.elo

    @property
    def attack_defense(self) -> float:
        return self.attack - self.defense


@dataclass(slots=True)
class MatchPrediction:
    match_number: int
    home_team: str
    away_team: str
    home_raw: str
    away_raw: str
    competition: str
    kickoff: str
    is_pleno: bool
    probabilities: dict[str, float]
    fair_odds: dict[str, float]
    expected_goals: dict[str, float]
    most_likely_score: str
    score_probability: float
    score_options: list[dict[str, object]]
    confidence: float
    data_quality: str
    home: dict[str, object]
    away: dict[str, object]
    h2h: dict[str, object]
    notes: list[str]
    is_women: bool = False

    def as_dict(self) -> dict[str, object]:
        return {
            "match_number": self.match_number,
            "home_team": self.home_raw,
            "away_team": self.away_raw,
            "home": self.home,
            "away": self.away,
            "competition": self.competition,
            "kickoff": self.kickoff,
            "is_pleno": self.is_pleno,
            "is_women": self.is_women,
            "probabilities": {
                sign: round(value, 6) for sign, value in self.probabilities.items()
            },
            "fair_odds": {
                sign: round(value, 3) for sign, value in self.fair_odds.items()
            },
            "expected_goals": {
                side: round(value, 3) for side, value in self.expected_goals.items()
            },
            "most_likely_score": self.most_likely_score,
            "score_probability": round(self.score_probability, 6),
            "score_options": self.score_options,
            "confidence": round(self.confidence, 4),
            "data_quality": self.data_quality,
            "h2h": self.h2h,
            "notes": self.notes,
        }


def _clip(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _poisson_pmf(lam: float, max_goals: int) -> np.ndarray:
    values = np.zeros(max_goals + 1)
    for goals in range(max_goals + 1):
        values[goals] = math.exp(-lam) * lam**goals / math.factorial(goals)
    return values


def _score_matrix(
    lambda_home: float,
    lambda_away: float,
    rho: float = -0.08,
    max_goals: int = MAX_GOALS,
) -> np.ndarray:
    """Matriz de marcadores con corrección Dixon-Coles en los resultados bajos."""
    home_pmf = _poisson_pmf(max(0.02, lambda_home), max_goals)
    away_pmf = _poisson_pmf(max(0.02, lambda_away), max_goals)
    matrix = np.outer(home_pmf, away_pmf)

    adjustments = {
        (0, 0): 1.0 - lambda_home * lambda_away * rho,
        (0, 1): 1.0 + lambda_home * rho,
        (1, 0): 1.0 + lambda_away * rho,
        (1, 1): 1.0 - rho,
    }
    for (home_goals, away_goals), factor in adjustments.items():
        matrix[home_goals, away_goals] *= max(0.01, factor)

    total = matrix.sum()
    return matrix / total if total else matrix


def _matrix_to_probabilities(matrix: np.ndarray) -> dict[str, float]:
    home = float(np.tril(matrix, -1).sum())
    draw = float(np.trace(matrix))
    away = float(np.triu(matrix, 1).sum())
    total = home + draw + away
    if total <= 0:
        return {"1": 1 / 3, "X": 1 / 3, "2": 1 / 3}
    return {"1": home / total, "X": draw / total, "2": away / total}


def _score_label(home_goals: int, away_goals: int) -> str:
    return f"{home_goals}-{away_goals}"


def _top_scores(matrix: np.ndarray, limit: int = 5) -> list[dict[str, object]]:
    options: list[tuple[float, int, int]] = []
    for home_goals in range(matrix.shape[0]):
        for away_goals in range(matrix.shape[1]):
            options.append((float(matrix[home_goals, away_goals]), home_goals, away_goals))
    options.sort(reverse=True)
    return [
        {
            "score": _score_label(home_goals, away_goals),
            "probability": round(probability, 6),
        }
        for probability, home_goals, away_goals in options[:limit]
    ]


def _result_from_goals(home_goals: int, away_goals: int) -> str:
    if home_goals > away_goals:
        return "H"
    if home_goals < away_goals:
        return "A"
    return "D"


class QuinielaModel:
    """Modelo cacheable de probabilidades por partido."""

    def __init__(
        self,
        matches: Sequence[Match],
        config: Optional[QuinielaModelConfig] = None,
        reference_date: Optional[dt.date] = None,
    ):
        self.config = config or QuinielaModelConfig()
        self.reference_date = reference_date or (
            max(match.date for match in matches) if matches else dt.date.today()
        )
        cutoff = self.reference_date - dt.timedelta(days=self.config.max_age_days)
        self.matches = [
            match
            for match in matches
            if cutoff <= match.date <= self.reference_date
        ]
        if not self.matches:
            self.matches = list(matches)

        self.resolver = TeamResolver(
            {match.home_team for match in self.matches}
            | {match.away_team for match in self.matches}
        )
        self.teams = sorted(
            {match.home_team for match in self.matches}
            | {match.away_team for match in self.matches}
        )
        self.team_index = {team: index for index, team in enumerate(self.teams)}

        self.team_matches: Counter[str] = Counter()
        self.team_goals_for: Counter[str] = Counter()
        self.team_goals_against: Counter[str] = Counter()
        self.team_last_match: dict[str, dt.date] = {}
        self.team_form: dict[str, list[str]] = {}
        self.team_league: dict[str, str] = {}
        self.team_league_name: dict[str, str] = {}
        self.team_tier: dict[str, int] = {}

        for match in self.matches:
            for team, goals_for, goals_against in (
                (match.home_team, match.home_goals, match.away_goals),
                (match.away_team, match.away_goals, match.home_goals),
            ):
                self.team_matches[team] += 1
                self.team_goals_for[team] += goals_for
                self.team_goals_against[team] += goals_against
                if team not in self.team_last_match or match.date > self.team_last_match[team]:
                    self.team_last_match[team] = match.date
                    self.team_league[team] = match.league
                    self.team_league_name[team] = match.league_name
                    self.team_tier[team] = match.tier
                if match.date > self.reference_date - dt.timedelta(days=550):
                    form = self.team_form.setdefault(team, [])
                    form.append(match.result if team == match.home_team else {"H": "A", "A": "H", "D": "D"}[match.result])

        # La forma se guarda del partido más reciente al más antiguo.
        self.team_form = {
            team: list(reversed(form[-5:])) for team, form in self.team_form.items()
        }

        self.league_counts: Counter[str] = Counter(match.league for match in self.matches)
        self.global_base = self._base_probabilities(self.matches)
        self.league_base: dict[str, dict[str, float]] = {}
        for league in self.league_counts:
            league_matches = [match for match in self.matches if match.league == league]
            self.league_base[league] = self._blend_base(
                self._base_probabilities(league_matches), self.global_base, weight=40
            )

        self.attack, self.defense, self.league_mu, self.home_advantage = self._fit_poisson()
        self.elo = self._fit_elo()
        self.team_ratings = self._build_team_ratings()

    # ------------------------------------------------------------------
    # Ajuste de modelos
    # ------------------------------------------------------------------
    @staticmethod
    def _base_probabilities(matches: Sequence[Match]) -> dict[str, float]:
        counts = Counter(match.result for match in matches)
        total = sum(counts.values())
        if total == 0:
            return {"1": 0.46, "X": 0.26, "2": 0.28}
        return {
            "1": (counts["H"] + 12) / (total + 26),
            "X": (counts["D"] + 7) / (total + 26),
            "2": (counts["A"] + 7) / (total + 26),
        }

    @staticmethod
    def _blend_base(
        local: dict[str, float], global_base: dict[str, float], weight: float
    ) -> dict[str, float]:
        return {
            sign: (local[sign] * weight + global_base[sign] * 20) / (weight + 20)
            for sign in SIGNS
        }

    def _fit_poisson(self) -> tuple[np.ndarray, np.ndarray, dict[str, float], float]:
        teams = self.teams
        team_index = self.team_index
        size = len(teams)
        if size == 0 or not self.matches:
            return np.zeros(0), np.zeros(0), {"SP1": math.log(1.35)}, 0.18

        leagues = sorted(self.league_counts)
        league_index = {league: index for index, league in enumerate(leagues)}
        league_matches = np.array(
            [league_index[match.league] for match in self.matches], dtype=np.int64
        )
        home = np.array([team_index[match.home_team] for match in self.matches], dtype=np.int64)
        away = np.array([team_index[match.away_team] for match in self.matches], dtype=np.int64)
        home_goals = np.array([match.home_goals for match in self.matches], dtype=np.float64)
        away_goals = np.array([match.away_goals for match in self.matches], dtype=np.float64)

        ages = np.array(
            [(self.reference_date - match.date).days for match in self.matches],
            dtype=np.float64,
        )
        weights = np.maximum(
            0.02, 0.5 ** (ages / max(1.0, self.config.half_life_days))
        )

        total_goals = float(home_goals.sum() + away_goals.sum())
        total_matches = max(1, len(self.matches))
        global_mu = math.log(max(0.3, total_goals / (2 * total_matches)))
        mu = np.full(len(leagues), global_mu, dtype=np.float64)
        for league, index in league_index.items():
            league_mask = league_matches == index
            goals = float(home_goals[league_mask].sum() + away_goals[league_mask].sum())
            matches_count = max(1, int(league_mask.sum()))
            mu[index] = math.log(max(0.3, goals / (2 * matches_count)))

        attack = np.zeros(size, dtype=np.float64)
        defense = np.zeros(size, dtype=np.float64)
        home_advantage = math.log(max(1.01, (home_goals.sum() + 1) / (away_goals.sum() + 1)))

        # Adam
        m_a = np.zeros(size); v_a = np.zeros(size)
        m_d = np.zeros(size); v_d = np.zeros(size)
        m_mu = np.zeros(len(leagues)); v_mu = np.zeros(len(leagues))
        m_h = 0.0; v_h = 0.0
        beta1, beta2, epsilon = 0.9, 0.999, 1e-8
        learning_rate = self.config.learning_rate
        regularization = self.config.regularization

        for epoch in range(1, self.config.epochs + 1):
            lambda_home = np.exp(
                np.clip(mu[league_matches] + home_advantage + attack[home] - defense[away], -3.0, 2.5)
            )
            lambda_away = np.exp(
                np.clip(mu[league_matches] + attack[away] - defense[home], -3.0, 2.5)
            )
            error_home = weights * (home_goals - lambda_home)
            error_away = weights * (away_goals - lambda_away)

            grad_attack = (
                np.bincount(home, weights=error_home, minlength=size)
                + np.bincount(away, weights=error_away, minlength=size)
                - regularization * attack
            )
            grad_defense = (
                -np.bincount(away, weights=error_home, minlength=size)
                - np.bincount(home, weights=error_away, minlength=size)
                - regularization * defense
            )
            grad_home = float(np.sum(error_home + error_away))
            grad_mu = np.bincount(
                league_matches,
                weights=error_home + error_away,
                minlength=len(leagues),
            ) - regularization * 0.15 * mu

            m_a = beta1 * m_a + (1 - beta1) * grad_attack
            v_a = beta2 * v_a + (1 - beta2) * grad_attack**2
            m_d = beta1 * m_d + (1 - beta1) * grad_defense
            v_d = beta2 * v_d + (1 - beta2) * grad_defense**2
            m_mu = beta1 * m_mu + (1 - beta1) * grad_mu
            v_mu = beta2 * v_mu + (1 - beta2) * grad_mu**2
            m_h = beta1 * m_h + (1 - beta1) * grad_home
            v_h = beta2 * v_h + (1 - beta2) * grad_home**2

            correction1 = 1 - beta1**epoch
            correction2 = 1 - beta2**epoch
            attack += learning_rate * (m_a / correction1) / (np.sqrt(v_a / correction2) + epsilon)
            defense += learning_rate * (m_d / correction1) / (np.sqrt(v_d / correction2) + epsilon)
            mu += learning_rate * 0.5 * (m_mu / correction1) / (np.sqrt(v_mu / correction2) + epsilon)
            home_advantage += learning_rate * 0.5 * (m_h / correction1) / (
                math.sqrt(v_h / correction2) + epsilon
            )

            # Identificabilidad: media ponderada por partidos a cero.
            team_weights = np.array(
                [self.team_matches[team] for team in teams], dtype=np.float64
            )
            total_weight = team_weights.sum() or 1.0
            attack -= float((attack * team_weights).sum() / total_weight)
            defense -= float((defense * team_weights).sum() / total_weight)

        home_advantage = _clip(home_advantage, 0.02, 0.55)
        mu_dict = {league: float(mu[index]) for league, index in league_index.items()}
        return attack, defense, mu_dict, home_advantage

    def _fit_elo(self) -> dict[str, float]:
        cutoff = self.reference_date - dt.timedelta(days=self.config.elo_max_age_days)
        elo: dict[str, float] = {}
        for team in self.teams:
            league = self.team_league.get(team, "")
            base = 1550.0 if league in {"SP1", "E0", "D1", "I1", "F1"} else 1470.0
            if league in {"SP2", "N1", "P1"}:
                base = 1450.0
            if self.team_matches[team] < 5:
                base -= 20.0
            elo[team] = base

        ordered = sorted(
            (match for match in self.matches if match.date >= cutoff),
            key=lambda match: match.date,
        )
        for match in ordered:
            home = match.home_team
            away = match.away_team
            home_rating = elo.get(home, 1450.0)
            away_rating = elo.get(away, 1450.0)
            expected = 1.0 / (1.0 + 10 ** (-(home_rating + self.config.elo_home_advantage - away_rating) / 400.0))
            actual = 1.0 if match.home_goals > match.away_goals else 0.5 if match.home_goals == match.away_goals else 0.0
            difference = abs(match.home_goals - match.away_goals)
            multiplier = 1.0 if difference <= 1 else 1.5 if difference == 2 else (11 + difference) / 8
            change = self.config.elo_k * multiplier * (actual - expected)
            elo[home] = home_rating + change
            elo[away] = away_rating - change
        return elo

    def _build_team_ratings(self) -> dict[str, TeamRating]:
        ratings: dict[str, TeamRating] = {}
        for index, team in enumerate(self.teams):
            matches = self.team_matches[team]
            ratings[team] = TeamRating(
                team=team,
                league=self.team_league.get(team, ""),
                league_name=self.team_league_name.get(team, ""),
                tier=self.team_tier.get(team, 1),
                matches=matches,
                attack=float(self.attack[index]) if index < len(self.attack) else 0.0,
                defense=float(self.defense[index]) if index < len(self.defense) else 0.0,
                elo=self.elo.get(team, 1450.0),
                goals_for=self.team_goals_for[team] / max(1, matches),
                goals_against=self.team_goals_against[team] / max(1, matches),
                last_match=self.team_last_match.get(team),
                form=list(self.team_form.get(team, [])),
            )
        return ratings

    # ------------------------------------------------------------------
    # Predicción
    # ------------------------------------------------------------------
    def _league_for(self, team: str, known: bool, competition: str, other_league: Optional[str]) -> tuple[str, float, bool]:
        """Devuelve (liga, offset, es_dato_real)."""
        if known and team in self.team_league:
            league = self.team_league[team]
            return league, LEAGUE_OFFSETS.get(league, 0.0), True
        lower_competition = any(
            token in competition.lower() for token in ("copa", "rey", "eliminatoria")
        )
        european_competition = any(
            token in competition.lower()
            for token in ("europe", "champions", "europa league", "conference")
        )
        if lower_competition:
            return "LOWER", LEAGUE_OFFSETS["LOWER"], False
        if european_competition:
            return "EUROPE", LEAGUE_OFFSETS["EUROPE"], False
        if other_league in {"SP1", "SP2"}:
            # Un rival sin datos frente a un club español suele ser de Copa.
            return "LOWER", LEAGUE_OFFSETS["LOWER"], False
        if other_league in {"E0", "D1", "I1", "F1", "N1", "P1"}:
            return "EUROPE", LEAGUE_OFFSETS["EUROPE"], False
        return "LOWER", LEAGUE_OFFSETS["LOWER"], False

    def predict_match(
        self,
        home_raw: str,
        away_raw: str,
        competition: str = "La Quiniela",
        match_number: int = 1,
        kickoff: str = "",
        is_pleno: bool = False,
        neutral: bool = False,
    ) -> MatchPrediction:
        women = is_women_team(home_raw) or is_women_team(away_raw)
        home, home_known = self.resolver.resolve(home_raw)
        away, away_known = self.resolver.resolve(away_raw)

        home_rating = self.team_ratings.get(home)
        away_rating = self.team_ratings.get(away)
        home_league, home_offset, home_real = self._league_for(
            home, home_known, competition, away_rating.league if away_rating else None
        )
        away_league, away_offset, away_real = self._league_for(
            away, away_known, competition, home_rating.league if home_rating else None
        )

        if women:
            home_league = away_league = "LIGA_F"
            home_offset = away_offset = LEAGUE_OFFSETS["LIGA_F"]
            home_known = away_known = False
            home_rating = away_rating = None

        league = home_league if home_league == away_league else (
            home_league if home_known else away_league
        )
        mu = self.league_mu.get(league, self.league_mu.get("SP1", math.log(1.35)))
        if women:
            mu = math.log(1.32)

        attack_home = home_rating.attack if home_rating and home_real else 0.0
        defense_home = home_rating.defense if home_rating and home_real else 0.0
        attack_away = away_rating.attack if away_rating and away_real else 0.0
        defense_away = away_rating.defense if away_rating and away_real else 0.0

        home_advantage = 0.0 if neutral else self.home_advantage
        if women:
            home_advantage = 0.12

        # ``delta`` es la diferencia de nivel entre las ligas de ambos equipos.
        # Se suma al local y se resta al visitante: un equipo de una división
        # inferior pierde gol esperado y su rival gana el mismo.
        delta = home_offset - away_offset
        lambda_home = math.exp(
            _clip(mu + home_advantage + attack_home - defense_away + delta, -3.0, 2.5)
        )
        lambda_away = math.exp(
            _clip(mu + attack_away - defense_home - delta, -3.0, 2.5)
        )
        lambda_home = _clip(lambda_home, 0.05, 5.5)
        lambda_away = _clip(lambda_away, 0.05, 5.5)

        matrix_poisson = _score_matrix(
            lambda_home,
            lambda_away,
            rho=self.config.draw_rho,
            max_goals=self.config.max_goals,
        )

        # Elo: se traduce a goles esperados y a una segunda matriz de marcadores.
        # Un equipo sin histórico no recibe un Elo neutro: se le asigna el nivel
        # de su competición para no convertir a un club modesto en favorito.
        home_elo = (
            home_rating.elo if home_rating and home_real else 1450.0 + 300.0 * home_offset
        )
        away_elo = (
            away_rating.elo if away_rating and away_real else 1450.0 + 300.0 * away_offset
        )
        if women:
            home_elo = away_elo = 1450.0
        elo_diff = home_elo - away_elo + (0.0 if neutral else self.config.elo_home_advantage)
        base_home = math.exp(mu + self.home_advantage)
        base_away = math.exp(mu)
        elo_lambda_home = _clip(base_home * math.exp(0.55 * elo_diff / 400.0), 0.05, 5.5)
        elo_lambda_away = _clip(base_away * math.exp(-0.55 * elo_diff / 400.0), 0.05, 5.5)
        matrix_elo = _score_matrix(
            elo_lambda_home,
            elo_lambda_away,
            rho=self.config.draw_rho,
            max_goals=self.config.max_goals,
        )

        data_home = min(1.0, self.team_matches.get(home, 0) / 40.0) if home_real else 0.0
        data_away = min(1.0, self.team_matches.get(away, 0) / 40.0) if away_real else 0.0
        # Si solo un equipo tiene histórico, su información sigue siendo útil
        # (caso habitual en Copa: un club modesto recibe a un Primera). No se
        # promedia a cero por el equipo desconocido.
        if home_real and away_real:
            data = min(data_home, data_away)
        elif home_real:
            data = 0.55 * data_home
        elif away_real:
            data = 0.55 * data_away
        else:
            data = 0.0
        poisson_weight = 0.35 + 0.45 * data
        matrix = poisson_weight * matrix_poisson + (1 - poisson_weight) * matrix_elo

        probabilities = _matrix_to_probabilities(matrix)
        base = self.league_base.get(league, self.global_base)
        if women:
            base = {"1": 0.45, "X": 0.25, "2": 0.30}
        shrink = 0.30 - 0.18 * data
        probabilities = {
            sign: (1 - shrink) * probabilities[sign] + shrink * base[sign]
            for sign in SIGNS
        }
        total = sum(probabilities.values())
        probabilities = {sign: value / total for sign, value in probabilities.items()}

        expected_home = float(sum(i * matrix[i].sum() for i in range(matrix.shape[0])))
        expected_away = float(sum(j * matrix[:, j].sum() for j in range(matrix.shape[1])))
        if women:
            expected_home = float(np.dot(np.arange(matrix.shape[0]), matrix.sum(axis=1)))
            expected_away = float(np.dot(np.arange(matrix.shape[1]), matrix.sum(axis=0)))

        flat_index = int(np.argmax(matrix))
        best_home, best_away = np.unravel_index(flat_index, matrix.shape)
        score_probability = float(matrix[best_home, best_away])
        score_options = _top_scores(matrix, 5)

        confidence = 0.18 + 0.52 * data
        if home_real and away_real:
            confidence += 0.12
        if women:
            confidence = 0.22
        if not home_real or not away_real:
            confidence -= 0.08
        confidence = _clip(confidence, 0.08, 0.94)
        data_quality = (
            "alta" if confidence >= 0.70 else "media" if confidence >= 0.45 else "baja" if confidence >= 0.25 else "sin datos"
        )

        notes: list[str] = []
        if women:
            notes.append(
                "Partido de Liga F: no hay histórico masculino comparable; se usa un prior de liga con confianza baja."
            )
        if not home_real or not away_real:
            missing = [raw for raw, real in ((home_raw, home_real), (away_raw, away_real)) if not real]
            notes.append(
                "Sin histórico suficiente para: " + ", ".join(missing) + ". Se aplica el nivel de su competición."
            )
        if home_rating and away_rating and home_rating.league != away_rating.league:
            notes.append("Partido entre equipos de ligas distintas: la comparación usa un ajuste de nivel.")

        h2h = self._head_to_head(home, away)
        home_payload = self._team_payload(home_rating, home_raw, home_real)
        away_payload = self._team_payload(away_rating, away_raw, away_real)

        return MatchPrediction(
            match_number=match_number,
            home_team=home,
            away_team=away,
            home_raw=home_raw,
            away_raw=away_raw,
            competition=competition,
            kickoff=kickoff,
            is_pleno=is_pleno,
            probabilities=probabilities,
            fair_odds={sign: 1 / max(1e-6, value) for sign, value in probabilities.items()},
            expected_goals={"home": expected_home, "away": expected_away},
            most_likely_score=_score_label(int(best_home), int(best_away)),
            score_probability=score_probability,
            score_options=score_options,
            confidence=confidence,
            data_quality=data_quality,
            home=home_payload,
            away=away_payload,
            h2h=h2h,
            notes=notes,
            is_women=women,
        )

    def _team_payload(
        self, rating: Optional[TeamRating], raw: str, real: bool
    ) -> dict[str, object]:
        if rating is None or not real:
            return {
                "name": raw,
                "known": False,
                "matches": 0,
                "elo": None,
                "attack": None,
                "defense": None,
                "goals_for": None,
                "goals_against": None,
                "form": [],
                "last_match": None,
            }
        return {
            "name": rating.team,
            "known": True,
            "league": rating.league,
            "league_name": rating.league_name,
            "matches": rating.matches,
            "elo": round(rating.elo, 1),
            "attack": round(rating.attack, 4),
            "defense": round(rating.defense, 4),
            "goals_for": round(rating.goals_for, 3),
            "goals_against": round(rating.goals_against, 3),
            "form": rating.form,
            "last_match": rating.last_match.isoformat() if rating.last_match else None,
        }

    def _head_to_head(self, home: str, away: str, limit: int = 10) -> dict[str, object]:
        if not home or not away:
            return {"matches": 0, "home_wins": 0, "draws": 0, "away_wins": 0, "results": []}
        confrontations = [
            match
            for match in self.matches
            if {match.home_team, match.away_team} == {home, away}
        ]
        confrontations.sort(key=lambda match: match.date, reverse=True)
        recent = confrontations[:limit]
        home_wins = draws = away_wins = 0
        results = []
        for match in recent:
            home_is_home = match.home_team == home
            goals_home = match.home_goals if home_is_home else match.away_goals
            goals_away = match.away_goals if home_is_home else match.home_goals
            if goals_home > goals_away:
                home_wins += 1
            elif goals_home < goals_away:
                away_wins += 1
            else:
                draws += 1
            results.append(
                {
                    "date": match.date.isoformat(),
                    "score": f"{goals_home}-{goals_away}",
                    "home": match.home_team,
                    "away": match.away_team,
                }
            )
        return {
            "matches": len(recent),
            "home_wins": home_wins,
            "draws": draws,
            "away_wins": away_wins,
            "results": results,
        }

    # ------------------------------------------------------------------
    # Vistas agregadas
    # ------------------------------------------------------------------
    def predict_jornada(self, jornada) -> list[MatchPrediction]:
        predictions: list[MatchPrediction] = []
        for fixture in jornada.fixtures:
            kickoff = " ".join(
                part for part in (fixture.kickoff_day, fixture.kickoff_time) if part
            )
            predictions.append(
                self.predict_match(
                    fixture.home_team,
                    fixture.away_team,
                    competition=fixture.competition,
                    match_number=fixture.match_number,
                    kickoff=kickoff,
                    is_pleno=fixture.is_pleno,
                )
            )
        return predictions

    def team_profile(self, name: str, limit: int = 10) -> Optional[dict[str, object]]:
        team, known = self.resolver.resolve(name)
        rating = self.team_ratings.get(team)
        if not known or rating is None:
            return None
        recent = [
            match
            for match in self.matches
            if match.home_team == team or match.away_team == team
        ]
        recent.sort(key=lambda match: match.date, reverse=True)
        payload = self._team_payload(rating, name, True)
        payload["recent"] = [
            {
                "date": match.date.isoformat(),
                "home": match.home_team,
                "away": match.away_team,
                "score": f"{match.home_goals}-{match.away_goals}",
                "result": (
                    "G"
                    if (match.home_team == team and match.home_goals > match.away_goals)
                    or (match.away_team == team and match.away_goals > match.home_goals)
                    else "E"
                    if match.home_goals == match.away_goals
                    else "P"
                ),
            }
            for match in recent[:limit]
        ]
        return payload

    def top_teams(self, limit: int = 12) -> list[dict[str, object]]:
        ordered = sorted(
            self.team_ratings.values(),
            key=lambda rating: rating.elo,
            reverse=True,
        )
        return [
            {
                "team": rating.team,
                "league": rating.league,
                "league_name": rating.league_name,
                "elo": round(rating.elo, 1),
                "matches": rating.matches,
                "attack": round(rating.attack, 4),
                "defense": round(rating.defense, 4),
                "goals_for": round(rating.goals_for, 3),
                "goals_against": round(rating.goals_against, 3),
            }
            for rating in ordered[:limit]
        ]

    def league_stats(self) -> list[dict[str, object]]:
        stats: list[dict[str, object]] = []
        for league, count in sorted(self.league_counts.items(), key=lambda item: -item[1]):
            league_matches = [match for match in self.matches if match.league == league]
            if not league_matches:
                continue
            goals = sum(match.home_goals + match.away_goals for match in league_matches)
            home_wins = sum(1 for match in league_matches if match.result == "H")
            draws = sum(1 for match in league_matches if match.result == "D")
            away_wins = sum(1 for match in league_matches if match.result == "A")
            over25 = sum(1 for match in league_matches if match.home_goals + match.away_goals > 2.5)
            btts = sum(1 for match in league_matches if match.home_goals > 0 and match.away_goals > 0)
            stats.append(
                {
                    "league": league,
                    "name": LEAGUE_LABELS.get(league, league),
                    "matches": len(league_matches),
                    "average_goals": round(goals / len(league_matches), 3),
                    "home_win_pct": round(100 * home_wins / len(league_matches), 2),
                    "draw_pct": round(100 * draws / len(league_matches), 2),
                    "away_win_pct": round(100 * away_wins / len(league_matches), 2),
                    "over_2_5_pct": round(100 * over25 / len(league_matches), 2),
                    "btts_pct": round(100 * btts / len(league_matches), 2),
                }
            )
        return stats

    def dataset_summary(self) -> dict[str, object]:
        return {
            "total_matches": len(self.matches),
            "date_range": {
                "from": self.matches[0].date.isoformat() if self.matches else None,
                "to": self.matches[-1].date.isoformat() if self.matches else None,
            },
            "teams": len(self.teams),
            "leagues": len(self.league_counts),
            "reference_date": self.reference_date.isoformat(),
            "home_advantage": round(self.home_advantage, 4),
            "half_life_days": self.config.half_life_days,
        }


# ----------------------------------------------------------------------
# Backtesting
# ----------------------------------------------------------------------
def _log_loss(probabilities: Sequence[dict[str, float]], results: Sequence[str]) -> float:
    total = 0.0
    for probability, result in zip(probabilities, results):
        sign = {"H": "1", "D": "X", "A": "2"}[result]
        total -= math.log(max(1e-9, probability[sign]))
    return total / max(1, len(results))


def _brier(probabilities: Sequence[dict[str, float]], results: Sequence[str]) -> float:
    total = 0.0
    for probability, result in zip(probabilities, results):
        sign = {"H": "1", "D": "X", "A": "2"}[result]
        total += sum(
            (probability[key] - (1.0 if key == sign else 0.0)) ** 2 for key in SIGNS
        )
    return total / max(1, len(results))


def backtest_model(
    matches: Sequence[Match],
    config: Optional[QuinielaModelConfig] = None,
    cutoff: Optional[dt.date] = None,
    limit: int = 1_200,
) -> dict[str, object]:
    """Evalúa el modelo sobre partidos no usados en el ajuste."""
    config = config or QuinielaModelConfig()
    ordered = sorted(matches, key=lambda match: match.date)
    if not ordered:
        return {"matches": 0}
    if cutoff is None:
        index = max(1, int(len(ordered) * 0.82))
        cutoff = ordered[index].date
    train = [match for match in ordered if match.date < cutoff]
    test = [match for match in ordered if match.date >= cutoff][:limit]
    if not train or not test:
        return {"matches": 0}

    model = QuinielaModel(train, config=config, reference_date=cutoff)
    probabilities: list[dict[str, float]] = []
    results: list[str] = []
    correct = 0
    baseline_correct = 0
    baseline_probabilities: list[dict[str, float]] = []
    for match in test:
        prediction = model.predict_match(
            match.home_team,
            match.away_team,
            competition=match.league_name,
        )
        probabilities.append(prediction.probabilities)
        results.append(match.result)
        if max(prediction.probabilities, key=prediction.probabilities.get) == {
            "H": "1",
            "D": "X",
            "A": "2",
        }[match.result]:
            correct += 1
        base = model.global_base
        baseline_probabilities.append(base)
        if max(base, key=base.get) == {"H": "1", "D": "X", "A": "2"}[match.result]:
            baseline_correct += 1

    # Calibración por tramos de confianza.
    buckets = {0.4: [0, 0, 0.0], 0.5: [0, 0, 0.0], 0.6: [0, 0, 0.0], 0.7: [0, 0, 0.0], 0.8: [0, 0, 0.0], 0.9: [0, 0, 0.0]}
    for probability, result in zip(probabilities, results):
        best_sign = max(probability, key=probability.get)
        confidence = probability[best_sign]
        bucket = max(key for key in buckets if key <= confidence) if confidence >= 0.4 else 0.4
        buckets[bucket][0] += 1
        if best_sign == {"H": "1", "D": "X", "A": "2"}[result]:
            buckets[bucket][1] += 1
        buckets[bucket][2] += confidence

    calibration = [
        {
            "min_confidence": key,
            "matches": count,
            "accuracy": round(hits / count, 4) if count else None,
            "average_confidence": round(total_confidence / count, 4) if count else None,
        }
        for key, (count, hits, total_confidence) in sorted(buckets.items())
    ]

    return {
        "matches": len(test),
        "train_matches": len(train),
        "cutoff": cutoff.isoformat(),
        "accuracy": round(correct / len(test), 4),
        "baseline_accuracy": round(baseline_correct / len(test), 4),
        "log_loss": round(_log_loss(probabilities, results), 4),
        "baseline_log_loss": round(_log_loss(baseline_probabilities, results), 4),
        "brier_score": round(_brier(probabilities, results), 4),
        "calibration": calibration,
    }


# ----------------------------------------------------------------------
# Cache
# ----------------------------------------------------------------------
_model_cache: Optional[QuinielaModel] = None
_model_cache_key: Optional[tuple] = None
_model_cache_lock = threading.Lock()


def clear_quiniela_model_cache() -> None:
    """Invalida el modelo cacheado (por ejemplo, tras actualizar resultados)."""
    global _model_cache, _model_cache_key
    with _model_cache_lock:
        _model_cache = None
        _model_cache_key = None


def get_quiniela_model(
    matches: Optional[Sequence[Match]] = None,
    config: Optional[QuinielaModelConfig] = None,
) -> QuinielaModel:
    """Devuelve el modelo cacheado para el histórico actual."""
    global _model_cache, _model_cache_key
    config = config or QuinielaModelConfig()
    if matches is None:
        matches = get_quiniela_data_manager().load_matches()
    matches = list(matches)
    if not matches:
        raise ValueError("No hay datos históricos de La Quiniela disponibles")

    # El config es frozen y hashable: incluirlo entero evita reutilizar un
    # modelo ajustado con otros hiperparámetros (rho, Elo, max_goals...).
    key = (len(matches), matches[-1].date, config)
    if _model_cache is not None and _model_cache_key == key:
        return _model_cache
    with _model_cache_lock:
        if _model_cache is not None and _model_cache_key == key:
            return _model_cache
        logger.info("Ajustando modelo de La Quiniela (Poisson + Elo)...")
        _model_cache = QuinielaModel(matches, config=config)
        _model_cache_key = key
        return _model_cache
