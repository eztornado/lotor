# Importación condicional de PyTorch
try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False
    # Creamos un mock simple de torch para las funciones que necesitamos
    class torch:
        @staticmethod
        def tensor(data, dtype=None):
            return data

import numpy as np
from typing import List, Dict, Tuple, Optional
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
    risk_level: str  # 'conservative', 'balanced', 'risky'


class MultiCombinationGenerator:
    """Generador de múltiples combinaciones estratégicas"""

    def __init__(self, ensemble_model, statistical_model):
        self.ensemble_model = ensemble_model
        self.statistical_model = statistical_model
        # Estrategias disponibles (código eliminado - no se usa en generate_weekly_combinations)

    def generate_weekly_combinations(
        self,
        sequence: List[List[int]],
        num_combinations: int = 7
    ) -> List[Combination]:
        """
        Generar múltiples combinaciones para un sorteo semanal

        Args:
            sequence: Secuencia de sorteos históricos
            num_combinations: Número de combinaciones a generar (default: 7)

        Returns:
            Lista de Combination objects
        """
        logger.info(f"Generating {num_combinations} strategic combinations for weekly play")

        # Obtener predicción base del ensemble
        base_prediction = self.ensemble_model.predict(sequence)
        base_numbers = base_prediction['predicted_numbers']
        base_key = base_prediction['predicted_key_number']
        base_probs = np.array(base_prediction['number_probabilities'])

        combinations = []

        # 1. Combinación Principal (Ensemble)
        combinations.append(Combination(
            numbers=base_numbers,
            key_number=base_key,
            strategy='ensemble',
            confidence=base_prediction['confidence'],
            description="Predicción principal del ensemble ML",
            risk_level='balanced'
        ))

        # 2. Combinación Conservadora (Números Calientes)
        hot_combo = self._conservative_strategy(sequence, base_probs)
        combinations.append(hot_combo)

        # 3. Combinación Equilibrada
        balanced_combo = self._balanced_strategy(sequence, base_probs)
        combinations.append(balanced_combo)

        # 4. Combinación Arriesgada (Números Fríos)
        risky_combo = self._risky_strategy(sequence, base_probs)
        combinations.append(risky_combo)

        # 5. Combinación basada en Patrones
        pattern_combo = self._pattern_strategy(sequence, base_probs)
        combinations.append(pattern_combo)

        # 6. Combinación Aleatoria Optimizada
        random_combo = self._random_optimized_strategy(sequence, base_probs)
        combinations.append(random_combo)

        # 7. Combinación Diversificada (Mínimo solapamiento)
        div_combo = self._diversified_strategy(sequence, base_probs, existing_combinations=combinations)
        combinations.append(div_combo)

        # Validar y limpiar combinaciones
        valid_combinations = self._validate_combinations(combinations)

        logger.info(f"Generated {len(valid_combinations)} valid combinations out of {num_combinations} requested")
        return valid_combinations[:num_combinations]

    def _conservative_strategy(self, sequence: List[List[int]], base_probs: np.ndarray) -> Combination:
        """Estrategia conservadora: números calientes + alta probabilidad"""
        # Obtener números más frecuentes
        all_numbers = []
        for draw in sequence:
            all_numbers.extend(draw[:5])  # Solo números principales

        freq_counts = Counter(all_numbers)
        hot_numbers = [num for num, count in freq_counts.most_common(15)]

        # Combinar con probabilidades del modelo
        combined_scores = {}
        for num in range(1, 55):
            freq_score = freq_counts.get(num, 0)
            prob_score = base_probs[num - 1] if num <= len(base_probs) else 0

            # Peso mayor a frecuencia (conservadora)
            combined_scores[num] = (freq_score * 0.7) + (prob_score * 0.3)

        # Seleccionar top-5
        selected = sorted(combined_scores.keys(), key=lambda x: combined_scores[x], reverse=True)[:5]

        # Número clave más frecuente
        key_numbers = [draw[5] for draw in sequence if len(draw) > 5]
        key_number = Counter(key_numbers).most_common(1)[0][0]

        return Combination(
            numbers=selected,
            key_number=key_number,
            strategy='conservative',
            confidence=0.65,
            description="Números calientes (históricamente más frecuentes)",
            risk_level='conservative'
        )

    def _balanced_strategy(self, sequence: List[List[int]], base_probs: np.ndarray) -> Combination:
        """Estrategia equilibrada: mezcla de calientes y fríos"""
        # Obtener estadísticas
        all_numbers = []
        for draw in sequence:
            all_numbers.extend(draw[:5])

        freq_counts = Counter(all_numbers)

        # Dividir en calientes (top 10) y fríos (bottom 10)
        hot = [num for num, _ in freq_counts.most_common(10)]
        cold = [num for num, _ in freq_counts.most_common()[-10:]]

        # Mezcla: 2 calientes, 2 medios, 1 frío
        medium = [num for num in range(1, 55) if num not in hot and num not in cold]
        random.shuffle(medium)

        selected = [
            hot[0], hot[1],  # 2 calientes
            medium[0], medium[1],  # 2 medios
            cold[0]  # 1 frío
        ]

        # Número clave medio
        key_numbers = [draw[5] for draw in sequence if len(draw) > 5]
        key_counts = Counter(key_numbers)
        medium_keys = [k for k in range(10) if k not in [k for k, _ in key_counts.most_common(3)]]
        key_number = medium_keys[0] if medium_keys else key_counts.most_common(1)[0][0]

        return Combination(
            numbers=sorted(selected),
            key_number=key_number,
            strategy='balanced',
            confidence=0.55,
            description="Mezcla equilibrada de números calientes y fríos",
            risk_level='balanced'
        )

    def _risky_strategy(self, sequence: List[List[int]], base_probs: np.ndarray) -> Combination:
        """Estrategia arriesgada: números fríos + baja probabilidad"""
        # Obtener números menos frecuentes
        all_numbers = []
        for draw in sequence:
            all_numbers.extend(draw[:5])

        freq_counts = Counter(all_numbers)
        cold_numbers = [num for num, count in freq_counts.most_common()[-15:]]

        # Combinar con probabilidades bajas del modelo
        combined_scores = {}
        for num in range(1, 55):
            freq_score = freq_counts.get(num, 0)
            prob_score = base_probs[num - 1] if num <= len(base_probs) else 0

            # Peso mayor a baja frecuencia (arriesgada)
            combined_scores[num] = (freq_score * 0.3) + ((1 - prob_score) * 0.7)

        # Seleccionar top-5 (que serán los de menor frecuencia/probabilidad)
        selected = sorted(combined_scores.keys(), key=lambda x: combined_scores[x], reverse=True)[:5]

        # Número clave menos frecuente
        key_numbers = [draw[5] for draw in sequence if len(draw) > 5]
        key_number = Counter(key_numbers).most_common()[-1][0]

        return Combination(
            numbers=selected,
            key_number=key_number,
            strategy='risky',
            confidence=0.35,
            description="Números fríos (históricamente menos frecuentes)",
            risk_level='risky'
        )

    def _pattern_strategy(self, sequence: List[List[int]], base_probs: np.ndarray) -> Combination:
        """Estrategia basada en patrones históricos"""
        # Analizar patrones consecutivos
        consecutive_pairs = Counter()
        for draw in sequence[-20:]:  # Últimos 20 sorteos
            nums = sorted(draw[:5])
            for i in range(len(nums) - 1):
                if nums[i + 1] - nums[i] == 1:
                    consecutive_pairs[(nums[i], nums[i + 1])] += 1

        # Analizar distribución por rangos
        range_counts = {'1-18': 0, '19-36': 0, '37-54': 0}
        for draw in sequence[-30:]:
            for num in draw[:5]:
                if 1 <= num <= 18:
                    range_counts['1-18'] += 1
                elif 19 <= num <= 36:
                    range_counts['19-36'] += 1
                else:
                    range_counts['37-54'] += 1

        # Seleccionar basado en patrones
        selected = []
        used_ranges = set()

        # 1 número de rango más frecuente
        most_common_range = max(range_counts, key=range_counts.get)
        candidates = [n for n in range(1, 55) if self._in_range(n, most_common_range)]
        selected.append(random.choice(candidates))
        used_ranges.add(most_common_range)

        # 2 números de rango medio
        for range_name in ['1-18', '19-36', '37-54']:
            if range_name not in used_ranges:
                candidates = [n for n in range(1, 55) if self._in_range(n, range_name)]
                selected.extend(random.sample(candidates, min(2, len(candidates))))
                used_ranges.add(range_name)
                break

        # Completar hasta 5
        while len(selected) < 5:
            candidates = [n for n in range(1, 55) if n not in selected]
            selected.append(random.choice(candidates))

        # Número clave basado en patrones recientes
        recent_keys = [draw[5] for draw in sequence[-10:] if len(draw) > 5]
        key_number = Counter(recent_keys).most_common(1)[0][0]

        return Combination(
            numbers=sorted(selected[:5]),
            key_number=key_number,
            strategy='pattern_based',
            confidence=0.50,
            description="Basada en patrones de rangos y consecutivos",
            risk_level='balanced'
        )

    def _random_optimized_strategy(self, sequence: List[List[int]], base_probs: np.ndarray) -> Combination:
        """Estrategia aleatoria optimizada"""
        # Usar probabilidades del modelo como pesos
        weights = base_probs.copy()
        weights = weights / weights.sum()  # Normalizar

        # Seleccionar 5 números sin reemplazo usando pesos
        selected = []
        available_numbers = list(range(1, 55))
        available_weights = weights[:54].copy()

        for _ in range(5):
            # Seleccionar número basado en pesos
            chosen_idx = np.random.choice(len(available_numbers), p=available_weights / available_weights.sum())
            chosen = available_numbers.pop(chosen_idx)
            selected.append(chosen)
            available_weights = np.delete(available_weights, chosen_idx - 1 if chosen_idx > 0 else 0)

        # Número clave aleatorio ponderado
        key_probs = np.array([sequence[-i-1][5] if len(sequence[-i-1]) > 5 else 0
                              for i in range(min(20, len(sequence)))])
        if len(key_probs) > 0:
            key_counter = Counter(key_probs)
            key_number = random.choice([k for k, c in key_counter.most_common(4)])
        else:
            key_number = random.randint(0, 9)

        return Combination(
            numbers=sorted(selected),
            key_number=key_number,
            strategy='random_optimized',
            confidence=0.45,
            description="Aleatoria optimizada con pesos probabilísticos",
            risk_level='balanced'
        )

    def _diversified_strategy(
        self,
        sequence: List[List[int]],
        base_probs: np.ndarray,
        existing_combinations: List[Combination]
    ) -> Combination:
        """Estrategia diversificada: mínimo solapamiento con combinaciones existentes"""
        # Obtener todos los números usados en combinaciones existentes
        used_numbers = set()
        for combo in existing_combinations:
            used_numbers.update(combo.numbers)

        # Seleccionar números con menor solapamiento
        available_numbers = [n for n in range(1, 55) if n not in used_numbers]

        if len(available_numbers) < 5:
            # Si no suficientes, usar los menos usados
            number_usage = Counter()
            for combo in existing_combinations:
                for num in combo.numbers:
                    number_usage[num] += 1

            available_numbers = sorted(range(1, 55), key=lambda x: number_usage.get(x, 0))[:10]

        # Seleccionar top-5 disponibles
        selected = available_numbers[:5]

        # Número clave diferente
        used_keys = [combo.key_number for combo in existing_combinations]
        available_keys = [k for k in range(10) if k not in used_keys]
        key_number = available_keys[0] if available_keys else (max(used_keys) + 1) % 10

        return Combination(
            numbers=sorted(selected),
            key_number=key_number,
            strategy='diversified',
            confidence=0.40,
            description="Combinación diversificada (mínimo solapamiento)",
            risk_level='balanced'
        )

    def _in_range(self, num: int, range_str: str) -> bool:
        """Verificar si número está en rango"""
        if range_str == '1-18':
            return 1 <= num <= 18
        elif range_str == '19-36':
            return 19 <= num <= 36
        elif range_str == '37-54':
            return 37 <= num <= 54
        return False

    def _validate_combinations(self, combinations: List[Combination]) -> List[Combination]:
        """Validar y limpiar combinaciones"""
        valid = []

        for combo in combinations:
            # Validar formato
            if len(combo.numbers) != 5:
                logger.warning(f"Invalid combination length: {len(combo.numbers)}")
                continue

            if not all(1 <= num <= 54 for num in combo.numbers):
                logger.warning(f"Numbers out of range: {combo.numbers}")
                continue

            if not 0 <= combo.key_number <= 9:
                logger.warning(f"Key number out of range: {combo.key_number}")
                continue

            # Verificar duplicados
            if len(set(combo.numbers)) != 5:
                logger.warning(f"Duplicate numbers: {combo.numbers}")
                continue

            valid.append(combo)

        return valid

    def calculate_coverage(self, combinations: List[Combination]) -> Dict[str, any]:
        """Calcular métricas de cobertura de las combinaciones"""
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

        avg_overlap = float(np.mean(overlaps)) if overlaps else 0.0

        # Distribución de riesgo
        risk_dist = Counter([combo.risk_level for combo in combinations])

        return {
            'unique_numbers_coverage': float(unique_numbers / total_numbers * 100),
            'avg_combination_overlap': avg_overlap,
            'risk_distribution': dict(risk_dist),
            'total_combinations': len(combinations),
            'numbers_per_combination': 5
        }


def create_multi_combination_generator(ensemble_model, statistical_model) -> MultiCombinationGenerator:
    """Crear generador de múltiples combinaciones"""
    return MultiCombinationGenerator(ensemble_model, statistical_model)