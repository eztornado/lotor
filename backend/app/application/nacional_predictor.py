"""
Predictor para el Sorteo Nacional del jueves
"""

from typing import List
from datetime import datetime, timedelta
from loguru import logger
import random
from collections import Counter
import numpy as np

from app.domain.lottery import (
    LotteryType,
    DrawResult,
    PredictionResult,
    LotterySchedule,
    LotteryPredictor
)
from app.ml.lightweight_models import LightweightPredictor as MLModel
from app.infrastructure.data.nacional_source import NacionalDataManager


class NacionalPredictor(LotteryPredictor):
    """Predictor para el Sorteo Nacional (jueves)"""

    def __init__(self):
        super().__init__()
        self.lottery_type = LotteryType.NACIONAL
        self.ml_model = MLModel(model_path="/app/data/processed/nacional_model.joblib")
        self.data_manager = NacionalDataManager()
        self.model_path = "/app/data/processed/nacional_model.joblib"

    def predict(self, historical_data: List[DrawResult]) -> PredictionResult:
        """Realizar predicción para el próximo sorteo del jueves"""

        if not historical_data:
            logger.error("No historical data available for Nacional prediction")
            return self._fallback_prediction()

        # Entrenar modelo si es necesario
        if not self.ml_model.is_trained:
            logger.info("Training ML model for Nacional...")
            self.train(historical_data)

        try:
            # Extraer features específicos para Sorteo Nacional
            features = self._extract_nacional_features(historical_data)

            # Realizar predicción basada en análisis estadístico
            predicted_numbers = self._predict_decimos(historical_data)
            serie, fraccion = self._predict_serie_fraccion(historical_data)

            # Calcular confianza basada en análisis
            confidence = self._calculate_confidence(predicted_numbers, historical_data)

            return PredictionResult(
                lottery_type=self.lottery_type,
                prediction_date=self.get_next_draw_date(),
                predicted_numbers=predicted_numbers,
                additional_predictions=[serie, fraccion],
                confidence=confidence,
                model_used="sklearn_statistical",
                strategy_used="frequency_analysis",
                analysis={
                    'hot_decimos': self._get_hot_decimos(historical_data),
                    'cold_decimos': self._get_cold_decimos(historical_data),
                    'series_frequency': self._get_series_frequency(historical_data),
                    'total_historical_draws': len(historical_data)
                },
                alternative_combinations=self._generate_alternatives(predicted_numbers, serie, fraccion, historical_data)
            )
        except Exception as e:
            logger.error(f"Error in Nacional prediction: {e}")
            return self._fallback_prediction()

    def get_schedule(self) -> LotterySchedule:
        """Sorteo Nacional: jueves"""
        from datetime import timedelta, datetime as dt

        # Calcular próximo jueves directamente aquí
        today = dt.now()
        days_until = (3 - today.weekday()) % 7
        if days_until == 0:
            days_until = 7  # Si hoy es jueves, próximo jueves
        next_draw = today + timedelta(days=days_until)

        return LotterySchedule(
            lottery_type=self.lottery_type,
            draw_day="thursday",
            draw_frequency="weekly",
            next_draw_date=next_draw
        )

    def train(self, historical_data: List[DrawResult]) -> bool:
        """Entrenar modelo con datos históricos de Nacional"""

        try:
            # Para Sorteo Nacional, usamos análisis estadístico más que ML puro
            # debido a la naturaleza de los décimos (números muy grandes)

            # Convertir DrawResult a formato interno
            internal_data = []
            for draw in historical_data:
                internal_data.append({
                    'date': draw.draw_date,
                    'numbers': draw.numbers,
                    'serie': draw.additional_numbers[0] if draw.additional_numbers else 0,
                    'fraccion': draw.additional_numbers[1] if len(draw.additional_numbers) > 1 else 1
                })

            # Guardar estadísticas para predicciones
            self._build_statistical_model(internal_data)
            self.is_trained = True

            logger.info(f"Nacional statistical model built with {len(historical_data)} draws")
            return True

        except Exception as e:
            logger.error(f"Error training Nacional model: {e}")
            return False

    def get_historical_data(self, count: int = 200) -> List[DrawResult]:
        """Obtener datos históricos de Nacional"""
        try:
            return self.data_manager.get_historical_data(count)
        except Exception as e:
            logger.error(f"Error fetching Nacional historical data: {e}")
            return []

    def _extract_nacional_features(self, historical_data: List[DrawResult]) -> np.ndarray:
        """Extraer features específicos para Sorteo Nacional"""

        features = []
        for draw in historical_data[-50:]:  # Últimos 50 sorteos
            # Features para décimos
            feature_vector = [
                len(draw.numbers),                      # Cantidad de números
                sum(draw.numbers) if draw.numbers else 0,  # Suma
                np.mean(draw.numbers) if draw.numbers else 0,  # Media
            ]

            # Features para serie/fracción
            if len(draw.additional_numbers) >= 2:
                feature_vector.extend([
                    draw.additional_numbers[0],  # Serie
                    draw.additional_numbers[1],  # Fracción
                ])
            else:
                feature_vector.extend([0, 1])

            features.append(feature_vector)

        return np.array(features)

    def _predict_decimos(self, historical_data: List[DrawResult]) -> List[int]:
        """Predecir números de décimos basado en frecuencias"""

        # Analizar frecuencias de números en últimos 100 sorteos
        recent_numbers = []
        for draw in historical_data[-100:]:
            recent_numbers.extend(draw.numbers)

        freq = Counter(recent_numbers)

        # Estrategia: 2 números calientes + 1 medio + 1 frío
        hot = [num for num, _ in freq.most_common(20)]
        cold = [num for num, _ in freq.most_common()[-20:]]

        # Seleccionar combinación
        selected = []

        # 2 números calientes
        if len(hot) >= 2:
            selected.extend(random.sample(hot[:10], 2))
        else:
            selected.extend([random.randint(1, 99999) for _ in range(2)])

        # 1 número medio del rango
        selected.append(random.randint(10000, 90000))

        # 1 número frío
        if cold:
            selected.append(random.choice(cold))
        else:
            selected.append(random.randint(1, 99999))

        # Ordenar y retornar 1-3 números
        result = sorted(selected)[:random.randint(1, 3)]

        return result if result else [random.randint(1, 99999)]

    def _predict_serie_fraccion(self, historical_data: List[DrawResult]) -> tuple:
        """Predecir serie y fracción basado en frecuencias"""

        # Analizar frecuencias de series
        series = []
        fracciones = []

        for draw in historical_data[-50:]:
            if len(draw.additional_numbers) >= 2:
                series.append(draw.additional_numbers[0])
                fracciones.append(draw.additional_numbers[1])

        series_freq = Counter(series)
        fraccion_freq = Counter(fracciones)

        # Serie más frecuente
        predicted_serie = series_freq.most_common(1)[0][0] if series_freq else random.randint(1, 10)

        # Fracción: mezcla de frecuencia y aleatoriedad
        if fraccion_freq:
            # 60% fracción frecuente, 40% aleatoria
            if random.random() < 0.6:
                predicted_fraccion = fraccion_freq.most_common(1)[0][0]
            else:
                predicted_fraccion = random.randint(1, 100)
        else:
            predicted_fraccion = random.randint(1, 100)

        return predicted_serie, predicted_fraccion

    def _calculate_confidence(self, predicted_numbers: List[int], historical_data: List[DrawResult]) -> float:
        """Calcular confianza basada en análisis"""

        if not historical_data:
            return 0.35

        # Verificar cuántos números predichos son frecuentes
        recent_numbers = []
        for draw in historical_data[-50:]:
            recent_numbers.extend(draw.numbers)

        freq = Counter(recent_numbers)
        high_freq_count = sum([1 for n in predicted_numbers if freq.get(n, 0) >= 2])

        # Base confidence + bonus por frecuencia
        confidence = 0.40 + (high_freq_count * 0.05)

        return min(confidence, 0.65)

    def _get_hot_decimos(self, historical_data: List[DrawResult], top_n: int = 10) -> List[int]:
        """Obtener décimos más frecuentes"""
        all_numbers = []
        for draw in historical_data[-50:]:
            all_numbers.extend(draw.numbers)

        freq = Counter(all_numbers)
        return [num for num, _ in freq.most_common(top_n)]

    def _get_cold_decimos(self, historical_data: List[DrawResult], top_n: int = 10) -> List[int]:
        """Obtener décimos menos frecuentes"""
        all_numbers = []
        for draw in historical_data[-50:]:
            all_numbers.extend(draw.numbers)

        freq = Counter(all_numbers)
        return [num for num, _ in freq.most_common()[-top_n:]]

    def _get_series_frequency(self, historical_data: List[DrawResult]) -> dict:
        """Obtener frecuencia de series"""
        series = []
        for draw in historical_data[-50:]:
            if draw.additional_numbers:
                series.append(draw.additional_numbers[0])

        freq = Counter(series)
        return {str(k): v for k, v in freq.most_common()}

    def _build_statistical_model(self, internal_data: List[dict]):
        """Construir modelo estadístico para Sorteo Nacional"""
        # Guardar estadísticas para uso en predicciones
        self.statistical_data = {
            'total_draws': len(internal_data),
            'number_frequency': Counter(),
            'serie_frequency': Counter(),
            'fraccion_distribution': []
        }

        for draw in internal_data:
            self.statistical_data['number_frequency'].update(draw.get('numbers', []))
            if 'serie' in draw:
                self.statistical_data['serie_frequency'][draw['serie']] += 1
            if 'fraccion' in draw:
                self.statistical_data['fraccion_distribution'].append(draw['fraccion'])

    def _generate_alternatives(self, main_numbers: List[int], serie: int, fraccion: int,
                              historical_data: List[DrawResult], n: int = 3) -> List[dict]:
        """Generar combinaciones alternativas"""

        alternatives = []
        hot_decimos = self._get_hot_decimos(historical_data)

        for i in range(n):
            # Variar 1 número principal
            alt_numbers = main_numbers.copy()
            if alt_numbers and len(hot_decimos) > 0:
                alt_numbers[0] = random.choice([n for n in hot_decimos if n not in alt_numbers])

            # Variar ligeramente serie/fracción
            alt_serie = (serie + i + 1) % 10
            alt_fraccion = ((fraccion + i * 7) % 100) + 1

            alternatives.append({
                'numbers': alt_numbers,
                'serie': alt_serie,
                'fraccion': alt_fraccion,
                'strategy': 'variation',
                'confidence': 0.35
            })

        return alternatives

    def _fallback_prediction(self) -> PredictionResult:
        """Predicción de fallback si todo falla"""
        return PredictionResult(
            lottery_type=self.lottery_type,
            prediction_date=self.get_next_draw_date(),
            predicted_numbers=[random.randint(1, 99999)],
            additional_predictions=[random.randint(1, 10), random.randint(1, 100)],
            confidence=0.30,
            model_used="fallback",
            strategy_used="random",
            analysis={}
        )