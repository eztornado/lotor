"""
Versión ligera del generador de múltiples combinaciones para ARM
No requiere PyTorch, usa scikit-learn y modelos estadísticos
"""

import numpy as np
from typing import List, Dict
from loguru import logger
import random
from collections import Counter
from dataclasses import dataclass


@dataclass
class Combination:
    """Estructura para una combinación de lotería"""
    numbers: List[int]
    key_number: int
    strategy: str
    confidence: float
    description: str
    risk_level: str


class LightweightMultiCombinationGenerator:
    """Generador ligero de múltiples combinaciones (sin PyTorch)"""

    def __init__(self, statistical_model):
        self.statistical_model = statistical_model
        self.strategies = {
            'statistical': self._statistical_strategy,
            'conservative': self._conservative_strategy,
            'balanced': self._balanced_strategy,
            'risky': self._risky_strategy,
            'random_diverse': self._random_diverse_strategy,
            'pattern_based': self._pattern_based_strategy,
            'optimized_coverage': self._optimized_coverage_strategy
        }

    def generate_weekly_combinations(
        self,
        historical_data: List[dict],
        num_combinations: int = 7
    ) -> List[Combination]:
        """Generar múltiples combinaciones estratégicas"""

        logger.info(f"Generating {num_combinations} lightweight combinations for ARM")

        # Entrenar modelo estadístico si es necesario
        if hasattr(self.statistical_model, 'total_draws') and self.statistical_model.total_draws == 0:
            self.statistical_model.train(historical_data)

        # Generar combinación base
        base_prediction = self.statistical_model.predict(None)
        base_numbers = base_prediction['predicted_numbers']
        base_key = base_prediction['predicted_key_number']

        combinations = []

        # 1. Combinación base (estadística)
        combinations.append(Combination(
            numbers=base_numbers,
            key_number=base_key,
            strategy='statistical',
            confidence=base_prediction.get('confidence', 0.50),
            description="Predicción estadística principal",
            risk_level='balanced'
        ))

        # 2. Combinación conservadora
        combinations.append(self._conservative_strategy(historical_data))

        # 3. Combinación equilibrada
        combinations.append(self._balanced_strategy(historical_data))

        # 4. Combinación arriesgada
        combinations.append(self._risky_strategy(historical_data))

        # 5. Combinación aleatoria diversa
        combinations.append(self._random_diverse_strategy(historical_data))

        # 6. Combinación basada en patrones
        combinations.append(self._pattern_based_strategy(historical_data))

        # 7. Combinación optimizada por cobertura
        combinations.append(self._optimized_coverage_strategy(historical_data, combinations))

        # Validar combinaciones
        valid_combinations = self._validate_combinations(combinations)

        logger.info(f"Generated {len(valid_combinations)} valid combinations")
        return valid_combinations[:num_combinations]

    def _statistical_strategy(self, historical_data: List[dict]) -> Combination:
        """Estrategia estadística pura"""
        prediction = self.statistical_model.predict(None)

        return Combination(
            numbers=prediction['predicted_numbers'],
            key_number=prediction['predicted_key_number'],
            strategy='statistical',
            confidence=prediction.get('confidence', 0.50),
            description="Análisis de frecuencias históricas",
            risk_level='balanced'
        )

    def _conservative_strategy(self, historical_data: List[dict]) -> Combination:
        """Estrategia conservadora: números más calientes"""
        # Obtener frecuencias
        all_numbers = []
        for draw in historical_data:
            all_numbers.extend(draw['numbers'])

        freq_counts = Counter(all_numbers)
        hot_numbers = [num for num, count in freq_counts.most_common(15)]

        # Seleccionar 5 números calientes
        selected = hot_numbers[:5]

        # Número clave más frecuente
        key_numbers = [draw['key_number'] for draw in historical_data]
        key_number = Counter(key_numbers).most_common(1)[0][0]

        return Combination(
            numbers=sorted(selected),
            key_number=key_number,
            strategy='conservative',
            confidence=0.60,
            description="Números calientes (frecuencia histórica alta)",
            risk_level='conservative'
        )

    def _balanced_strategy(self, historical_data: List[dict]) -> Combination:
        """Estrategia equilibrada"""
        all_numbers = []
        for draw in historical_data:
            all_numbers.extend(draw['numbers'])

        freq_counts = Counter(all_numbers)

        # Dividir en tercios
        hot = [num for num, _ in freq_counts.most_common(10)]
        medium = [num for num, _ in freq_counts.most_common(10:30)]
        cold = [num for num, _ in freq_counts.most_common()[-10:]]

        # Mezcla: 2 calientes, 2 medios, 1 frío
        selected = [
            hot[0], hot[1],
            medium[0] if len(medium) > 0 else hot[2],
            medium[1] if len(medium) > 1 else hot[3],
            cold[0] if len(cold) > 0 else hot[4]
        ]

        # Número clave medio
        key_numbers = [draw['key_number'] for draw in historical_data]
        key_counter = Counter(key_numbers)
        key_number = key_counter.most_common(5)[2][0]  # 5to más común

        return Combination(
            numbers=sorted(selected),
            key_number=key_number,
            strategy='balanced',
            confidence=0.55,
            description="Mezcla equilibrada de números",
            risk_level='balanced'
        )

    def _risky_strategy(self, historical_data: List[dict]) -> Combination:
        """Estrategia arriesgada: números fríos"""
        all_numbers = []
        for draw in historical_data:
            all_numbers.extend(draw['numbers'])

        freq_counts = Counter(all_numbers)
        cold_numbers = [num for num, count in freq_counts.most_common()[-15:]]

        # Seleccionar 5 números fríos
        selected = cold_numbers[:5]

        # Número clave menos frecuente
        key_numbers = [draw['key_number'] for draw in historical_data]
        key_number = Counter(key_numbers).most_common()[-1][0]

        return Combination(
            numbers=sorted(selected),
            key_number=key_number,
            strategy='risky',
            confidence=0.35,
            description="Números fríos (alta varianza)",
            risk_level='risky'
        )

    def _random_diverse_strategy(self, historical_data: List[dict]) -> Combination:
        """Estrategia aleatoria diversa"""
        # Obtener distribución para pesos
        all_numbers = []
        for draw in historical_data:
            all_numbers.extend(draw['numbers'])

        freq_counts = Counter(all_numbers)

        # Crear pesos basados en frecuencia inversa (para diversificar)
        weights = {}
        for num in range(1, 55):
            freq = freq_counts.get(num, 0)
            weights[num] = 1.0 / (freq + 1)  # Inversa de frecuencia

        # Seleccionar 5 números con pesos
        numbers = list(weights.keys())
        probs = list(weights.values())
        probs = np.array(probs) / sum(probs)

        selected = np.random.choice(numbers, size=5, replace=False, p=probs)

        # Número clave aleatorio
        key_number = random.randint(0, 9)

        return Combination(
            numbers=sorted(selected),
            key_number=key_number,
            strategy='random_diverse',
            confidence=0.40,
            description="Aleatoria con pesos inversos",
            risk_level='balanced'
        )

    def _pattern_based_strategy(self, historical_data: List[dict]) -> Combination:
        """Estrategia basada en patrones"""
        # Analizar rangos
        range_counts = {'1-18': 0, '19-36': 0, '37-54': 0}
        for draw in historical_data[-30:]:
            for num in draw['numbers']:
                if 1 <= num <= 18:
                    range_counts['1-18'] += 1
                elif 19 <= num <= 36:
                    range_counts['19-36'] += 1
                else:
                    range_counts['37-54'] += 1

        # Seleccionar un número de cada rango
        selected = []
        for range_name in ['1-18', '19-36', '37-54']:
            if range_name == '1-18':
                candidates = list(range(1, 19))
            elif range_name == '19-36':
                candidates = list(range(19, 37))
            else:
                candidates = list(range(37, 55))

            selected.extend(random.sample(candidates, min(2, len(candidates))))
            if len(selected) >= 5:
                break

        # Completar si faltan números
        while len(selected) < 5:
            new_num = random.randint(1, 54)
            if new_num not in selected:
                selected.append(new_num)

        # Número clave basado en recientes
        recent_keys = [draw['key_number'] for draw in historical_data[-10:]]
        key_number = Counter(recent_keys).most_common(1)[0][0]

        return Combination(
            numbers=sorted(selected[:5]),
            key_number=key_number,
            strategy='pattern_based',
            confidence=0.45,
            description="Basada en distribución por rangos",
            risk_level='balanced'
        )

    def _optimized_coverage_strategy(
        self,
        historical_data: List[dict],
        existing_combinations: List[Combination]
    ) -> Combination:
        """Estrategia optimizada para cobertura"""
        # Obtener números usados
        used_numbers = set()
        for combo in existing_combinations:
            used_numbers.update(combo.numbers)

        # Seleccionar números menos usados
        all_numbers_freq = Counter()
        for draw in historical_data:
            all_numbers_freq.update(draw['numbers'])

        # Ordenar por frecuencia y luego por uso
        candidates = []
        for num in range(1, 55):
            freq = all_numbers_freq.get(num, 0)
            used = num in used_numbers
            candidates.append((num, freq, used))

        # Ordenar: baja frecuencia primero, luego no usados
        candidates.sort(key=lambda x: (x[1], x[2]))

        selected = [num for num, _, _ in candidates[:5]]

        # Número clave diferente
        used_keys = [combo.key_number for combo in existing_combinations]
        available_keys = [k for k in range(10) if k not in used_keys]
        key_number = available_keys[0] if available_keys else random.randint(0, 9)

        return Combination(
            numbers=sorted(selected),
            key_number=key_number,
            strategy='optimized_coverage',
            confidence=0.42,
            description="Optimizada para máxima cobertura",
            risk_level='balanced'
        )

    def _validate_combinations(self, combinations: List[Combination]) -> List[Combination]:
        """Validar combinaciones"""
        valid = []

        for combo in combinations:
            # Validar formato
            if len(combo.numbers) != 5:
                continue

            if not all(1 <= num <= 54 for num in combo.numbers):
                continue

            if not 0 <= combo.key_number <= 9:
                continue

            # Verificar duplicados
            if len(set(combo.numbers)) != 5:
                continue

            valid.append(combo)

        return valid

    def calculate_coverage(self, combinations: List[Combination]) -> Dict[str, any]:
        """Calcular métricas de cobertura"""
        # Números únicos cubiertos
        all_numbers = []
        for combo in combinations:
            all_numbers.extend(combo.numbers)

        unique_numbers = len(set(all_numbers))
        total_numbers = 54

        # Solapamiento promedio
        overlaps = []
        for i in range(len(combinations)):
            for j in range(i + 1, len(combinations)):
                overlap = len(set(combinations[i].numbers) & set(combinations[j].numbers))
                overlaps.append(overlap)

        avg_overlap = np.mean(overlaps) if overlaps else 0

        # Distribución de riesgo
        risk_dist = Counter([combo.risk_level for combo in combinations])

        return {
            'unique_numbers_coverage': unique_numbers / total_numbers * 100,
            'avg_combination_overlap': avg_overlap,
            'risk_distribution': dict(risk_dist),
            'total_combinations': len(combinations),
            'numbers_per_combination': 5
        }


def create_lightweight_multi_combination_generator(statistical_model):
    """Crear generador ligero de múltiples combinaciones"""
    return LightweightMultiCombinationGenerator(statistical_model)