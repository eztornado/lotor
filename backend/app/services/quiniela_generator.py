"""
Generador y optimizador de boletos de La Quiniela.

La Quiniela no es una lotería uniforme: cada partido tiene una probabilidad
estimada de terminar en 1, X o 2. Eso permite dos cosas que en Bonoloto no
tienen sentido:

1. Construir una columna con los signos más probables.
2. Construir un **múltiple** (dobles y triples) que cubra varios resultados
   y repartir el presupuesto entre los partidos donde la incertidumbre es
   mayor.

El cálculo de aciertos de un boleto múltiple es exacto: si en el partido *i*
se marcan los signos ``S_i``, el boleto acierta ese partido cuando el
resultado real pertenece a ``S_i``. La probabilidad de acertar cada partido
es ``c_i = suma(P(resultado) para resultado en S_i)`` y, bajo el modelo, los
partidos son independientes. Por tanto el número de aciertos sigue una
distribución Poisson-binomial que se calcula con programación dinámica, sin
simulación.

Para carteras de varias columnas simples se usa Monte Carlo: las columnas
comparten los mismos resultados reales, así que sus aciertos no son
independientes y la distribución del *mejor* boleto no se puede obtener
multiplicando probabilidades.

Ningún modelo puede garantizar un premio. La Quiniela es un juego de azar y
los premios son de reparto (pari-mutuel): dependen del número de acertantes.
"""

from __future__ import annotations

import datetime as dt
import math
from dataclasses import dataclass, field
from itertools import product
from typing import Iterable, Optional, Sequence

import numpy as np
from loguru import logger

from app.services.quiniela_data import (
    MATCHES_PER_TICKET,
    SIGNS,
    TICKET_PRICE_EUR,
    Jornada,
    get_quiniela_data_manager,
)
from app.services.quiniela_model import (
    MatchPrediction,
    QuinielaModel,
    get_quiniela_model,
)

MAX_DOUBLES = 7
MAX_TRIPLES = 4
DEFAULT_BUDGET_EUR = 20.0
# Tope técnico de columnas para un múltiple. El presupuesto real manda: este
# límite solo evita configuraciones desproporcionadas si se usa la API interna.
MAX_TICKET_COLUMNS = 2_048

GAME_INFO = {
    "name": "La Quiniela",
    "matches": 15,
    "sign_matches": MATCHES_PER_TICKET,
    "pleno_match": 15,
    "ticket_price_eur": TICKET_PRICE_EUR,
    "max_doubles": MAX_DOUBLES,
    "max_triples": MAX_TRIPLES,
    "prize_categories": {
        "15": "Pleno al 15 (1ª categoría)",
        "14": "2ª categoría (14 aciertos)",
        "13": "3ª categoría (13 aciertos)",
        "12": "4ª categoría (12 aciertos)",
        "11": "5ª categoría (11 aciertos)",
        "10": "6ª categoría (10 aciertos)",
    },
}

STRATEGIES = {
    "balanced": {
        "label": "Equilibrada",
        "description": (
            "Reparte el presupuesto entre los partidos más inciertos y "
            "maximiza la probabilidad de alcanzar categorías con premio."
        ),
        "category_weights": {10: 1.0, 11: 1.6, 12: 2.6, 13: 4.0, 14: 7.0, 15: 11.0},
        "expected_weight": 0.12,
    },
    "coverage": {
        "label": "Máxima cobertura",
        "description": (
            "Prioriza cubrir resultados y llegar a 10-11 aciertos. Es la "
            "opción más conservadora para un presupuesto ajustado."
        ),
        "category_weights": {10: 2.0, 11: 2.4, 12: 2.8, 13: 3.2, 14: 4.0, 15: 5.0},
        "expected_weight": 0.05,
    },
    "max_probability": {
        "label": "Máxima probabilidad",
        "description": (
            "Elige los signos y dobles con mayor probabilidad individual. "
            "Menos cobertura, pero la columna más probable del modelo."
        ),
        "category_weights": {10: 0.8, 11: 1.0, 12: 1.4, 13: 2.0, 14: 3.0, 15: 4.0},
        "expected_weight": 1.0,
    },
    "jackpot": {
        "label": "Caza del pleno",
        "description": (
            "Concentra el presupuesto en las categorías altas (13-15). "
            "Más riesgo: la probabilidad de premio pequeño baja."
        ),
        "category_weights": {10: 0.2, 11: 0.4, 12: 1.0, 13: 3.0, 14: 9.0, 15: 25.0},
        "expected_weight": 0.02,
    },
}

# Estimaciones orientativas de premio medio por categoría. Los premios reales
# son de reparto y varían en cada jornada; se muestran rangos, no promesas.
PRIZE_ESTIMATES = {
    15: {"low": 50_000.0, "average": 200_000.0, "high": 1_000_000.0},
    14: {"low": 1_500.0, "average": 5_000.0, "high": 20_000.0},
    13: {"low": 150.0, "average": 400.0, "high": 1_200.0},
    12: {"low": 20.0, "average": 50.0, "high": 150.0},
    11: {"low": 3.0, "average": 6.0, "high": 15.0},
    10: {"low": 0.75, "average": 1.2, "high": 3.0},
}

# Número máximo de columnas que se expanden para mostrar el boleto completo.
MAX_EXPANDED_COLUMNS = 128


def _clip(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _strategy(name: str) -> dict:
    return STRATEGIES.get(name, STRATEGIES["balanced"])


# ----------------------------------------------------------------------
# Distribuciones
# ----------------------------------------------------------------------
def poisson_binomial(probabilities: Sequence[float]) -> list[float]:
    """Distribución exacta del número de aciertos de una columna múltiple."""
    distribution = [0.0] * (len(probabilities) + 1)
    distribution[0] = 1.0
    for probability in probabilities:
        probability = _clip(float(probability), 0.0, 1.0)
        for hits in range(len(distribution) - 1, 0, -1):
            distribution[hits] = (
                distribution[hits] * (1.0 - probability)
                + distribution[hits - 1] * probability
            )
        distribution[0] *= 1.0 - probability
    total = sum(distribution)
    if total > 0:
        distribution = [value / total for value in distribution]
    return distribution


def _add_pleno(
    hits_distribution: Sequence[float], pleno_probability: float
) -> list[float]:
    """Convierte la distribución de aciertos de los 14 partidos en 15 aciertos."""
    pleno_probability = _clip(pleno_probability, 0.0, 1.0)
    total = [0.0] * (len(hits_distribution) + 1)
    for hits, probability in enumerate(hits_distribution):
        total[hits] += probability * (1.0 - pleno_probability)
        total[hits + 1] += probability * pleno_probability
    return total


def _cumulative_from(distribution: Sequence[float], threshold: int) -> float:
    return sum(distribution[threshold:]) if threshold < len(distribution) else 0.0


# ----------------------------------------------------------------------
# Configuración y estructuras
# ----------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class QuinielaConfig:
    budget: float = DEFAULT_BUDGET_EUR
    max_doubles: int = 4
    max_triples: int = 2
    max_columns: int = 64
    simulations: int = 12_000
    candidates: int = 260
    local_search_passes: int = 2


@dataclass(slots=True)
class Ticket:
    signs: list[tuple[str, ...]]
    pleno_score: tuple[int, int]
    pleno_probability: float
    columns: int
    cost: float
    doubles: int
    triples: int
    expected_hits: float
    expected_total_hits: float
    guaranteed_hits: int
    hits_14_distribution: list[float]
    hit_distribution: list[float]
    category_probabilities: dict[str, float]
    prize_estimate: dict[str, object]
    coverage: list[float]
    probabilities: list[dict[str, float]] = field(default_factory=list)

    @property
    def pleno_label(self) -> str:
        return f"{self.pleno_score[0]}-{self.pleno_score[1]}"

    def as_dict(self, index: int = 1) -> dict[str, object]:
        return {
            "index": index,
            "signs": [
                {
                    "match_number": number,
                    "signs": list(sign_set),
                    "pick": (
                        _best_sign(sign_set, self.probabilities[number - 1])
                        if number - 1 < len(self.probabilities)
                        else sign_set[0]
                    ),
                    "coverage": round(self.coverage[number - 1], 6),
                }
                for number, sign_set in enumerate(self.signs, start=1)
            ],
            "pleno": {
                "score": self.pleno_label,
                "probability": round(self.pleno_probability, 6),
            },
            "columns": self.columns,
            "cost": round(self.cost, 2),
            "doubles": self.doubles,
            "triples": self.triples,
            "expected_hits": round(self.expected_hits, 3),
            "expected_total_hits": round(self.expected_total_hits, 3),
            "guaranteed_hits": self.guaranteed_hits,
            "hits_14_distribution": [round(value, 6) for value in self.hits_14_distribution],
            "hit_distribution": [round(value, 6) for value in self.hit_distribution],
            "category_probabilities": {
                category: round(value, 6)
                for category, value in self.category_probabilities.items()
            },
            "prize_estimate": self.prize_estimate,
            "coverage": [round(value, 6) for value in self.coverage],
        }


def _best_sign(sign_set: Sequence[str], probabilities: dict[str, float]) -> str:
    return max(sign_set, key=lambda sign: probabilities.get(sign, 0.0))


@dataclass(slots=True)
class PredictionBundle:
    jornada: Jornada
    predictions: list[MatchPrediction]
    pleno: MatchPrediction
    sign_probabilities: list[dict[str, float]]
    pleno_score: tuple[int, int]
    pleno_probability: float


# ----------------------------------------------------------------------
# Utilidades del boleto
# ----------------------------------------------------------------------
def _sign_sets_from_column(column: Sequence[str]) -> list[tuple[str, ...]]:
    return [(sign,) for sign in column]


def _columns_for(signs: Sequence[Sequence[str]]) -> int:
    columns = 1
    for sign_set in signs:
        columns *= max(1, len(sign_set))
    return columns


def _doubles_and_triples(signs: Sequence[Sequence[str]]) -> tuple[int, int]:
    doubles = sum(1 for sign_set in signs if len(sign_set) == 2)
    triples = sum(1 for sign_set in signs if len(sign_set) >= 3)
    return doubles, triples


def _expand(signs: Sequence[Sequence[str]], limit: int = MAX_EXPANDED_COLUMNS) -> Optional[list[tuple[str, ...]]]:
    if _columns_for(signs) > limit:
        return None
    return [tuple(combination) for combination in product(*signs)]


def _category_probabilities(
    hit_distribution: Sequence[float],
) -> dict[str, float]:
    """Probabilidad exacta de cada categoría con premio (10 a 15 aciertos)."""
    return {
        str(hits): hit_distribution[hits] if hits < len(hit_distribution) else 0.0
        for hits in range(10, 16)
    }


def _prize_estimate(category_probabilities: dict[str, float], cost: float) -> dict[str, object]:
    low_return = sum(
        category_probabilities[key] * PRIZE_ESTIMATES[int(key)]["low"]
        for key in category_probabilities
    )
    average_return = sum(
        category_probabilities[key] * PRIZE_ESTIMATES[int(key)]["average"]
        for key in category_probabilities
    )
    high_return = sum(
        category_probabilities[key] * PRIZE_ESTIMATES[int(key)]["high"]
        for key in category_probabilities
    )
    prize_probability = sum(category_probabilities.values())
    return {
        "probability_any_prize": round(prize_probability, 6),
        "expected_return": {
            "low": round(low_return, 2),
            "average": round(average_return, 2),
            "high": round(high_return, 2),
        },
        "cost": round(cost, 2),
        "roi": {
            "low": round(low_return / cost - 1, 4) if cost else 0.0,
            "average": round(average_return / cost - 1, 4) if cost else 0.0,
            "high": round(high_return / cost - 1, 4) if cost else 0.0,
        },
        "by_category": {
            category: {
                "probability": round(probability, 6),
                "average_prize": PRIZE_ESTIMATES[int(category)]["average"],
            }
            for category, probability in category_probabilities.items()
        },
        "note": (
            "Estimación conservadora con premios medios orientativos: cuenta "
            "solo el mejor boleto de la cartera. Un múltiple puede cobrar varias "
            "categorías a la vez, pero los premios son de reparto y dependen de "
            "los acertantes de cada jornada."
        ),
    }


def build_ticket(
    signs: Sequence[Sequence[str]],
    probabilities: Sequence[dict[str, float]],
    pleno_score: tuple[int, int],
    pleno_probability: float,
    strategy: str = "balanced",
) -> Ticket:
    """Construye un boleto y calcula sus métricas exactas."""
    sign_sets = [tuple(sign_set) for sign_set in signs]
    coverage = [
        sum(probabilities[index].get(sign, 0.0) for sign in sign_set)
        for index, sign_set in enumerate(sign_sets)
    ]
    columns = _columns_for(sign_sets)
    doubles, triples = _doubles_and_triples(sign_sets)
    expected_hits = sum(coverage)
    hits_14_distribution = poisson_binomial(coverage)
    hit_distribution = _add_pleno(hits_14_distribution, pleno_probability)
    categories = _category_probabilities(hit_distribution)
    ticket = Ticket(
        signs=sign_sets,
        pleno_score=pleno_score,
        pleno_probability=pleno_probability,
        columns=columns,
        cost=columns * TICKET_PRICE_EUR,
        doubles=doubles,
        triples=triples,
        expected_hits=expected_hits,
        expected_total_hits=sum(index * value for index, value in enumerate(hit_distribution)),
        guaranteed_hits=triples,
        hits_14_distribution=hits_14_distribution,
        hit_distribution=hit_distribution,
        category_probabilities=categories,
        prize_estimate=_prize_estimate(categories, columns * TICKET_PRICE_EUR),
        coverage=coverage,
        probabilities=list(probabilities),
    )
    return ticket


def _utility(ticket: Ticket, strategy: str) -> float:
    weights = _strategy(strategy)["category_weights"]
    value = sum(
        weights.get(int(category), 0.0) * ticket.category_probabilities[category]
        for category in ticket.category_probabilities
    )
    value += _strategy(strategy)["expected_weight"] * (ticket.expected_total_hits / 15.0)
    return value


# ----------------------------------------------------------------------
# Optimización de un múltiple
# ----------------------------------------------------------------------
def _fits(
    signs: Sequence[Sequence[str]],
    config: QuinielaConfig,
    budget: float,
) -> bool:
    columns = _columns_for(signs)
    doubles, triples = _doubles_and_triples(signs)
    return (
        columns <= config.max_columns
        and columns * TICKET_PRICE_EUR <= budget + 1e-9
        and doubles <= config.max_doubles
        and triples <= config.max_triples
    )


def _greedy_multiple(
    base: Sequence[str],
    probabilities: Sequence[dict[str, float]],
    pleno_score: tuple[int, int],
    pleno_probability: float,
    config: QuinielaConfig,
    strategy: str,
    budget: float,
) -> Ticket:
    signs: list[tuple[str, ...]] = [(sign,) for sign in base]
    current = build_ticket(signs, probabilities, pleno_score, pleno_probability, strategy)
    current_value = _utility(current, strategy)

    while True:
        best_ticket: Optional[Ticket] = None
        best_value = current_value + 1e-12

        for index in range(MATCHES_PER_TICKET):
            if len(signs[index]) >= 3:
                continue
            for sign in SIGNS:
                if sign in signs[index]:
                    continue
                trial = list(signs)
                trial[index] = tuple(sorted((*trial[index], sign), key=SIGNS.index))
                if not _fits(trial, config, budget):
                    continue
                ticket = build_ticket(
                    trial, probabilities, pleno_score, pleno_probability, strategy
                )
                value = _utility(ticket, strategy)
                if value > best_value:
                    best_value = value
                    best_ticket = ticket

        if best_ticket is None:
            break
        current = best_ticket
        current_value = best_value
        signs = list(best_ticket.signs)

    return current


def _local_search_multiple(
    ticket: Ticket,
    probabilities: Sequence[dict[str, float]],
    pleno_score: tuple[int, int],
    pleno_probability: float,
    config: QuinielaConfig,
    strategy: str,
    budget: float,
) -> Ticket:
    """Intercambia un signo de un partido por otro de otro partido."""
    best = ticket
    best_value = _utility(best, strategy)

    for _ in range(config.local_search_passes):
        improved = False
        for remove_index in range(MATCHES_PER_TICKET):
            if len(best.signs[remove_index]) <= 1:
                continue
            for remove_sign in best.signs[remove_index]:
                for add_index in range(MATCHES_PER_TICKET):
                    if add_index == remove_index:
                        continue
                    for add_sign in SIGNS:
                        if add_sign in best.signs[add_index]:
                            continue
                        trial = list(best.signs)
                        remaining = tuple(
                            sign for sign in trial[remove_index] if sign != remove_sign
                        )
                        if not remaining:
                            continue
                        trial[remove_index] = remaining
                        trial[add_index] = tuple(
                            sorted((*trial[add_index], add_sign), key=SIGNS.index)
                        )
                        if not _fits(trial, config, budget):
                            continue
                        candidate = build_ticket(
                            trial,
                            probabilities,
                            pleno_score,
                            pleno_probability,
                            strategy,
                        )
                        value = _utility(candidate, strategy)
                        if value > best_value + 1e-12:
                            best = candidate
                            best_value = value
                            improved = True
        if not improved:
            break
    return best


def optimize_multiple(
    predictions: Sequence[MatchPrediction],
    pleno: MatchPrediction,
    config: QuinielaConfig,
    strategy: str = "balanced",
) -> Ticket:
    """Optimiza un único boleto múltiple con dobles y triples."""
    probabilities = [prediction.probabilities for prediction in predictions[:MATCHES_PER_TICKET]]
    pleno_score = _pleno_score(pleno)
    pleno_probability = _pleno_probability(pleno, pleno_score)
    budget = min(config.budget, config.max_columns * TICKET_PRICE_EUR)
    if budget < TICKET_PRICE_EUR:
        raise ValueError("El presupuesto debe permitir al menos una columna (0,75 €)")

    # Varias semillas: la columna de máxima probabilidad, una variante con
    # empates y otra con los segundos signos. Nos quedamos con la mejor.
    bases: list[list[str]] = [
        [max(probability, key=probability.get) for probability in probabilities],
        [
            "X"
            if probability["X"] + 0.06 >= max(probability.values())
            else max(probability, key=probability.get)
            for probability in probabilities
        ],
    ]
    for index in range(MATCHES_PER_TICKET):
        alternative = list(bases[0])
        ordered = sorted(probabilities[index], key=probabilities[index].get, reverse=True)
        alternative[index] = ordered[1]
        bases.append(alternative)

    best: Optional[Ticket] = None
    best_value = -math.inf
    for base in bases:
        if not _fits(base, config, budget):
            continue
        candidate = _greedy_multiple(
            base, probabilities, pleno_score, pleno_probability, config, strategy, budget
        )
        candidate = _local_search_multiple(
            candidate,
            probabilities,
            pleno_score,
            pleno_probability,
            config,
            strategy,
            budget,
        )
        value = _utility(candidate, strategy)
        if value > best_value:
            best = candidate
            best_value = value

    if best is None:
        # Con presupuesto mínimo siempre cabe una columna simple.
        base = bases[0]
        best = build_ticket(
            _sign_sets_from_column(base),
            probabilities,
            pleno_score,
            pleno_probability,
            strategy,
        )
    return best


# ----------------------------------------------------------------------
# Cartera de columnas simples
# ----------------------------------------------------------------------
def _candidate_columns(
    probabilities: Sequence[dict[str, float]],
    count: int,
    rng: np.random.Generator,
) -> list[tuple[str, ...]]:
    """Genera columnas candidatas: deterministas, variantes y muestreo."""
    candidates: set[tuple[str, ...]] = set()

    def add(column: Iterable[str]) -> None:
        candidate = tuple(column)
        if len(candidate) == MATCHES_PER_TICKET:
            candidates.add(candidate)

    ordered = [
        sorted(probability, key=probability.get, reverse=True)
        for probability in probabilities
    ]
    add([signs[0] for signs in ordered])
    add([signs[1] for signs in ordered])
    add([signs[2] for signs in ordered])

    # Una variante por partido cambiando el signo más probable por el segundo.
    for index in range(MATCHES_PER_TICKET):
        column = [signs[0] for signs in ordered]
        column[index] = ordered[index][1]
        add(column)

    # Pares de cambios: cubre las combinaciones de dos partidos inciertos.
    for first in range(MATCHES_PER_TICKET):
        for second in range(first + 1, MATCHES_PER_TICKET):
            column = [signs[0] for signs in ordered]
            column[first] = ordered[first][1]
            column[second] = ordered[second][1]
            add(column)

    probabilities_array = np.array(
        [[probability[sign] for sign in SIGNS] for probability in probabilities],
        dtype=np.float64,
    )
    # Muestreo con tres temperaturas: exploración amplia, media y conservadora.
    for temperature in (1.0, 0.65, 0.35):
        adjusted = np.power(probabilities_array, 1.0 / temperature)
        adjusted /= adjusted.sum(axis=1, keepdims=True)
        for _ in range(count):
            column = []
            for index in range(MATCHES_PER_TICKET):
                chosen = rng.choice(len(SIGNS), p=adjusted[index])
                column.append(SIGNS[int(chosen)])
            add(column)

    # El orden de un set depende del hash aleatorio de las cadenas en cada
    # proceso; se ordena para que una misma semilla sea reproducible.
    return sorted(candidates)


def _simulate_outcomes(
    probabilities: Sequence[dict[str, float]],
    simulations: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Matriz (simulaciones x partidos) con el índice del signo resultante."""
    probabilities_array = np.array(
        [[probability[sign] for sign in SIGNS] for probability in probabilities],
        dtype=np.float64,
    )
    probabilities_array /= probabilities_array.sum(axis=1, keepdims=True)
    cumulative = np.cumsum(probabilities_array, axis=1)
    uniforms = rng.random((simulations, MATCHES_PER_TICKET))
    outcomes = (uniforms[:, :, None] > cumulative[None, :, :]).sum(axis=2)
    return np.clip(outcomes, 0, 2).astype(np.int8)


def _column_hits(outcomes: np.ndarray, column: Sequence[str]) -> np.ndarray:
    indices = np.array([SIGNS.index(sign) for sign in column], dtype=np.int8)
    return (outcomes == indices[None, :]).sum(axis=1).astype(np.int16)


def _portfolio_utility(
    best_hits: np.ndarray, strategy: str, simulations: int
) -> float:
    weights = _strategy(strategy)["category_weights"]
    value = 0.0
    for threshold, weight in weights.items():
        value += weight * float((best_hits >= threshold).sum()) / simulations
    value += _strategy(strategy)["expected_weight"] * float(best_hits.mean()) / 15.0
    return value


def optimize_portfolio(
    predictions: Sequence[MatchPrediction],
    pleno: MatchPrediction,
    count: int,
    config: QuinielaConfig,
    strategy: str = "balanced",
    seed: Optional[int] = None,
) -> list[Ticket]:
    """Selecciona ``count`` columnas simples maximizando el mejor boleto."""
    probabilities = [prediction.probabilities for prediction in predictions[:MATCHES_PER_TICKET]]
    pleno_score = _pleno_score(pleno)
    pleno_probability = _pleno_probability(pleno, pleno_score)

    seed = seed if seed is not None else 20261022
    rng = np.random.default_rng(seed)
    outcomes = _simulate_outcomes(probabilities, config.simulations, rng)
    candidates = _candidate_columns(probabilities, config.candidates, rng)
    if not candidates:
        candidates = [tuple(max(probability, key=probability.get) for probability in probabilities)]

    # Matriz de aciertos por candidato y simulación.
    hit_matrix = np.stack(
        [_column_hits(outcomes, column) for column in candidates], axis=0
    )
    own_expected = hit_matrix.mean(axis=1)

    selected: list[int] = []
    best_hits = np.full(config.simulations, -1, dtype=np.int16)
    available = set(range(len(candidates)))

    for _ in range(count):
        best_index: Optional[int] = None
        best_value = -math.inf
        for index in available:
            trial_best = np.maximum(best_hits, hit_matrix[index])
            value = _portfolio_utility(trial_best, strategy, config.simulations)
            # Desempate: calidad individual y diversidad frente a lo elegido.
            value += 1e-4 * float(own_expected[index])
            if selected:
                similarity = sum(
                    len(set(candidates[index]).intersection(candidates[other]))
                    for other in selected
                ) / (MATCHES_PER_TICKET * len(selected))
                value -= 1e-3 * similarity
            if value > best_value + 1e-12:
                best_value = value
                best_index = index
        if best_index is None:
            break
        selected.append(best_index)
        available.remove(best_index)
        best_hits = np.maximum(best_hits, hit_matrix[best_index])

    tickets: list[Ticket] = []
    for index in selected:
        ticket = build_ticket(
            _sign_sets_from_column(candidates[index]),
            probabilities,
            pleno_score,
            pleno_probability,
            strategy,
        )
        tickets.append(ticket)
    return tickets


# ----------------------------------------------------------------------
# Métricas agregadas
# ----------------------------------------------------------------------
def _portfolio_metrics(
    tickets: Sequence[Ticket],
    predictions: Sequence[MatchPrediction],
    simulations: int = 12_000,
    seed: int = 20261022,
) -> dict[str, object]:
    probabilities = [prediction.probabilities for prediction in predictions[:MATCHES_PER_TICKET]]
    rng = np.random.default_rng(seed)
    outcomes = _simulate_outcomes(probabilities, simulations, rng)
    best = np.full(simulations, -1, dtype=np.int16)
    for ticket in tickets:
        column = tuple(sign_set[0] for sign_set in ticket.signs)
        best = np.maximum(best, _column_hits(outcomes, column))
    best = np.maximum(best, 0)

    pleno_probability = tickets[0].pleno_probability if tickets else 0.0
    hits_14_distribution = [
        float((best == hits).sum()) / simulations for hits in range(MATCHES_PER_TICKET + 1)
    ]
    total_distribution = _add_pleno(hits_14_distribution, pleno_probability)
    categories = _category_probabilities(total_distribution)
    cost = sum(ticket.cost for ticket in tickets)
    prize = _prize_estimate(categories, cost) if cost else _prize_estimate(categories, 0.0)

    coverage = []
    for index in range(MATCHES_PER_TICKET):
        covered = {
            ticket.signs[index][0]
            for ticket in tickets
        }
        coverage.append(sorted(covered, key=SIGNS.index))

    return {
        "tickets": len(tickets),
        "columns": sum(ticket.columns for ticket in tickets),
        "cost": round(cost, 2),
        "expected_best_hits": round(float(best.mean()), 3),
        "expected_total_hits": round(
            sum(index * value for index, value in enumerate(total_distribution)), 3
        ),
        "guaranteed_hits": sum(ticket.guaranteed_hits for ticket in tickets),
        "hits_14_distribution": [round(value, 6) for value in hits_14_distribution],
        "hit_distribution": [round(value, 6) for value in total_distribution],
        "category_probabilities": {
            category: round(value, 6) for category, value in categories.items()
        },
        "prize_estimate": prize,
        "coverage": coverage,
        "method": "monte_carlo",
        "simulations": simulations,
    }


def _multiple_metrics(ticket: Ticket) -> dict[str, object]:
    return {
        "tickets": 1,
        "columns": ticket.columns,
        "cost": round(ticket.cost, 2),
        "expected_best_hits": round(ticket.expected_hits, 3),
        "expected_total_hits": round(ticket.expected_total_hits, 3),
        "guaranteed_hits": ticket.guaranteed_hits,
        "hits_14_distribution": [round(value, 6) for value in ticket.hits_14_distribution],
        "hit_distribution": [round(value, 6) for value in ticket.hit_distribution],
        "category_probabilities": {
            category: round(value, 6)
            for category, value in ticket.category_probabilities.items()
        },
        "prize_estimate": ticket.prize_estimate,
        "coverage": [
            list(ticket.signs[index]) for index in range(MATCHES_PER_TICKET)
        ],
        "method": "exact_poisson_binomial",
        "simulations": 0,
    }


# ----------------------------------------------------------------------
# Predicciones y pleno
# ----------------------------------------------------------------------
def _pleno_score(prediction: MatchPrediction) -> tuple[int, int]:
    home, away = prediction.most_likely_score.split("-")
    return int(home), int(away)


def _pleno_probability(prediction: MatchPrediction, score: tuple[int, int]) -> float:
    label = f"{score[0]}-{score[1]}"
    for option in prediction.score_options:
        if option["score"] == label:
            return float(option["probability"])
    return max(1e-6, prediction.score_probability)


def _bundle(jornada: Optional[int] = None, season: Optional[str] = None) -> PredictionBundle:
    manager = get_quiniela_data_manager()
    if jornada is None:
        selected = manager.next_jornada()
    else:
        selected = manager.find_jornada(jornada, season)
    if selected is None:
        raise ValueError(f"No hay datos para la jornada {jornada or 'solicitada'}")
    if not selected.is_complete:
        raise ValueError(
            f"La jornada {selected.jornada} está incompleta "
            f"({len(selected.fixtures)} de 15 partidos)"
        )

    model = get_quiniela_model()
    predictions = model.predict_jornada(selected)
    pleno = next(
        (prediction for prediction in predictions if prediction.is_pleno),
        predictions[-1],
    )
    sign_predictions = [prediction for prediction in predictions if not prediction.is_pleno]
    if len(sign_predictions) < MATCHES_PER_TICKET:
        sign_predictions = predictions[:MATCHES_PER_TICKET]
    pleno_score = _pleno_score(pleno)
    return PredictionBundle(
        jornada=selected,
        predictions=predictions,
        pleno=pleno,
        sign_probabilities=[prediction.probabilities for prediction in sign_predictions],
        pleno_score=pleno_score,
        pleno_probability=_pleno_probability(pleno, pleno_score),
    )


def _jornada_payload(jornada: Jornada) -> dict[str, object]:
    return {
        "season": jornada.season,
        "jornada": jornada.jornada,
        "label": jornada.label,
        "start_date": jornada.start_date.isoformat(),
        "matches": len(jornada.fixtures),
        "competition": jornada.competition,
        "competitions": jornada.competitions,
    }


def _match_payload(prediction: MatchPrediction) -> dict[str, object]:
    payload = prediction.as_dict()
    ordered = sorted(prediction.probabilities, key=prediction.probabilities.get, reverse=True)
    payload["pick"] = ordered[0]
    payload["edge"] = round(
        prediction.probabilities[ordered[0]] - prediction.probabilities[ordered[1]], 4
    )
    payload["entropy"] = round(
        -sum(
            value * math.log(max(value, 1e-12))
            for value in prediction.probabilities.values()
        ),
        4,
    )
    return payload


# ----------------------------------------------------------------------
# Recomendaciones
# ----------------------------------------------------------------------
def _recommendations(
    bundle: PredictionBundle,
    tickets: Sequence[Ticket],
    config: QuinielaConfig,
    mode: str,
) -> list[str]:
    recommendations: list[str] = []
    ordered = sorted(
        bundle.predictions,
        key=lambda prediction: max(prediction.probabilities.values()),
        reverse=True,
    )
    most_confident = ordered[:2]
    least_confident = [
        prediction
        for prediction in sorted(
            bundle.predictions,
            key=lambda prediction: max(prediction.probabilities.values()),
        )
        if not prediction.is_pleno
    ][:2]
    if most_confident:
        recommendations.append(
            "Partidos más claros: "
            + ", ".join(
                f"{prediction.home_raw}-{prediction.away_raw} "
                f"({max(prediction.probabilities, key=prediction.probabilities.get)})"
                for prediction in most_confident
            )
            + "."
        )
    if least_confident:
        recommendations.append(
            "Partidos más abiertos: "
            + ", ".join(
                f"{prediction.home_raw}-{prediction.away_raw}"
                for prediction in least_confident
            )
            + ". Ahí suele tener más valor un doble."
        )
    if mode == "multiple" and tickets:
        ticket = tickets[0]
        recommendations.append(
            f"El múltiple usa {ticket.doubles} dobles y {ticket.triples} triples: "
            f"{ticket.columns} columnas por {ticket.cost:.2f} €."
        )
        if ticket.guaranteed_hits:
            recommendations.append(
                f"Con {ticket.triples} triple(s) tienes {ticket.guaranteed_hits} "
                "acierto(s) garantizado(s) en esos partidos."
            )
    if config.budget < 3:
        recommendations.append(
            "Con menos de 3 € conviene jugar una sola columna simple; los "
            "dobles encarecen mucho el boleto."
        )
    recommendations.append(
        "El pleno al 15 se estima con el marcador más probable del modelo; "
        "es la parte más difícil del boleto."
    )
    recommendations.append(
        "Juega solo lo que puedas permitirte. Ningún modelo garantiza premios."
    )
    return recommendations


# ----------------------------------------------------------------------
# API interna
# ----------------------------------------------------------------------
def generate_quiniela(
    jornada: Optional[int] = None,
    season: Optional[str] = None,
    mode: str = "multiple",
    budget: float = DEFAULT_BUDGET_EUR,
    max_doubles: int = 4,
    max_triples: int = 2,
    count: int = 1,
    strategy: str = "balanced",
    seed: Optional[int] = None,
) -> dict[str, object]:
    """Genera un boleto múltiple o una cartera de columnas simples."""
    if mode not in {"multiple", "simple"}:
        raise ValueError("El modo debe ser 'multiple' o 'simple'")
    if strategy not in STRATEGIES:
        raise ValueError(
            f"Estrategia no válida: {strategy}. Opciones: {', '.join(STRATEGIES)}"
        )
    if budget < TICKET_PRICE_EUR:
        raise ValueError("El presupuesto mínimo es 0,75 € (una columna)")
    if not 1 <= count <= 10:
        raise ValueError("El número de columnas simples debe estar entre 1 y 10")
    if max_doubles < 0 or max_triples < 0:
        raise ValueError("Los dobles y triples no pueden ser negativos")
    if max_doubles > MAX_DOUBLES or max_triples > MAX_TRIPLES:
        raise ValueError(
            f"Máximo permitido: {MAX_DOUBLES} dobles y {MAX_TRIPLES} triples"
        )

    # Con un único boleto múltiple, cualquier objetivo creciente en el número
    # de aciertos conduce a la misma cobertura óptima. Las estrategias solo
    # diferencian la cartera de columnas simples.
    if mode == "multiple":
        strategy = "balanced"

    affordable_columns = max(1, int(budget // TICKET_PRICE_EUR))
    config = QuinielaConfig(
        budget=budget,
        max_doubles=max_doubles,
        max_triples=max_triples,
        # El presupuesto es el límite real; el tope técnico solo evita
        # configuraciones absurdas si se llama a la API interna.
        max_columns=min(MAX_TICKET_COLUMNS, affordable_columns),
    )
    bundle = _bundle(jornada, season)
    effective_seed = seed if seed is not None else int(dt.datetime.now().timestamp())

    if mode == "multiple":
        ticket = optimize_multiple(
            bundle.predictions, bundle.pleno, config, strategy
        )
        tickets = [ticket]
        portfolio = _multiple_metrics(ticket)
        expanded = _expand(ticket.signs)
        ticket_payloads = [
            {
                **ticket.as_dict(1),
                "expanded_columns": (
                    [
                        {"signs": list(column), "pleno": ticket.pleno_label}
                        for column in expanded
                    ]
                    if expanded is not None
                    else None
                ),
                "expanded_note": (
                    None
                    if expanded is not None
                    else (
                        f"El boleto tiene {ticket.columns} columnas; se omite la "
                        "expansión completa para no saturar la interfaz."
                    )
                ),
            }
        ]
    else:
        affordable = max(1, int(budget // TICKET_PRICE_EUR))
        requested = min(count, affordable, 10)
        tickets = optimize_portfolio(
            bundle.predictions,
            bundle.pleno,
            requested,
            config,
            strategy,
            seed=effective_seed,
        )
        # La cartera se eligió con las simulaciones de ``effective_seed``.
        # Se evalúa con otra semilla para no reportar métricas in-sample.
        portfolio = _portfolio_metrics(
            tickets,
            bundle.predictions,
            simulations=config.simulations,
            seed=(effective_seed + 1) % (2**32),
        )
        ticket_payloads = [
            {
                **ticket.as_dict(index + 1),
                "expanded_columns": None,
                "expanded_note": None,
            }
            for index, ticket in enumerate(tickets)
        ]

    matches = [_match_payload(prediction) for prediction in bundle.predictions]
    return {
        "game": GAME_INFO,
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "seed": effective_seed,
        "mode": mode,
        "strategy": strategy,
        "strategy_label": _strategy(strategy)["label"],
        "strategy_description": _strategy(strategy)["description"],
        "jornada": _jornada_payload(bundle.jornada),
        "budget": {
            "requested": round(budget, 2),
            "max_doubles": max_doubles,
            "max_triples": max_triples,
            "max_columns": config.max_columns,
            "max_cost": round(config.max_columns * TICKET_PRICE_EUR, 2),
            "ticket_price": TICKET_PRICE_EUR,
        },
        "matches": matches,
        "tickets": ticket_payloads,
        "portfolio": portfolio,
        "analysis": {
            "most_confident": [
                {
                    "match_number": prediction.match_number,
                    "match": f"{prediction.home_raw} - {prediction.away_raw}",
                    "pick": max(prediction.probabilities, key=prediction.probabilities.get),
                    "probability": round(max(prediction.probabilities.values()), 4),
                }
                for prediction in sorted(
                    bundle.predictions,
                    key=lambda item: max(item.probabilities.values()),
                    reverse=True,
                )[:3]
            ],
            "most_uncertain": [
                {
                    "match_number": prediction.match_number,
                    "match": f"{prediction.home_raw} - {prediction.away_raw}",
                    "pick": max(prediction.probabilities, key=prediction.probabilities.get),
                    "probability": round(max(prediction.probabilities.values()), 4),
                }
                for prediction in sorted(
                    (item for item in bundle.predictions if not item.is_pleno),
                    key=lambda item: max(item.probabilities.values()),
                )[:3]
            ],
            "average_confidence": round(
                sum(prediction.confidence for prediction in bundle.predictions)
                / max(1, len(bundle.predictions)),
                4,
            ),
            "data_quality": {
                "alta": sum(1 for prediction in bundle.predictions if prediction.data_quality == "alta"),
                "media": sum(1 for prediction in bundle.predictions if prediction.data_quality == "media"),
                "baja": sum(1 for prediction in bundle.predictions if prediction.data_quality == "baja"),
                "sin_datos": sum(
                    1 for prediction in bundle.predictions if prediction.data_quality == "sin datos"
                ),
            },
            "pleno": {
                "score": f"{bundle.pleno_score[0]}-{bundle.pleno_score[1]}",
                "probability": round(bundle.pleno_probability, 6),
                "alternatives": bundle.pleno.score_options,
            },
        },
        "recommendations": _recommendations(bundle, tickets, config, mode),
        "disclaimer": (
            "La Quiniela es un juego de azar. Las probabilidades proceden de un "
            "modelo estadístico (Poisson Dixon-Coles + Elo) y no garantizan "
            "ningún resultado. Los premios son de reparto y pueden variar. "
            "Juega con responsabilidad y solo dinero que puedas permitirte perder."
        ),
    }


def get_jornada_predictions(
    jornada: Optional[int] = None, season: Optional[str] = None
) -> dict[str, object]:
    """Predicciones completas de una jornada, sin generar boletos."""
    bundle = _bundle(jornada, season)
    return {
        "jornada": _jornada_payload(bundle.jornada),
        "matches": [_match_payload(prediction) for prediction in bundle.predictions],
        "pleno": {
            "match_number": bundle.pleno.match_number,
            "score": f"{bundle.pleno_score[0]}-{bundle.pleno_score[1]}",
            "probability": round(bundle.pleno_probability, 6),
            "alternatives": bundle.pleno.score_options,
        },
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
    }


def list_jornadas() -> list[dict[str, object]]:
    manager = get_quiniela_data_manager()
    return [_jornada_payload(jornada) for jornada in manager.jornadas()]
