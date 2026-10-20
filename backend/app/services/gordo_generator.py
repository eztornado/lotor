"""
Generador inteligente de combinaciones de El Gordo de la Primitiva.

Objetivo
--------
No existe ningún algoritmo capaz de predecir una lotería uniforme. Lo que sí
se puede hacer es construir una *cartera* de apuestas mejor que una elección
ingenua:

1. Modelo de propensión por número (frecuencia a largo plazo, frecuencia
   reciente, retraso y afinidad de pares) con suavizado bayesiano y pesos
   deliberadamente moderados para no sobreajustar.
2. Modelo del número clave (0-9) con frecuencia, tendencia y retraso.
3. Filtro estructural aprendido del histórico: suma, paridad, bajos/altos,
   distribución por décadas, consecutivos y terminaciones.
4. Penalización de combinaciones populares (fechas de nacimiento, progresiones,
   patrones obvios...) para reducir el riesgo de compartir un gran premio.
5. Optimización de cartera: maximiza calidad media, cobertura de números,
   pares y tríos, y mantiene las apuestas disjuntas.
6. Cobertura de claves: con 10 apuestas se cubren las 10 claves posibles, de
   modo que una de ellas lleva siempre la clave ganadora y su reintegro
   (1,50 €), compatible con los premios de las 8 categorías.

Las probabilidades que se muestran son matemáticamente exactas para carteras
disjuntas (se calculan por enumeración combinatoria). La simulación se incluye
como comprobación independiente. Ninguna estrategia puede aumentar la
probabilidad del primer premio por apuesta: 1 entre 31.625.100.
"""

from __future__ import annotations

import datetime as dt
import math
import random
import threading
from collections import Counter
from dataclasses import dataclass, field
from itertools import combinations
from typing import Optional, Sequence

from loguru import logger

from app.services.gordo_data import (
    Draw,
    KEY_SIZE,
    PICK_SIZE,
    POOL_SIZE,
    get_gordo_data_manager,
    next_gordo_date,
)

NUMBER_COMBINATIONS = math.comb(POOL_SIZE, PICK_SIZE)  # 3.162.510
TOTAL_COMBINATIONS = NUMBER_COMBINATIONS * KEY_SIZE  # 31.625.100
TICKET_PRICE_EUR = 1.5
REINTEGRO_PROBABILITY = 1.0 / KEY_SIZE

# Número de combinaciones que otorgan cada categoría de premio.
PRIZE_COUNTS = {
    "1": 1,                # 5 + clave
    "2": 9,                # 5
    "3": 245,              # 4 + clave
    "4": 2_205,            # 4
    "5": 11_760,           # 3 + clave
    "6": 105_840,          # 3
    "7": 184_240,          # 2 + clave
    "8": 1_658_160,        # 2
}

PRIZE_PROBABILITIES = {
    category: count / TOTAL_COMBINATIONS
    for category, count in PRIZE_COUNTS.items()
}

TWO_PLUS_COUNT = sum(PRIZE_COUNTS.values())  # 1.962.460
THREE_PLUS_COUNT = sum(PRIZE_COUNTS[key] for key in ("1", "2", "3", "4", "5", "6"))
FOUR_PLUS_COUNT = sum(PRIZE_COUNTS[key] for key in ("1", "2", "3", "4"))
FIVE_PLUS_COUNT = PRIZE_COUNTS["1"] + PRIZE_COUNTS["2"]
KEY_TWO_PLUS_COUNT = sum(PRIZE_COUNTS[key] for key in ("1", "2", "3", "4", "5", "6", "7"))

GAME_INFO = {
    "name": "El Gordo de la Primitiva",
    "numbers_per_ticket": PICK_SIZE,
    "max_number": POOL_SIZE,
    "key_range": [0, 9],
    "draw_days": "Domingos",
    "ticket_price_eur": TICKET_PRICE_EUR,
    "prize_categories": {
        "1": "1ª categoría (5 + clave)",
        "2": "2ª categoría (5 aciertos)",
        "3": "3ª categoría (4 + clave)",
        "4": "4ª categoría (4 aciertos)",
        "5": "5ª categoría (3 + clave)",
        "6": "6ª categoría (3 aciertos)",
        "7": "7ª categoría (2 + clave)",
        "8": "8ª categoría (2 aciertos)",
        "reintegro": "Reintegro (clave acertada, 1,50 €)",
    },
}

STRATEGIES = {
    "big_prize": {
        "label": "Máximo premio",
        "description": (
            "Prioriza cobertura de pares y tríos, baja popularidad y calidad "
            "estadística. Pensada para maximizar opciones en categorías altas "
            "y reducir el riesgo de compartir el premio."
        ),
        # quality, numbers, pairs, triples, overlap, balance, popularity
        "weights": (0.24, 0.22, 0.14, 0.12, 0.20, 0.04, 0.04),
    },
    "balanced": {
        "label": "Equilibrada",
        "description": "Reparte el peso entre calidad estadística y cobertura.",
        "weights": (0.42, 0.18, 0.12, 0.10, 0.12, 0.03, 0.03),
    },
    "coverage": {
        "label": "Máxima cobertura",
        "description": (
            "Maximiza números, pares y tríos distintos. Ideal para repartir "
            "las opciones entre muchos resultados posibles."
        ),
        "weights": (0.10, 0.26, 0.18, 0.14, 0.24, 0.04, 0.04),
    },
    "statistical": {
        "label": "Estadística pura",
        "description": (
            "Da prioridad a los números con mayor propensión histórica y "
            "reciente, con menos énfasis en la cobertura."
        ),
        "weights": (0.72, 0.08, 0.05, 0.04, 0.06, 0.03, 0.02),
    },
}

DECADES = ((1, 9), (10, 19), (20, 29), (30, 39), (40, 49), (50, 54))
DECADE_LABELS = ("1-9", "10-19", "20-29", "30-39", "40-49", "50-54")
DECADE_PATTERNS = 252  # C(5 + 6 - 1, 5)
PAIRS_PER_TICKET = math.comb(PICK_SIZE, 2)  # 10
TRIPLES_PER_TICKET = math.comb(PICK_SIZE, 3)  # 10


def _decade_index(number: int) -> int:
    if number <= 9:
        return 0
    if number <= 19:
        return 1
    if number <= 29:
        return 2
    if number <= 39:
        return 3
    if number <= 49:
        return 4
    return 5


def _decade_counts(numbers: Sequence[int]) -> tuple[int, ...]:
    counts = [0] * len(DECADES)
    for number in numbers:
        counts[_decade_index(number)] += 1
    return tuple(counts)


def _consecutive_pairs(numbers: Sequence[int]) -> int:
    ordered = sorted(numbers)
    return sum(
        1 for left, right in zip(ordered, ordered[1:]) if right - left == 1
    )


def _has_consecutive_block(numbers: Sequence[int], size: int = 4) -> bool:
    ordered = sorted(numbers)
    run = 1
    for left, right in zip(ordered, ordered[1:]):
        if right - left == 1:
            run += 1
            if run >= size:
                return True
        else:
            run = 1
    return False


def _arithmetic_progression(numbers: Sequence[int]) -> bool:
    ordered = sorted(numbers)
    differences = [right - left for left, right in zip(ordered, ordered[1:])]
    return len(set(differences)) == 1


def _sigmoid(value: float) -> float:
    if value >= 0:
        return 1.0 / (1.0 + math.exp(-value))
    exponential = math.exp(value)
    return exponential / (1.0 + exponential)


def _standardize(values: Sequence[float]) -> list[float]:
    if not values:
        return []
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / max(1, len(values) - 1)
    deviation = math.sqrt(variance) or 1.0
    return [(value - mean) / deviation for value in values]


def _clip(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


@dataclass(frozen=True, slots=True)
class GordoConfig:
    half_life_days: float = 730.0       # 2 años para la frecuencia estructural
    recent_half_life_days: float = 45.0  # mes y medio para la tendencia reciente
    recent_window_days: int = 365
    model_strength: float = 0.65
    candidate_count: int = 18_000
    uniform_share: float = 0.32
    pool_size: int = 1_400
    structural_draws: int = 1_100
    simulations: int = 60_000
    local_search_candidates: int = 400
    local_search_passes: int = 2


@dataclass(slots=True)
class NumberProfile:
    number: int
    frequency: int
    decayed_frequency: float
    recent_frequency: float
    last_seen: Optional[dt.date]
    gap_draws: int
    gap_days: Optional[int]
    long_lift: float
    recent_lift: float
    overdue_z: float
    pair_z: float
    log_weight: float
    weight: float


@dataclass(slots=True)
class KeyProfile:
    digit: int
    frequency: int
    decayed_frequency: float
    probability: float
    last_seen: Optional[dt.date]
    gap_draws: int


@dataclass(slots=True)
class Candidate:
    numbers: tuple[int, ...]
    model_score: float
    structure_score: float
    popularity: float
    total_score: float
    quality: float
    popularity_norm: float = 0.0
    number_set: frozenset[int] = field(init=False)
    pair_set: frozenset[tuple[int, int]] = field(init=False)
    triple_set: frozenset[tuple[int, int, int]] = field(init=False)

    def __post_init__(self) -> None:
        self.number_set = frozenset(self.numbers)
        self.pair_set = frozenset(combinations(self.numbers, 2))
        self.triple_set = frozenset(combinations(self.numbers, 3))


@dataclass(slots=True)
class StructuralModel:
    average_sum: float
    sum_deviation: float
    average_spread: float
    spread_deviation: float
    odd_counts: Counter
    low_counts: Counter
    consecutive_counts: Counter
    ending_counts: Counter
    decade_probabilities: tuple[float, ...]
    decade_patterns: Counter
    total_draws: int

    @classmethod
    def from_draws(cls, draws: Sequence[Draw]) -> "StructuralModel":
        odd_counts: Counter = Counter()
        low_counts: Counter = Counter()
        consecutive_counts: Counter = Counter()
        ending_counts: Counter = Counter()
        decade_patterns: Counter = Counter()
        sums: list[int] = []
        spreads: list[int] = []
        decade_totals = [0] * len(DECADES)

        for draw in draws:
            numbers = draw.numbers
            sums.append(sum(numbers))
            spreads.append(max(numbers) - min(numbers))
            odd_counts[sum(1 for number in numbers if number % 2)] += 1
            low_counts[sum(1 for number in numbers if number <= 27)] += 1
            consecutive_counts[_consecutive_pairs(numbers)] += 1
            ending_counts[len({number % 10 for number in numbers})] += 1
            pattern = _decade_counts(numbers)
            decade_patterns[pattern] += 1
            for index, count in enumerate(pattern):
                decade_totals[index] += count

        total_draws = len(draws)
        average_sum = sum(sums) / total_draws if total_draws else 137.5
        sum_deviation = (
            math.sqrt(sum((value - average_sum) ** 2 for value in sums) / total_draws)
            if total_draws
            else 40.0
        ) or 1.0
        average_spread = sum(spreads) / total_draws if total_draws else 40.0
        spread_deviation = (
            math.sqrt(
                sum((value - average_spread) ** 2 for value in spreads) / total_draws
            )
            if total_draws
            else 12.0
        ) or 1.0

        total_numbers = sum(decade_totals) or 1
        decade_probabilities = tuple(value / total_numbers for value in decade_totals)

        return cls(
            average_sum=average_sum,
            sum_deviation=sum_deviation,
            average_spread=average_spread,
            spread_deviation=spread_deviation,
            odd_counts=odd_counts,
            low_counts=low_counts,
            consecutive_counts=consecutive_counts,
            ending_counts=ending_counts,
            decade_probabilities=decade_probabilities,
            decade_patterns=decade_patterns,
            total_draws=total_draws,
        )

    @staticmethod
    def _categorical_log_probability(
        counter: Counter, value: int, possible_values: int, alpha: float = 2.0
    ) -> float:
        total = sum(counter.values())
        return math.log(
            (counter.get(value, 0) + alpha) / (total + alpha * possible_values)
        )

    def _gaussian_log_probability(
        self, value: float, mean: float, deviation: float
    ) -> float:
        z = (value - mean) / deviation
        return -0.5 * z * z - math.log(deviation * math.sqrt(2 * math.pi))

    def _multinomial_decade_log_probability(self, counts: tuple[int, ...]) -> float:
        value = math.lgamma(PICK_SIZE + 1)
        for count in counts:
            value -= math.lgamma(count + 1)
        for count, probability in zip(counts, self.decade_probabilities):
            value += count * math.log(max(probability, 1e-9))

        # Suavizado con el patrón exacto observado: evita que patrones nunca
        # vistos reciban una probabilidad excesiva.
        total_patterns = sum(self.decade_patterns.values()) or 1
        pattern_probability = (
            self.decade_patterns.get(counts, 0) + 1.0
        ) / (total_patterns + DECADE_PATTERNS)
        return 0.5 * value + 0.5 * math.log(pattern_probability)

    def score(self, numbers: Sequence[int]) -> float:
        ordered = sorted(numbers)
        odd_count = sum(1 for number in ordered if number % 2)
        low_count = sum(1 for number in ordered if number <= 27)
        consecutive = _consecutive_pairs(ordered)
        endings = len({number % 10 for number in ordered})
        decade_pattern = _decade_counts(ordered)
        spread = ordered[-1] - ordered[0]

        score = 0.30 * self._gaussian_log_probability(
            sum(ordered), self.average_sum, self.sum_deviation
        )
        score += 0.18 * self._categorical_log_probability(
            self.odd_counts, odd_count, PICK_SIZE + 1
        )
        score += 0.15 * self._categorical_log_probability(
            self.low_counts, low_count, PICK_SIZE + 1
        )
        score += 0.20 * self._multinomial_decade_log_probability(decade_pattern)
        score += 0.10 * self._categorical_log_probability(
            self.consecutive_counts, consecutive, PICK_SIZE
        )
        score += 0.04 * self._categorical_log_probability(
            self.ending_counts, endings, PICK_SIZE
        )
        score += 0.03 * self._gaussian_log_probability(
            spread, self.average_spread, self.spread_deviation
        )

        # Los patrones con una década muy concentrada son raros y, además,
        # suelen ser elegidos por jugadores que buscan "formas".
        if max(decade_pattern) >= 4:
            score -= 0.5 * (max(decade_pattern) - 3)

        return score

    def summary(self) -> dict:
        most_common_pattern = (
            self.decade_patterns.most_common(1)[0] if self.decade_patterns else None
        )
        return {
            "draws_used": self.total_draws,
            "average_sum": round(self.average_sum, 2),
            "sum_deviation": round(self.sum_deviation, 2),
            "average_spread": round(self.average_spread, 2),
            "odd_distribution": dict(sorted(self.odd_counts.items())),
            "low_distribution": dict(sorted(self.low_counts.items())),
            "consecutive_distribution": dict(sorted(self.consecutive_counts.items())),
            "most_common_decade_pattern": {
                "pattern": list(most_common_pattern[0]) if most_common_pattern else [],
                "labels": list(DECADE_LABELS),
                "count": most_common_pattern[1] if most_common_pattern else 0,
            },
        }


class GordoModel:
    """Estadísticas y puntuaciones de un histórico de El Gordo."""

    def __init__(self, draws: Sequence[Draw], config: GordoConfig):
        if not draws:
            raise ValueError("No hay sorteos para construir el modelo")
        self.config = config
        self.draws = sorted(draws, key=lambda item: item.date)
        self.reference_date = self.draws[-1].date
        self.previous_draw = self.draws[-1]

        self.number_profiles: list[NumberProfile] = []
        self.key_profiles: list[KeyProfile] = []
        self.structural = StructuralModel.from_draws(
            self.draws[-config.structural_draws :]
        )
        self._pair_lifts: dict[tuple[int, int], float] = {}
        self._top_pairs: list[tuple[int, int, int, float]] = []
        self._build_number_model()
        self._build_key_model()

    # ------------------------------------------------------------------
    # Modelo de números
    # ------------------------------------------------------------------
    def _build_number_model(self) -> None:
        total_long = 0.0
        total_recent = 0.0
        decayed_counts = [0.0] * (POOL_SIZE + 1)
        recent_counts = [0.0] * (POOL_SIZE + 1)
        raw_counts = [0] * (POOL_SIZE + 1)
        last_seen: list[Optional[dt.date]] = [None] * (POOL_SIZE + 1)
        gap_draws = [0] * (POOL_SIZE + 1)
        pair_counts: dict[tuple[int, int], float] = Counter()

        # Recorremos de más reciente a más antiguo para calcular rachas.
        for reverse_index, draw in enumerate(reversed(self.draws)):
            age_days = (self.reference_date - draw.date).days
            long_weight = 0.5 ** (age_days / self.config.half_life_days)
            recent_weight = 0.0
            if age_days <= self.config.recent_window_days:
                recent_weight = 0.5 ** (
                    age_days / self.config.recent_half_life_days
                )

            total_long += long_weight
            total_recent += recent_weight

            for number in draw.numbers:
                decayed_counts[number] += long_weight
                recent_counts[number] += recent_weight
                raw_counts[number] += 1
                if last_seen[number] is None:
                    last_seen[number] = draw.date
                    gap_draws[number] = reverse_index

            for left, right in combinations(draw.numbers, 2):
                pair_counts[(left, right)] += long_weight

        # Probabilidad base de un número y de un par.
        base_number_probability = PICK_SIZE / POOL_SIZE
        base_pair_probability = (
            PICK_SIZE * (PICK_SIZE - 1)
        ) / (POOL_SIZE * (POOL_SIZE - 1))

        number_prior = 18.0
        pair_prior = 30.0

        long_lifts: list[float] = []
        recent_lifts: list[float] = []
        overdue_values: list[float] = []
        pair_number_values: list[float] = []
        pair_lifts: dict[tuple[int, int], float] = {}

        for left in range(1, POOL_SIZE + 1):
            for right in range(left + 1, POOL_SIZE + 1):
                count = pair_counts.get((left, right), 0.0)
                probability = (count + pair_prior * base_pair_probability) / (
                    total_long + pair_prior
                )
                pair_lifts[(left, right)] = math.log(
                    max(probability, 1e-12) / base_pair_probability
                )
        self._pair_lifts = pair_lifts

        self._top_pairs = sorted(
            (
                (left, right, int(round(pair_counts.get((left, right), 0.0))), lift)
                for (left, right), lift in pair_lifts.items()
                if pair_counts.get((left, right), 0.0) > 0
            ),
            key=lambda item: item[3],
            reverse=True,
        )[:20]

        for number in range(1, POOL_SIZE + 1):
            long_probability = (
                decayed_counts[number] + number_prior * base_number_probability
            ) / (total_long + number_prior)
            long_lift = math.log(
                max(long_probability, 1e-12) / base_number_probability
            )

            recent_probability = (
                recent_counts[number] + number_prior * base_number_probability
            ) / (total_recent + number_prior)
            recent_lift = math.log(
                max(recent_probability, 1e-12) / base_number_probability
            )

            # Retraso: cuántos sorteos lleva sin aparecer frente a la espera
            # media de 54/5 = 10,8 sorteos. Se usa log para suavizar la cola.
            overdue_values.append(math.log1p(gap_draws[number]))

            # Afinidad media de este número con el resto (pares históricos).
            affinities = [
                pair_lifts[(min(number, other), max(number, other))]
                for other in range(1, POOL_SIZE + 1)
                if other != number
            ]
            pair_number_values.append(sum(affinities) / len(affinities))

            long_lifts.append(long_lift)
            recent_lifts.append(recent_lift)

            last_date = last_seen[number]
            self.number_profiles.append(
                NumberProfile(
                    number=number,
                    frequency=raw_counts[number],
                    decayed_frequency=decayed_counts[number],
                    recent_frequency=recent_counts[number],
                    last_seen=last_date,
                    gap_draws=gap_draws[number],
                    gap_days=(
                        (self.reference_date - last_date).days
                        if last_date is not None
                        else None
                    ),
                    long_lift=long_lift,
                    recent_lift=recent_lift,
                    overdue_z=0.0,
                    pair_z=0.0,
                    log_weight=0.0,
                    weight=1.0,
                )
            )

        long_z = _standardize(long_lifts)
        recent_z = _standardize(recent_lifts)
        overdue_z = _standardize(overdue_values)
        pair_z = _standardize(pair_number_values)

        strength = self.config.model_strength
        log_weights: list[float] = []
        for index, profile in enumerate(self.number_profiles):
            combined = (
                0.45 * _clip(long_z[index], -2.0, 2.0)
                + 0.30 * _clip(recent_z[index], -2.0, 2.0)
                + 0.15 * _clip(overdue_z[index], -2.0, 2.0)
                + 0.10 * _clip(pair_z[index], -2.0, 2.0)
            )
            log_weight = _clip(strength * combined, -0.28, 0.28)
            log_weights.append(log_weight)
            profile.overdue_z = overdue_z[index]
            profile.pair_z = pair_z[index]
            profile.log_weight = log_weight

        weights = [math.exp(value) for value in log_weights]
        mean_weight = sum(weights) / len(weights)
        for profile, weight in zip(self.number_profiles, weights):
            profile.weight = weight / mean_weight

    # ------------------------------------------------------------------
    # Modelo de la clave
    # ------------------------------------------------------------------
    def _build_key_model(self) -> None:
        total_weight = 0.0
        decayed = [0.0] * KEY_SIZE
        counts = [0] * KEY_SIZE
        last_seen: list[Optional[dt.date]] = [None] * KEY_SIZE
        gap_draws = [0] * KEY_SIZE

        draw_index = 0
        for draw in reversed(self.draws):
            if draw.key_number is None:
                continue
            age_days = (self.reference_date - draw.date).days
            weight = 0.5 ** (age_days / self.config.half_life_days)
            total_weight += weight
            decayed[draw.key_number] += weight
            counts[draw.key_number] += 1
            if last_seen[draw.key_number] is None:
                last_seen[draw.key_number] = draw.date
                gap_draws[draw.key_number] = draw_index
            draw_index += 1

        prior = 10.0
        for digit in range(KEY_SIZE):
            probability = (decayed[digit] + prior / KEY_SIZE) / (
                total_weight + prior
            )
            self.key_profiles.append(
                KeyProfile(
                    digit=digit,
                    frequency=counts[digit],
                    decayed_frequency=decayed[digit],
                    probability=probability,
                    last_seen=last_seen[digit],
                    gap_draws=gap_draws[digit],
                )
            )

    # ------------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------------
    @property
    def weights(self) -> list[float]:
        return [profile.weight for profile in self.number_profiles]

    def popularity_penalty(self, numbers: Sequence[int]) -> float:
        """Penaliza combinaciones que mucha gente juega (riesgo de compartir)."""
        ordered = sorted(numbers)
        penalty = 0.0

        date_numbers = sum(1 for number in ordered if number <= 31)
        if date_numbers >= 5:
            penalty += (date_numbers - 4) * 0.7
        if date_numbers == PICK_SIZE:
            penalty += 0.9
        if all(number <= 12 for number in ordered):
            penalty += 1.5
        if all(number <= 31 for number in ordered):
            penalty += 0.8

        decades = _decade_counts(ordered)
        if max(decades) == PICK_SIZE:
            penalty += 2.5
        elif max(decades) >= 4:
            penalty += 0.7

        if _arithmetic_progression(ordered):
            penalty += 2.5
        if _has_consecutive_block(ordered, 4):
            penalty += 1.0

        common_divisor = 0
        for divisor in range(2, 10):
            if all(number % divisor == 0 for number in ordered):
                common_divisor = divisor
                break
        if common_divisor:
            penalty += 1.0

        ending_counts = Counter(number % 10 for number in ordered)
        if max(ending_counts.values()) >= 4:
            penalty += 0.6

        odd_count = sum(1 for number in ordered if number % 2)
        if odd_count in (0, PICK_SIZE):
            penalty += 0.6
        if all(number <= 27 for number in ordered) or all(
            number >= 28 for number in ordered
        ):
            penalty += 0.5

        previous_numbers = set(self.previous_draw.numbers)
        overlap = len(previous_numbers.intersection(ordered))
        if overlap == PICK_SIZE:
            penalty += 5.0
        elif overlap == PICK_SIZE - 1:
            penalty += 0.9
        elif overlap == PICK_SIZE - 2:
            penalty += 0.2

        return min(penalty, 6.0)

    def _weighted_sample(self, rng: random.Random) -> tuple[int, ...]:
        available = list(range(1, POOL_SIZE + 1))
        current_weights = self.weights
        selected: list[int] = []

        for _ in range(PICK_SIZE):
            total = sum(current_weights)
            target = rng.random() * total
            accumulated = 0.0
            chosen_index = len(available) - 1
            for index, weight in enumerate(current_weights):
                accumulated += weight
                if target <= accumulated:
                    chosen_index = index
                    break
            selected.append(available.pop(chosen_index))
            current_weights.pop(chosen_index)

        return tuple(sorted(selected))

    def build_candidates(self, seed: int, candidate_count: int) -> list[Candidate]:
        rng = random.Random(seed)
        seen: set[tuple[int, ...]] = set()
        raw_candidates: list[tuple[tuple[int, ...], float, float, float]] = []
        ordered_profiles = sorted(
            self.number_profiles, key=lambda item: item.weight, reverse=True
        )
        top_numbers = [profile.number for profile in ordered_profiles]
        log_weights = {
            profile.number: profile.log_weight for profile in self.number_profiles
        }

        def add(numbers: Sequence[int]) -> None:
            candidate_numbers = tuple(sorted(numbers))
            if len(set(candidate_numbers)) != PICK_SIZE:
                return
            if candidate_numbers in seen:
                return
            seen.add(candidate_numbers)
            model_score = sum(log_weights[number] for number in candidate_numbers)
            structure_score = self.structural.score(candidate_numbers)
            popularity = self.popularity_penalty(candidate_numbers)
            raw_candidates.append(
                (candidate_numbers, model_score, structure_score, popularity)
            )

        # Semillas deterministas: la mejor combinación por peso y una
        # combinación de cobertura por cada número.
        add(top_numbers[:PICK_SIZE])
        for number in range(1, POOL_SIZE + 1):
            others = [candidate for candidate in top_numbers if candidate != number][:5]
            add([number, *others[: PICK_SIZE - 1]])
        for start in range(0, 20, PICK_SIZE):
            block = top_numbers[start : start + PICK_SIZE]
            if len(block) == PICK_SIZE:
                add(block)

        # Combinaciones equilibradas por décadas: elegimos 5 de las 6 décadas
        # y rotamos la década que queda fuera.
        for omitted in range(len(DECADES)):
            for shifted in range(6):
                chosen: list[int] = []
                for decade_index, (low, high) in enumerate(DECADES):
                    if decade_index == omitted:
                        continue
                    offset = (decade_index + shifted) % max(1, high - low + 1)
                    chosen.append(low + offset)
                for number in top_numbers:
                    if len(chosen) >= PICK_SIZE:
                        break
                    if number not in chosen:
                        chosen.append(number)
                add(chosen[:PICK_SIZE])

        # Muestreo ponderado masivo.
        attempts = 0
        uniform_target = int(candidate_count * self.config.uniform_share)
        weighted_target = candidate_count - uniform_target
        max_attempts = max(candidate_count * 4, 2000)

        while len(raw_candidates) < weighted_target and attempts < max_attempts:
            attempts += 1
            add(self._weighted_sample(rng))

        # Una parte de la población debe ser uniforme. Sin ella, el pool se
        # concentra en los números "calientes" y se reduce la diversidad.
        while len(raw_candidates) < candidate_count and attempts < max_attempts * 2:
            attempts += 1
            add(rng.sample(range(1, POOL_SIZE + 1), PICK_SIZE))

        if len(raw_candidates) < candidate_count:
            # Completar con aleatorias uniformes si hiciera falta.
            while len(raw_candidates) < candidate_count and attempts < max_attempts * 3:
                attempts += 1
                add(rng.sample(range(1, POOL_SIZE + 1), PICK_SIZE))

        model_values = [item[1] for item in raw_candidates]
        structure_values = [item[2] for item in raw_candidates]
        model_z = _standardize(model_values)
        structure_z = _standardize(structure_values)

        candidates: list[Candidate] = []
        for index, (numbers, model_score, structure_score, popularity) in enumerate(
            raw_candidates
        ):
            popularity_norm = _clip(popularity / 4.0, 0.0, 1.5)
            total_score = (
                0.55 * _clip(model_z[index], -3.0, 3.0)
                + 0.45 * _clip(structure_z[index], -3.0, 3.0)
                - 0.65 * popularity_norm
            )
            candidates.append(
                Candidate(
                    numbers=numbers,
                    model_score=model_score,
                    structure_score=structure_score,
                    popularity=popularity,
                    total_score=total_score,
                    quality=_sigmoid(total_score),
                    popularity_norm=popularity_norm,
                )
            )

        candidates.sort(key=lambda item: item.total_score, reverse=True)
        logger.info(
            f"El Gordo: {len(candidates)} candidatos generados "
            f"(semilla {seed}, {attempts} intentos)"
        )
        return candidates

    def select_pool(
        self,
        candidates: Sequence[Candidate],
        pool_size: int,
        count: int = 10,
    ) -> list[Candidate]:
        """Selecciona los mejores candidatos garantizando cobertura de números."""
        pool: dict[tuple[int, ...], Candidate] = {}
        for candidate in candidates[:pool_size]:
            pool[candidate.numbers] = candidate

        # Añadimos el mejor candidato que contiene cada número. Esto evita que
        # un número quede fuera de la cartera por una racha desfavorable.
        best_by_number: dict[int, Candidate] = {}
        for candidate in candidates:
            for number in candidate.numbers:
                if number not in best_by_number:
                    best_by_number[number] = candidate
            if len(best_by_number) == POOL_SIZE:
                break
        for candidate in best_by_number.values():
            pool.setdefault(candidate.numbers, candidate)

        # Añadimos varias "columnas vertebrales" de cobertura para el tamaño
        # de cartera solicitado. Se construyen con un greedy de máxima
        # cobertura sobre todos los candidatos, no solo sobre el top por
        # calidad.
        for variant in range(4):
            backbone: list[Candidate] = []
            backbone_numbers: set[tuple[int, ...]] = set()
            covered: set[int] = set()
            for _ in range(count):
                best_candidate: Optional[Candidate] = None
                best_key: Optional[tuple[float, float]] = None
                for candidate in candidates:
                    if candidate.numbers in backbone_numbers:
                        continue
                    new_numbers = len(candidate.number_set - covered)
                    overlap = len(candidate.number_set.intersection(covered))
                    key = (
                        new_numbers * 10.0
                        + candidate.total_score * (variant * 0.5 + 0.5)
                        - overlap * (0.02 + variant * 0.04),
                        candidate.total_score,
                    )
                    if best_key is None or key > best_key:
                        best_key = key
                        best_candidate = candidate
                if best_candidate is None:
                    break
                backbone.append(best_candidate)
                backbone_numbers.add(best_candidate.numbers)
                covered.update(best_candidate.numbers)
            for candidate in backbone:
                pool.setdefault(candidate.numbers, candidate)

        # Para carteras de hasta 10 apuestas es posible que todos los números
        # sean distintos (10 × 5 = 50 ≤ 54). Buscamos explícitamente una
        # cartera disjunta: es la estructura que permite calcular las
        # probabilidades exactas y maximiza la cobertura.
        shuffle_rng = random.Random(20261020 + count)
        best_disjoint: list[Candidate] = []
        best_disjoint_key: Optional[tuple[int, float]] = None
        for _ in range(16):
            shuffled = list(candidates)
            shuffle_rng.shuffle(shuffled)
            chosen: list[Candidate] = []
            used: set[int] = set()
            for candidate in shuffled:
                if len(chosen) >= count:
                    break
                if used.intersection(candidate.number_set):
                    continue
                chosen.append(candidate)
                used.update(candidate.number_set)
            key = (
                len(used),
                sum(candidate.total_score for candidate in chosen),
            )
            if best_disjoint_key is None or key > best_disjoint_key:
                best_disjoint_key = key
                best_disjoint = chosen
        for candidate in best_disjoint:
            pool.setdefault(candidate.numbers, candidate)

        return list(pool.values())

    # ------------------------------------------------------------------
    # Optimización de cartera
    # ------------------------------------------------------------------
    @staticmethod
    def _strategy_weights(strategy: str) -> tuple[float, ...]:
        return STRATEGIES.get(strategy, STRATEGIES["big_prize"])["weights"]

    def _objective(
        self, selected: Sequence[Candidate], strategy: str, coverage_target: int = 0
    ) -> float:
        if not selected:
            return 0.0

        wq, wn, wp, wt, wo, wb, wpop = self._strategy_weights(strategy)
        count = len(selected)
        numbers: set[int] = set()
        pairs: set[tuple[int, int]] = set()
        triples: set[tuple[int, int, int]] = set()
        appearances: Counter = Counter()
        quality = 0.0
        popularity = 0.0
        overlap_total = 0

        for index, candidate in enumerate(selected):
            numbers.update(candidate.number_set)
            pairs.update(candidate.pair_set)
            triples.update(candidate.triple_set)
            appearances.update(candidate.numbers)
            quality += candidate.quality
            popularity += candidate.popularity_norm
            for other in selected[index + 1 :]:
                overlap_total += len(candidate.number_set.intersection(other.number_set))

        number_coverage = len(numbers) / min(POOL_SIZE, PICK_SIZE * count)
        pair_coverage = len(pairs) / (PAIRS_PER_TICKET * count)
        triple_coverage = len(triples) / (TRIPLES_PER_TICKET * count)
        total_ticket_pairs = count * (count - 1) / 2
        average_overlap = (
            overlap_total / total_ticket_pairs if total_ticket_pairs else 0.0
        )
        overlap_score = max(0.0, 1.0 - average_overlap / 2.0)
        max_appearances = max(appearances.values()) if appearances else 0
        balance_score = max(0.0, 1.0 - max(0, max_appearances - 2) / 4.0)
        coverage_penalty = 5.0 * max(0, coverage_target - len(numbers))

        return (
            wq * (quality / count)
            + wn * number_coverage
            + wp * pair_coverage
            + wt * triple_coverage
            + wo * overlap_score
            + wb * balance_score
            - wpop * (popularity / count)
            - coverage_penalty
        )

    def _candidate_stats(
        self, pool: Sequence[Candidate]
    ) -> tuple[float, float, float, float]:
        model_values = [candidate.model_score for candidate in pool]
        structure_values = [candidate.structure_score for candidate in pool]
        model_mean = sum(model_values) / len(model_values)
        structure_mean = sum(structure_values) / len(structure_values)
        model_std = math.sqrt(
            sum((value - model_mean) ** 2 for value in model_values)
            / max(1, len(model_values) - 1)
        ) or 1.0
        structure_std = math.sqrt(
            sum((value - structure_mean) ** 2 for value in structure_values)
            / max(1, len(structure_values) - 1)
        ) or 1.0
        return model_mean, model_std, structure_mean, structure_std

    def _candidate_from_numbers(
        self,
        numbers: Sequence[int],
        stats: tuple[float, float, float, float],
    ) -> Candidate:
        numbers = tuple(sorted(numbers))
        model_mean, model_std, structure_mean, structure_std = stats
        model_score = sum(
            self.number_profiles[number - 1].log_weight for number in numbers
        )
        structure_score = self.structural.score(numbers)
        popularity = self.popularity_penalty(numbers)
        popularity_norm = _clip(popularity / 4.0, 0.0, 1.5)
        total_score = (
            0.55
            * _clip((model_score - model_mean) / model_std, -3.0, 3.0)
            + 0.45
            * _clip((structure_score - structure_mean) / structure_std, -3.0, 3.0)
            - 0.65 * popularity_norm
        )
        return Candidate(
            numbers=numbers,
            model_score=model_score,
            structure_score=structure_score,
            popularity=popularity,
            total_score=total_score,
            quality=_sigmoid(total_score),
            popularity_norm=popularity_norm,
        )

    def _construct_coverage_portfolio(
        self,
        pool: Sequence[Candidate],
        count: int,
        strategy: str,
    ) -> list[Candidate]:
        """
        Construye una cartera que cubre min(54, 5*count) números, no solo los
        que aparecen en los mejores candidatos del pool.

        Para count ≤ 10 (5*count ≤ 50 < 54), la construcción elige siempre
        números no cubiertos, por lo que las apuestas resultantes son disjuntas.
        """
        stats = self._candidate_stats(pool)
        selected: list[Candidate] = []
        selected_numbers: set[tuple[int, ...]] = set()
        covered: set[int] = set()
        appearances: Counter = Counter()
        ordered_profiles = sorted(
            self.number_profiles, key=lambda item: item.weight, reverse=True
        )
        top_numbers = [profile.number for profile in ordered_profiles]

        # Primera apuesta: la de mayor calidad del pool.
        first = max(pool, key=lambda candidate: candidate.quality)
        selected.append(first)
        selected_numbers.add(first.numbers)
        covered.update(first.numbers)
        appearances.update(first.numbers)

        while len(selected) < count:
            missing = [number for number in range(1, POOL_SIZE + 1) if number not in covered]
            slots_left = count - len(selected)

            if not missing:
                # Ya está todo cubierto: completamos con la mejor apuesta que
                # menos solape tenga con lo ya elegido.
                best = max(
                    (
                        candidate
                        for candidate in pool
                        if candidate.numbers not in selected_numbers
                    ),
                    key=lambda candidate: (
                        candidate.quality
                        - 0.15
                        * len(candidate.number_set.intersection(covered))
                    ),
                    default=None,
                )
                if best is None:
                    break
                selected.append(best)
                selected_numbers.add(best.numbers)
                appearances.update(best.numbers)
                continue

            # Números que deben entrar ahora para no quedarnos cortos.
            mandatory = min(
                PICK_SIZE,
                max(0, len(missing) - PICK_SIZE * (slots_left - 1)),
            )
            missing_sorted = sorted(
                missing,
                key=lambda number: (
                    self.number_profiles[number - 1].weight,
                    -appearances[number],
                ),
                reverse=True,
            )
            # Como máximo necesitamos 5 números nuevos por apuesta.
            missing_pool = missing_sorted[: max(PICK_SIZE, 10)]
            variants: list[tuple[int, ...]] = []

            if len(missing_pool) >= PICK_SIZE:
                for combination in combinations(missing_pool, PICK_SIZE):
                    variants.append(tuple(combination))
            else:
                fillers = [
                    number
                    for number in top_numbers
                    if number not in covered and number not in missing_pool
                ][:12]
                if len(fillers) < PICK_SIZE - len(missing_pool):
                    fillers.extend(
                        number
                        for number in sorted(
                            covered, key=lambda item: appearances[item]
                        )
                        if number not in fillers
                    )
                fillers = fillers[:12]
                for combination in combinations(
                    fillers, PICK_SIZE - len(missing_pool)
                ):
                    variants.append(tuple(missing_pool) + tuple(combination))

            if not variants:
                variants.append(tuple(missing_pool[:PICK_SIZE]))

            # Si hay que cubrir obligatoriamente ciertos números, descartamos
            # las variantes que no los incluyan.
            if mandatory:
                required = set(missing_sorted[:mandatory])
                filtered = [
                    variant for variant in variants if required.issubset(variant)
                ]
                if filtered:
                    variants = filtered

            scored_variants = [
                (self._candidate_from_numbers(variant, stats), variant)
                for variant in variants
            ]
            scored_variants.sort(key=lambda item: item[0].quality, reverse=True)
            candidate = next(
                (
                    scored
                    for scored, variant in scored_variants
                    if scored.numbers not in selected_numbers
                ),
                scored_variants[0][0],
            )

            selected.append(candidate)
            selected_numbers.add(candidate.numbers)
            covered.update(candidate.numbers)
            appearances.update(candidate.numbers)

        return selected

    def _disjoint_greedy_portfolio(
        self, pool: Sequence[Candidate], count: int, strategy: str
    ) -> list[Candidate]:
        """Greedy que mantiene siempre apuestas disjuntas (máxima cobertura)."""
        selected: list[Candidate] = []
        used: set[int] = set()
        coverage_target = min(POOL_SIZE, PICK_SIZE * count)

        while len(selected) < count:
            best_candidate: Optional[Candidate] = None
            best_value = -math.inf
            for candidate in pool:
                if candidate.numbers in {item.numbers for item in selected}:
                    continue
                if used.intersection(candidate.number_set):
                    continue
                value = self._objective(
                    [*selected, candidate], strategy, coverage_target
                )
                if value > best_value:
                    best_value = value
                    best_candidate = candidate
            if best_candidate is None:
                break
            selected.append(best_candidate)
            used.update(best_candidate.number_set)

        # Si el greedy se queda sin candidatos disjuntos en el pool, completamos
        # con los mejores números libres. Con count ≤ 10 siempre hay al menos
        # 5 números sin usar, así que la cartera final siempre tiene count
        # apuestas disjuntas.
        if len(selected) < count:
            stats = self._candidate_stats(pool)
            while len(selected) < count:
                available = [
                    number
                    for number in range(1, POOL_SIZE + 1)
                    if number not in used
                ]
                if len(available) < PICK_SIZE:
                    break
                available.sort(
                    key=lambda number: self.number_profiles[number - 1].weight,
                    reverse=True,
                )
                candidate = self._candidate_from_numbers(
                    available[:PICK_SIZE], stats
                )
                selected.append(candidate)
                used.update(candidate.number_set)

        return selected

    def optimize_portfolio(
        self,
        pool: Sequence[Candidate],
        count: int,
        strategy: str,
        enforce_coverage: bool = True,
    ) -> list[Candidate]:
        """Selección greedy + búsqueda local con una cartera disjunta."""
        if count <= 0:
            return []
        if len(pool) < count:
            raise ValueError("No hay suficientes candidatos para generar la cartera")

        coverage_target = min(POOL_SIZE, PICK_SIZE * count) if enforce_coverage else 0
        if enforce_coverage:
            selected = self._construct_coverage_portfolio(pool, count, strategy)
        else:
            selected = self._disjoint_greedy_portfolio(pool, count, strategy)

        # Búsqueda local con sustituciones que preservan la disyunción y la
        # cobertura. Para count=10 solo quedan 9 números libres por posición
        # (54 - 45), así que también exploramos todas las combinaciones
        # posibles de esos 9 números.
        stats = self._candidate_stats(pool)
        base_pool = list(pool[: self.config.local_search_candidates])

        for _ in range(self.config.local_search_passes):
            improved = False
            current_value = self._objective(selected, strategy, coverage_target)
            for index in range(len(selected)):
                others_numbers: set[int] = set()
                for position, item in enumerate(selected):
                    if position != index:
                        others_numbers.update(item.numbers)

                selected_set = {candidate.numbers for candidate in selected}
                candidates_to_try = [
                    candidate
                    for candidate in base_pool
                    if candidate.numbers not in selected_set
                    and not others_numbers.intersection(candidate.number_set)
                ]
                candidates_to_try.sort(key=lambda item: item.quality, reverse=True)
                candidates_to_try = candidates_to_try[:300]

                # Exploración exhaustiva de las combinaciones de números
                # libres cuando el espacio es pequeño (count ≥ 9).
                if count >= 9:
                    available = [
                        number
                        for number in range(1, POOL_SIZE + 1)
                        if number not in others_numbers
                    ]
                    if len(available) <= 12:
                        for combination in combinations(available, PICK_SIZE):
                            candidate = self._candidate_from_numbers(combination, stats)
                            if candidate.numbers not in selected_set:
                                candidates_to_try.append(candidate)

                best_replacement: Optional[Candidate] = None
                best_value = current_value
                for candidate in candidates_to_try:
                    if candidate.numbers in selected_set:
                        continue
                    if others_numbers.intersection(candidate.number_set):
                        continue
                    trial = list(selected)
                    trial[index] = candidate
                    value = self._objective(trial, strategy, coverage_target)
                    if value > best_value + 1e-9:
                        best_value = value
                        best_replacement = candidate
                if best_replacement is not None:
                    selected[index] = best_replacement
                    current_value = best_value
                    improved = True
            if not improved:
                break

        logger.info(
            f"El Gordo: cartera de {len(selected)} combinaciones optimizada "
            f"(estrategia {strategy})"
        )
        return selected

    # ------------------------------------------------------------------
    # Claves y métricas
    # ------------------------------------------------------------------
    def assign_keys(self, count: int) -> list[int]:
        """Asigna claves distintas, priorizando las de mayor probabilidad."""
        ordered = sorted(
            self.key_profiles, key=lambda item: item.probability, reverse=True
        )
        digits = [profile.digit for profile in ordered]
        return [digits[index % len(digits)] for index in range(count)]

    def exact_portfolio_probabilities(
        self, selected: Sequence[Candidate], keys: Sequence[int]
    ) -> Optional[dict]:
        """
        Calcula las probabilidades exactas de cada categoría para una cartera
        de apuestas disjuntas.

        Se enumeran todas las formas de repartir los 5 números ganadores entre
        las apuestas (m_i aciertos) y los números no jugados. Para cada reparto
        y cada una de las 10 claves posibles se determina la mejor categoría.
        """
        count = len(selected)
        if count == 0:
            return None

        number_sets = [candidate.number_set for candidate in selected]
        for left in range(count):
            for right in range(left + 1, count):
                if number_sets[left].intersection(number_sets[right]):
                    return None

        unused = POOL_SIZE - PICK_SIZE * count
        if unused < 0:
            return None

        number_ways = [math.comb(PICK_SIZE, matches) for matches in range(PICK_SIZE + 1)]
        unused_ways = [math.comb(unused, matches) for matches in range(unused + 1)]

        vectors: list[tuple[tuple[int, ...], int]] = []

        def enumerate_vectors(
            index: int,
            remaining: int,
            ways: int,
            current: list[int],
        ) -> None:
            if index == count:
                if 0 <= remaining <= unused:
                    vectors.append((tuple(current), ways * unused_ways[remaining]))
                return
            for matches in range(0, min(PICK_SIZE, remaining) + 1):
                current.append(matches)
                enumerate_vectors(
                    index + 1,
                    remaining - matches,
                    ways * number_ways[matches],
                    current,
                )
                current.pop()

        enumerate_vectors(0, PICK_SIZE, 1, [])

        category_counts: Counter = Counter()
        key_tickets = {
            key: tuple(index for index, ticket_key in enumerate(keys) if ticket_key == key)
            for key in range(KEY_SIZE)
        }

        for vector, ways in vectors:
            for key in range(KEY_SIZE):
                matching = key_tickets[key]
                best_category = 9  # sin premio
                for index, matches in enumerate(vector):
                    if matches == 5:
                        category = 1 if index in matching else 2
                    elif matches == 4:
                        category = 3 if index in matching else 4
                    elif matches == 3:
                        category = 5 if index in matching else 6
                    elif matches == 2:
                        category = 7 if index in matching else 8
                    else:
                        continue
                    if category < best_category:
                        best_category = category
                if best_category <= 8:
                    # Cada clave tiene probabilidad 1/10.
                    category_counts[best_category] += ways / KEY_SIZE

        total = NUMBER_COMBINATIONS
        probabilities = {
            f"prob_{category}": category_counts[category] / total
            for category in range(1, 9)
        }
        prob_any_prize = sum(
            probabilities[f"prob_{category}"] for category in range(1, 9)
        )
        prob_reintegro = len(set(keys)) / KEY_SIZE
        # El reintegro (clave acertada) es compatible con las 8 categorías.
        prob_any_return = 1.0 - (1.0 - prob_any_prize) * (1.0 - prob_reintegro)
        probabilities.update(
            {
                "prob_5_plus": probabilities["prob_1"] + probabilities["prob_2"],
                "prob_4_plus": sum(
                    probabilities[f"prob_{category}"] for category in range(1, 5)
                ),
                "prob_3_plus": sum(
                    probabilities[f"prob_{category}"] for category in range(1, 7)
                ),
                "prob_7_plus": sum(
                    probabilities[f"prob_{category}"] for category in range(1, 8)
                ),
                "prob_2_plus": prob_any_prize,
                "prob_any_prize": prob_any_prize,
                "prob_reintegro": prob_reintegro,
                "prob_any_return": prob_any_return,
                "prob_key_match": prob_reintegro,
                "exact": True,
            }
        )
        return probabilities

    def simulate_portfolio(
        self,
        selected: Sequence[Candidate],
        keys: Sequence[int],
        simulations: int,
        seed: int,
    ) -> dict:
        """Simula sorteos para comprobar las probabilidades de la cartera."""
        simulations = max(1, simulations)
        masks = [
            sum(1 << (number - 1) for number in candidate.numbers)
            for candidate in selected
        ]
        rng = random.Random(seed)
        best_match_distribution = [0] * (PICK_SIZE + 1)
        category_distribution = [0] * 9  # 0 = sin premio, 1..8 categorías
        reintegro_count = 0
        any_return_count = 0

        for _ in range(simulations):
            draw = rng.sample(range(POOL_SIZE), PICK_SIZE)
            draw_mask = 0
            for index in draw:
                draw_mask |= 1 << index
            draw_key = rng.randrange(KEY_SIZE)

            best_matches = 0
            best_category = 9
            for index, ticket_mask in enumerate(masks):
                hits = (draw_mask & ticket_mask).bit_count()
                if hits > best_matches:
                    best_matches = hits
                key_match = keys[index] == draw_key
                if hits == 5:
                    category = 1 if key_match else 2
                elif hits == 4:
                    category = 3 if key_match else 4
                elif hits == 3:
                    category = 5 if key_match else 6
                elif hits == 2:
                    category = 7 if key_match else 8
                else:
                    category = 9
                if category < best_category:
                    best_category = category

            key_hit = any(key == draw_key for key in keys)
            if key_hit:
                reintegro_count += 1
            if best_category <= 8 or key_hit:
                any_return_count += 1

            best_match_distribution[best_matches] += 1
            category_distribution[0 if best_category == 9 else best_category] += 1

        return {
            "simulations": simulations,
            "seed": seed,
            "best_match_distribution": {
                str(hits): round(value / simulations, 8)
                for hits, value in enumerate(best_match_distribution)
            },
            "category_distribution": {
                str(category): round(value / simulations, 8)
                for category, value in enumerate(category_distribution)
            },
            "prob_any_prize": sum(category_distribution[1:]) / simulations,
            "prob_2_plus": sum(category_distribution[1:]) / simulations,
            "prob_3_plus": sum(category_distribution[1:7]) / simulations,
            "prob_4_plus": sum(category_distribution[1:5]) / simulations,
            "prob_5_plus": sum(category_distribution[1:3]) / simulations,
            "prob_reintegro": reintegro_count / simulations,
            "prob_key_match": reintegro_count / simulations,
            "prob_any_return": any_return_count / simulations,
        }

    def portfolio_metrics(
        self,
        selected: Sequence[Candidate],
        keys: Sequence[int],
        simulations: int,
        seed: int,
    ) -> dict:
        count = len(selected)
        numbers: set[int] = set()
        pairs: set[tuple[int, int]] = set()
        triples: set[tuple[int, int, int]] = set()
        appearances: Counter = Counter()
        overlap_values: list[int] = []

        for index, candidate in enumerate(selected):
            numbers.update(candidate.number_set)
            pairs.update(candidate.pair_set)
            triples.update(candidate.triple_set)
            appearances.update(candidate.numbers)
            for other in selected[index + 1 :]:
                overlap_values.append(
                    len(candidate.number_set.intersection(other.number_set))
                )

        distinct_keys = len(set(keys))
        key_probability = distinct_keys / KEY_SIZE
        exact = self.exact_portfolio_probabilities(selected, keys)
        simulation = self.simulate_portfolio(selected, keys, simulations, seed)

        popularity_values = [candidate.popularity_norm for candidate in selected]
        average_popularity = (
            sum(popularity_values) / len(popularity_values)
            if popularity_values
            else 0.0
        )

        if exact is None:
            # Fallback para carteras con solapamiento: usamos simulación y
            # cotas exactas para las categorías altas.
            exact = {
                "prob_1": count * PRIZE_PROBABILITIES["1"],
                "prob_2": count * PRIZE_PROBABILITIES["2"],
                "prob_3": count * PRIZE_PROBABILITIES["3"],
                "prob_4": count * PRIZE_PROBABILITIES["4"],
                "prob_5": count * PRIZE_PROBABILITIES["5"],
                "prob_6": count * PRIZE_PROBABILITIES["6"],
                "prob_7": simulation["category_distribution"].get("7", 0.0),
                "prob_8": simulation["category_distribution"].get("8", 0.0),
                "prob_5_plus": count
                * (PRIZE_PROBABILITIES["1"] + PRIZE_PROBABILITIES["2"]),
                "prob_4_plus": count
                * sum(
                    PRIZE_PROBABILITIES[key] for key in ("1", "2", "3", "4")
                ),
                "prob_3_plus": simulation["prob_3_plus"],
                "prob_7_plus": simulation["prob_3_plus"]
                + simulation["category_distribution"].get("7", 0.0),
                "prob_2_plus": simulation["prob_any_prize"],
                "prob_any_prize": simulation["prob_any_prize"],
                "prob_reintegro": key_probability,
                "prob_any_return": 1.0
                - (1.0 - simulation["prob_any_prize"])
                * (1.0 - key_probability),
                "prob_key_match": key_probability,
                "exact": False,
            }

        jackpot_probability = count / TOTAL_COMBINATIONS
        expected_matches = count * PICK_SIZE * PICK_SIZE / POOL_SIZE
        prob_reintegro = exact.get("prob_reintegro", key_probability)
        prob_any_return = exact.get(
            "prob_any_return",
            1.0
            - (1.0 - exact["prob_any_prize"]) * (1.0 - key_probability),
        )

        return {
            "tickets": count,
            "cost_eur": round(count * 1.5, 2),
            "coverage": {
                "unique_numbers": len(numbers),
                # Porcentaje sobre los 54 números del bombo.
                "numbers_pct": round(100.0 * len(numbers) / POOL_SIZE, 2),
                # Porcentaje sobre el máximo alcanzable con estas apuestas
                # (5 × count; con 10 apuestas, 50 de 54).
                "possible_numbers": min(POOL_SIZE, PICK_SIZE * count),
                "numbers_possible_pct": round(
                    100.0 * len(numbers) / min(POOL_SIZE, PICK_SIZE * count), 2
                ),
                "total_numbers": POOL_SIZE,
                "unique_pairs": len(pairs),
                "pairs_pct": round(100.0 * len(pairs) / (PAIRS_PER_TICKET * count), 2),
                "pairs_total": math.comb(POOL_SIZE, 2),
                "pairs_total_pct": round(
                    100.0 * len(pairs) / math.comb(POOL_SIZE, 2), 2
                ),
                "unique_triples": len(triples),
                "triples_pct": round(
                    100.0 * len(triples) / (TRIPLES_PER_TICKET * count), 2
                ),
                "triples_total": math.comb(POOL_SIZE, 3),
                "triples_total_pct": round(
                    100.0 * len(triples) / math.comb(POOL_SIZE, 3), 2
                ),
            },
            "overlap": {
                "average": round(
                    sum(overlap_values) / len(overlap_values), 3
                ) if overlap_values else 0.0,
                "max": max(overlap_values, default=0),
            },
            "appearance": {
                "max": max(appearances.values(), default=0),
                "min": min(appearances.values(), default=0),
                "distribution": dict(sorted(Counter(appearances.values()).items())),
            },
            "popularity": {
                "average_penalty": round(average_popularity, 4),
                "low_popularity_tickets": sum(
                    1 for value in popularity_values if value <= 0.12
                ),
                "risk": (
                    "bajo"
                    if average_popularity <= 0.1
                    else "medio"
                    if average_popularity <= 0.35
                    else "alto"
                ),
                "explanation": (
                    "Penaliza combinaciones muy jugadas (fechas de nacimiento, "
                    "progresiones o patrones obvios). Cuanto más bajo, menor "
                    "riesgo de compartir un gran premio."
                ),
            },
            "theoretical": {
                "jackpot_probability": jackpot_probability,
                "jackpot_one_in": round(TOTAL_COMBINATIONS / count, 2),
                "prob_1": exact["prob_1"],
                "prob_2": exact["prob_2"],
                "prob_3": exact["prob_3"],
                "prob_4": exact["prob_4"],
                "prob_5": exact["prob_5"],
                "prob_6": exact["prob_6"],
                "prob_7": exact["prob_7"],
                "prob_8": exact["prob_8"],
                "prob_5_plus": exact["prob_5_plus"],
                "prob_4_plus": exact["prob_4_plus"],
                "prob_3_plus": exact["prob_3_plus"],
                "prob_7_plus": exact["prob_7_plus"],
                "prob_2_plus": exact["prob_2_plus"],
                "prob_any_prize": exact["prob_any_prize"],
                "prob_any_prize_one_in": (
                    round(1.0 / exact["prob_any_prize"], 2)
                    if exact["prob_any_prize"] > 0
                    else None
                ),
                "prob_reintegro": prob_reintegro,
                "prob_any_return": prob_any_return,
                "prob_any_return_one_in": (
                    round(1.0 / prob_any_return, 2)
                    if prob_any_return > 0
                    else None
                ),
                "reintegro_eur": TICKET_PRICE_EUR,
                "expected_reintegro_eur": round(
                    key_probability * TICKET_PRICE_EUR, 3
                ),
                "prob_key_match": key_probability,
                "expected_matches": round(expected_matches, 3),
                "expected_tickets_by_tier": {
                    category: round(count * probability, 6)
                    for category, probability in PRIZE_PROBABILITIES.items()
                },
                "single_ticket": {
                    "prob_1": PRIZE_PROBABILITIES["1"],
                    "prob_2": PRIZE_PROBABILITIES["2"],
                    "prob_3": PRIZE_PROBABILITIES["3"],
                    "prob_4": PRIZE_PROBABILITIES["4"],
                    "prob_5": PRIZE_PROBABILITIES["5"],
                    "prob_6": PRIZE_PROBABILITIES["6"],
                    "prob_7": PRIZE_PROBABILITIES["7"],
                    "prob_8": PRIZE_PROBABILITIES["8"],
                    "prob_5_plus": FIVE_PLUS_COUNT / TOTAL_COMBINATIONS,
                    "prob_4_plus": FOUR_PLUS_COUNT / TOTAL_COMBINATIONS,
                    "prob_3_plus": THREE_PLUS_COUNT / TOTAL_COMBINATIONS,
                    "prob_2_plus": TWO_PLUS_COUNT / TOTAL_COMBINATIONS,
                    "prob_reintegro": REINTEGRO_PROBABILITY,
                    "prob_any_return": 1.0
                    - (1.0 - TWO_PLUS_COUNT / TOTAL_COMBINATIONS)
                    * (1.0 - REINTEGRO_PROBABILITY),
                },
                "exact": exact.get("exact", False),
            },
            "simulation": simulation,
            "keys": {
                "digits": list(keys),
                "distinct": distinct_keys,
                "coverage_pct": round(100.0 * distinct_keys / KEY_SIZE, 2),
                "guaranteed_match": distinct_keys == KEY_SIZE,
            },
        }

    # ------------------------------------------------------------------
    # Análisis legible para la API
    # ------------------------------------------------------------------
    def analysis(self) -> dict:
        profiles = self.number_profiles
        hot = sorted(
            profiles,
            key=lambda item: item.recent_lift - item.long_lift,
            reverse=True,
        )[:10]
        cold = sorted(
            profiles,
            key=lambda item: item.recent_lift - item.long_lift,
        )[:10]
        frequent = sorted(profiles, key=lambda item: item.frequency, reverse=True)[:10]
        overdue = sorted(profiles, key=lambda item: item.gap_draws, reverse=True)[:10]

        def serialize(profile: NumberProfile) -> dict:
            return {
                "number": profile.number,
                "frequency": profile.frequency,
                "recent_frequency": round(profile.recent_frequency, 3),
                "last_seen": profile.last_seen.isoformat() if profile.last_seen else None,
                "gap_draws": profile.gap_draws,
                "gap_days": profile.gap_days,
                "long_lift": round(profile.long_lift, 4),
                "recent_lift": round(profile.recent_lift, 4),
                "weight": round(profile.weight, 4),
            }

        return {
            "hot_numbers": [serialize(profile) for profile in hot],
            "cold_numbers": [serialize(profile) for profile in cold],
            "most_frequent_numbers": [serialize(profile) for profile in frequent],
            "overdue_numbers": [serialize(profile) for profile in overdue],
            "top_pairs": [
                {
                    "numbers": [left, right],
                    "frequency": frequency,
                    "lift": round(lift, 4),
                }
                for left, right, frequency, lift in self._top_pairs[:10]
            ],
            "key": [
                {
                    "digit": profile.digit,
                    "frequency": profile.frequency,
                    "probability": round(profile.probability, 5),
                    "last_seen": (
                        profile.last_seen.isoformat() if profile.last_seen else None
                    ),
                    "gap_draws": profile.gap_draws,
                }
                for profile in sorted(
                    self.key_profiles,
                    key=lambda item: item.probability,
                    reverse=True,
                )
            ],
            "structure": self.structural.summary(),
        }

    def dataset_summary(self) -> dict:
        return {
            "total_draws": len(self.draws),
            "date_range": {
                "from": self.draws[0].date.isoformat(),
                "to": self.draws[-1].date.isoformat(),
            },
            "last_draw": {
                "date": self.previous_draw.date.isoformat(),
                "numbers": list(self.previous_draw.numbers),
                "key_number": self.previous_draw.key_number,
            },
            "source": self.previous_draw.source,
            "next_draw": next_gordo_date(self.previous_draw.date).isoformat(),
        }


# ----------------------------------------------------------------------
# Cache del modelo estadístico (los datos cambian como mucho una vez al día)
# ----------------------------------------------------------------------
_model_cache: Optional[GordoModel] = None
_model_cache_key: Optional[tuple] = None
_model_cache_lock = threading.Lock()


def _get_model(draws: Sequence[Draw], config: GordoConfig) -> GordoModel:
    global _model_cache, _model_cache_key

    key = (
        draws[0].date,
        len(draws),
        config.half_life_days,
        config.recent_half_life_days,
        config.recent_window_days,
        config.structural_draws,
    )
    if _model_cache is not None and _model_cache_key == key:
        return _model_cache

    with _model_cache_lock:
        if _model_cache is not None and _model_cache_key == key:
            return _model_cache
        _model_cache = GordoModel(draws, config)
        _model_cache_key = key
        return _model_cache


def get_gordo_model(
    draws: Optional[Sequence[Draw]] = None,
    config: Optional[GordoConfig] = None,
) -> GordoModel:
    """Devuelve el modelo estadístico cacheado para el histórico actual."""
    config = config or GordoConfig()
    if draws is None:
        draws = get_gordo_data_manager().load()
    draws = list(draws)
    if not draws:
        raise ValueError("No hay datos históricos de El Gordo disponibles")
    return _get_model(draws, config)


def _default_seed(last_draw: dt.date, strategy: str, count: int) -> int:
    """Semilla reproducible por sorteo, estrategia y número de apuestas."""
    return (
        last_draw.toordinal() * 1_000_003
        + count * 10_007
        + sum(ord(character) for character in strategy)
    )


def _tags_for_candidate(
    candidate: Candidate,
    selected: Sequence[Candidate],
    key_number: int,
    count: int,
) -> list[str]:
    tags: list[str] = []
    if candidate.quality >= 0.60:
        tags.append("Alta calidad estadística")
    if candidate.popularity_norm <= 0.12:
        tags.append("Poco popular")
    odd_count = sum(1 for number in candidate.numbers if number % 2)
    low_count = sum(1 for number in candidate.numbers if number <= 27)
    if 2 <= odd_count <= 3 and 2 <= low_count <= 3:
        tags.append("Equilibrada")
    if candidate.structure_score >= 0:
        tags.append("Estructura habitual")
    if any(number >= 50 for number in candidate.numbers):
        tags.append("Cubre 50-54")
    if count >= 9:
        tags.append("Cartera de cobertura")
    return tags[:4]


def generate_gordo(
    count: int = 10,
    strategy: str = "big_prize",
    seed: Optional[int] = None,
    draws: Optional[Sequence[Draw]] = None,
    config: Optional[GordoConfig] = None,
) -> dict:
    """
    Genera entre 1 y 10 combinaciones de El Gordo de la Primitiva.

    Args:
        count: número de apuestas (1-10).
        strategy: big_prize | balanced | coverage | statistical.
        seed: semilla para reproducibilidad. Si es None se usa una semilla
            determinista basada en el último sorteo.
        draws: histórico opcional (para tests).
        config: configuración opcional del modelo.
    """
    if not 1 <= count <= 10:
        raise ValueError("El número de combinaciones debe estar entre 1 y 10")
    if strategy not in STRATEGIES:
        raise ValueError(
            f"Estrategia no válida: {strategy}. "
            f"Opciones: {', '.join(STRATEGIES)}"
        )

    config = config or GordoConfig()
    if draws is None:
        draws = get_gordo_data_manager().load()
    draws = list(draws)
    if not draws:
        raise ValueError("No hay datos históricos de El Gordo disponibles")

    model = _get_model(draws, config)
    if seed is None:
        seed = _default_seed(model.previous_draw.date, strategy, count)

    candidates = model.build_candidates(
        seed + sum(ord(character) for character in strategy) * 1_009,
        config.candidate_count,
    )
    pool = model.select_pool(candidates, config.pool_size, count)
    selected = model.optimize_portfolio(
        pool,
        count,
        strategy,
        enforce_coverage=strategy != "statistical",
    )
    keys = model.assign_keys(count)
    metrics = model.portfolio_metrics(
        selected,
        keys,
        simulations=config.simulations,
        seed=seed + 17,
    )

    combinations_payload = []
    for index, (candidate, key_number) in enumerate(zip(selected, keys), start=1):
        numbers = list(candidate.numbers)
        combinations_payload.append(
            {
                "index": index,
                "numbers": numbers,
                "key_number": key_number,
                "quality": round(candidate.quality, 4),
                "total_score": round(candidate.total_score, 4),
                "popularity": round(candidate.popularity_norm, 4),
                "sum": sum(numbers),
                "odd": sum(1 for number in numbers if number % 2),
                "even": sum(1 for number in numbers if number % 2 == 0),
                "low": sum(1 for number in numbers if number <= 27),
                "high": sum(1 for number in numbers if number > 27),
                "consecutive_pairs": _consecutive_pairs(numbers),
                "decades": list(_decade_counts(numbers)),
                "tags": _tags_for_candidate(candidate, selected, key_number, count),
                "theoretical": {
                    "prob_1": PRIZE_PROBABILITIES["1"],
                    "prob_2": PRIZE_PROBABILITIES["2"],
                    "prob_3": PRIZE_PROBABILITIES["3"],
                    "prob_4": PRIZE_PROBABILITIES["4"],
                    "prob_5": PRIZE_PROBABILITIES["5"],
                    "prob_6": PRIZE_PROBABILITIES["6"],
                    "prob_7": PRIZE_PROBABILITIES["7"],
                    "prob_8": PRIZE_PROBABILITIES["8"],
                    "prob_5_plus": FIVE_PLUS_COUNT / TOTAL_COMBINATIONS,
                    "prob_4_plus": FOUR_PLUS_COUNT / TOTAL_COMBINATIONS,
                    "prob_3_plus": THREE_PLUS_COUNT / TOTAL_COMBINATIONS,
                    "prob_2_plus": TWO_PLUS_COUNT / TOTAL_COMBINATIONS,
                    "prob_key": REINTEGRO_PROBABILITY,
                    "prob_reintegro": REINTEGRO_PROBABILITY,
                    "prob_any_return": 1.0
                    - (1.0 - TWO_PLUS_COUNT / TOTAL_COMBINATIONS)
                    * (1.0 - REINTEGRO_PROBABILITY),
                    "reintegro_eur": TICKET_PRICE_EUR,
                },
                "quality_grade": (
                    "alta"
                    if candidate.quality >= 0.60
                    else "media"
                    if candidate.quality >= 0.35
                    else "baja"
                ),
            }
        )

    strategy_meta = STRATEGIES[strategy]
    recommendations = [
        (
            "Con 10 apuestas se cubren las 10 claves posibles: una de ellas "
            "lleva siempre la clave ganadora y recupera 1,50 € de reintegro. "
            "Con menos apuestas se usan claves distintas, priorizando las de "
            "mayor probabilidad histórica."
        ),
        (
            "El reintegro por clave (1,50 €) es compatible con los premios de "
            "las 8 categorías: si la apuesta con la clave acertada suma además "
            "2 o más números, se cobran ambos."
        ),
        (
            "La cartera evita combinaciones populares (fechas, progresiones, "
            "patrones obvios). Si el premio sale en una combinación muy jugada, "
            "se reparte entre más acertantes; esta es la única ventaja real "
            "sobre el azar en premios grandes."
        ),
        (
            "Ninguna estrategia aumenta la probabilidad matemática del primer "
            "premio: cada apuesta sigue siendo 1 entre 31.625.100. La "
            "optimización mejora la cobertura de números, pares y tríos y "
            "reduce el riesgo de compartir el premio."
        ),
        "Juega de forma responsable y solo lo que puedas permitirte perder.",
    ]

    return {
        "game": GAME_INFO,
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "seed": seed,
        "strategy": strategy,
        "strategy_label": strategy_meta["label"],
        "strategy_description": strategy_meta["description"],
        "count": count,
        "dataset": model.dataset_summary(),
        "combinations": combinations_payload,
        "portfolio": metrics,
        "analysis": model.analysis(),
        "model": {
            "type": "statistical-portfolio-optimizer",
            "version": "1.0",
            "candidate_count": config.candidate_count,
            "pool_size": len(pool),
            "model_strength": config.model_strength,
            "half_life_days": config.half_life_days,
            "recent_half_life_days": config.recent_half_life_days,
            "structural_draws": config.structural_draws,
            "simulations": config.simulations,
            "strategies": {
                name: {
                    "label": value["label"],
                    "description": value["description"],
                }
                for name, value in STRATEGIES.items()
            },
        },
        "recommendations": recommendations,
        "disclaimer": (
            "La lotería es un juego de azar. Ningún sistema puede garantizar "
            "premios ni predecir el resultado. Esta herramienta es educativa y "
            "de entretenimiento; juega de forma responsable."
        ),
    }
