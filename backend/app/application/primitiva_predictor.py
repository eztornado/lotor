"""
Predictor específico para El Gordo de la Primitiva
Refactorización del código existente a la nueva arquitectura
"""

from typing import List
from datetime import datetime, timedelta
from loguru import logger

from app.domain.lottery import (
    LotteryType,
    DrawResult,
    PredictionResult,
    LotterySchedule,
    LotteryPredictor
)
from app.ml.lightweight_models import LightweightPredictor as MLModel
from app.services.data_sources import create_data_manager
from app.services.validator import create_validator


class PrimitivaPredictor(LotteryPredictor):
    """Predictor para El Gordo de la Primitiva (domingos)"""

    def __init__(self):
        super().__init__()
        self.lottery_type = LotteryType.PRIMITIVA
        self.ml_model = MLModel(model_path="/app/data/processed/primitiva_model.joblib")
        self.data_manager = create_data_manager()
        self.validator = create_validator()
        self.model_path = "/app/data/processed/primitiva_model.joblib"

    def predict(self, historical_data: List[DrawResult]) -> PredictionResult:
        """Realizar predicción para el próximo sorteo del domingo"""

        if not historical_data:
            logger.error("No historical data available for Primitiva prediction")
            return self._fallback_prediction()

        # Entrenar modelo si es necesario
        if not self.ml_model.is_trained:
            logger.info("Training ML model for Primitiva...")
            self.train(historical_data)

        # Preparar secuencia para predicción
        sequence = self._prepare_sequence(historical_data)

        # Realizar predicción ML
        try:
            ml_prediction = self.ml_model.predict(sequence)

            # Convertir a PredictionResult
            return PredictionResult(
                lottery_type=self.lottery_type,
                prediction_date=self.get_next_draw_date(),
                predicted_numbers=ml_prediction['predicted_numbers'],
                additional_predictions=[ml_prediction['predicted_key_number']],
                confidence=ml_prediction['confidence'],
                model_used=ml_prediction['model_used'],
                strategy_used="ensemble_sklearn",
                analysis={
                    'hot_numbers': self._get_hot_numbers(historical_data),
                    'cold_numbers': self._get_cold_numbers(historical_data),
                    'total_historical_draws': len(historical_data)
                },
                alternative_combinations=ml_prediction.get('alternative_combinations', [])
            )
        except Exception as e:
            logger.error(f"Error in Primitiva prediction: {e}")
            return self._fallback_prediction()

    def get_schedule(self) -> LotterySchedule:
        """El Gordo de la Primitiva: domingos"""
        from datetime import timedelta, datetime as dt

        # Calcular próximo domingo directamente aquí
        today = dt.now()
        days_until = (6 - today.weekday()) % 7
        if days_until == 0:
            days_until = 7  # Si hoy es domingo, próximo domingo
        next_draw = today + timedelta(days=days_until)

        return LotterySchedule(
            lottery_type=self.lottery_type,
            draw_day="sunday",
            draw_frequency="weekly",
            next_draw_date=next_draw
        )

    def train(self, historical_data: List[DrawResult]) -> bool:
        """Entrenar modelo con datos históricos de Primitiva"""

        # Convertir DrawResult a formato interno del ML
        internal_data = []
        for draw in historical_data:
            internal_data.append({
                'date': draw.draw_date,
                'numbers': draw.numbers,
                'key_number': draw.additional_numbers[0] if draw.additional_numbers else 0
            })

        try:
            self.ml_model.train(internal_data)
            self.is_trained = True
            logger.info(f"Primitiva model trained with {len(historical_data)} draws")
            return True
        except Exception as e:
            logger.error(f"Error training Primitiva model: {e}")
            return False

    def get_historical_data(self, count: int = 200) -> List[DrawResult]:
        """Obtener datos históricos de Primitiva"""

        try:
            # Usar data manager existente
            raw_data = self.data_manager.get_historical_data(force_refresh=False, count=count)

            # Convertir a DrawResult
            historical_data = []
            for draw in raw_data:
                historical_data.append(DrawResult(
                    lottery_type=self.lottery_type,
                    draw_date=draw['date'],
                    numbers=draw['numbers'],
                    additional_numbers=[draw['key_number']],
                    metadata={'source': draw.get('source', 'unknown')}
                ))

            return historical_data
        except Exception as e:
            logger.error(f"Error fetching Primitiva historical data: {e}")
            return []

    def _prepare_sequence(self, historical_data: List[DrawResult]) -> List[List[int]]:
        """Preparar secuencia para el modelo ML"""
        sequence = []
        # Ordenar por fecha y tomar los últimos MAX_HISTORY_LENGTH
        sorted_draws = sorted(historical_data, key=lambda x: x.draw_date)[-200:]

        for draw in sorted_draws:
            sequence.append(draw.numbers + draw.additional_numbers)

        return sequence

    def _get_hot_numbers(self, historical_data: List[DrawResult], top_n: int = 10) -> List[int]:
        """Obtener números más frecuentes (calientes)"""
        from collections import Counter

        all_numbers = []
        for draw in historical_data[-50:]:  # Últimos 50 sorteos
            all_numbers.extend(draw.numbers)

        freq = Counter(all_numbers)
        return [num for num, _ in freq.most_common(top_n)]

    def _get_cold_numbers(self, historical_data: List[DrawResult], top_n: int = 10) -> List[int]:
        """Obtener números menos frecuentes (fríos)"""
        from collections import Counter

        all_numbers = []
        for draw in historical_data[-50:]:
            all_numbers.extend(draw.numbers)

        freq = Counter(all_numbers)
        return [num for num, _ in freq.most_common()[-top_n:]]

    def _fallback_prediction(self) -> PredictionResult:
        """Predicción de fallback si todo falla"""
        import random

        return PredictionResult(
            lottery_type=self.lottery_type,
            prediction_date=self.get_next_draw_date(),
            predicted_numbers=sorted(random.sample(range(1, 55), 5)),
            additional_predictions=[random.randint(0, 9)],
            confidence=0.30,
            model_used="fallback",
            strategy_used="random",
            analysis={}
        )