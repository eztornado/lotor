"""
Predictor para el Sorteo Nacional del jueves
Usa sklearn para predecir 4 números por sorteo
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

# Importar sklearn si está disponible
try:
    from sklearn.ensemble import GradientBoostingClassifier
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
    logger.info("sklearn available for Nacional prediction")
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("sklearn not available, using statistical fallback")


class NacionalPredictor(LotteryPredictor):
    """Predictor para el Sorteo Nacional (jueves) con sklearn"""

    def __init__(self):
        super().__init__()
        self.lottery_type = LotteryType.NACIONAL
        self.ml_model = MLModel(model_path="/app/data/processed/nacional_model.joblib")
        self.data_manager = NacionalDataManager()
        self.model_path = "/app/data/processed/nacional_model.joblib"
        self.sklearn_models = {}  # Modelos sklearn para 4 posiciones
        self.scalers = {}  # Scalers para normalización
        self.target_numbers_count = 4  # Siempre predecir 4 números

    def predict(self, historical_data: List[DrawResult]) -> PredictionResult:
        """Realizar predicción para el próximo sorteo del jueves - SIEMPRE 4 números"""

        if not historical_data:
            logger.error("No historical data available for Nacional prediction")
            return self._fallback_prediction()

        # Entrenar modelo si es necesario
        if not self.ml_model.is_trained and SKLEARN_AVAILABLE:
            logger.info("Training sklearn models for Nacional...")
            self.train(historical_data)
        elif not self.is_trained:
            logger.info("Training statistical model for Nacional...")
            self.train(historical_data)

        try:
            # Si sklearn está disponible y los modelos están entrenados
            if SKLEARN_AVAILABLE and self.sklearn_models:
                predicted_numbers = self._predict_with_sklearn(historical_data)
                model_used = "sklearn_gradient_boosting"
                strategy_used = "ml_4_positions"
            else:
                # Fallback a modelo estadístico mejorado
                predicted_numbers = self._predict_decimos_enhanced(historical_data)
                model_used = "enhanced_statistical"
                strategy_used = "frequency_4_numbers"

            # Siempre asegurarnos de tener exactamente 4 números
            while len(predicted_numbers) < 4:
                predicted_numbers.append(random.randint(1, 99999))
            predicted_numbers = sorted(predicted_numbers)[:4]

            serie, fraccion = self._predict_serie_fraccion(historical_data)

            # Calcular confianza basada en análisis
            confidence = self._calculate_confidence_enhanced(predicted_numbers, historical_data)

            return PredictionResult(
                lottery_type=self.lottery_type,
                prediction_date=self.get_next_draw_date(),
                predicted_numbers=predicted_numbers,  # SIEMPRE 4 números
                additional_predictions=[serie, fraccion],
                confidence=confidence,
                model_used=model_used,
                strategy_used=strategy_used,
                analysis={
                    'hot_decimos': self._get_hot_decimos(historical_data),
                    'cold_decimos': self._get_cold_decimos(historical_data),
                    'series_frequency': self._get_series_frequency(historical_data),
                    'total_historical_draws': len(historical_data),
                    'prediction_count': len(predicted_numbers),
                    'target_numbers': 4
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
        """Entrenar modelo con datos históricos de Nacional - sklearn si disponible"""

        try:
            # Convertir DrawResult a formato interno
            internal_data = []
            for draw in historical_data:
                internal_data.append({
                    'date': draw.draw_date,
                    'numbers': draw.numbers,
                    'serie': draw.additional_numbers[0] if draw.additional_numbers else 0,
                    'fraccion': draw.additional_numbers[1] if len(draw.additional_numbers) > 1 else 1
                })

            # Guardar estadísticas para predicciones (siempre)
            self._build_statistical_model(internal_data)

            # Si sklearn está disponible, entrenar modelos ML
            if SKLEARN_AVAILABLE and len(internal_data) >= 20:
                self._train_sklearn_models(internal_data)
                logger.info(f"Nacional sklearn models trained with {len(historical_data)} draws")
            else:
                logger.info(f"Nacional statistical model built with {len(historical_data)} draws")

            self.is_trained = True
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
                              historical_data: List[DrawResult], n: int = 3) -> List[List[int]]:
        """Generar combinaciones alternativas"""

        alternatives = []
        hot_decimos = self._get_hot_decimos(historical_data)

        for i in range(n):
            # Variar 1 número principal
            alt_numbers = main_numbers.copy()
            if alt_numbers and len(hot_decimos) > 0:
                alt_numbers[0] = random.choice([n for n in hot_decimos if n not in alt_numbers])

            alternatives.append(sorted(alt_numbers))

        return alternatives

    def _train_sklearn_models(self, internal_data: List[dict]):
        """Entrenar modelos sklearn para 4 posiciones de números"""
        logger.info("Training sklearn models for Nacional - 4 number positions...")

        # Preparar datos para entrenamiento - asegurar 4 números por sorteo
        training_sequences = []
        for draw in internal_data:
            # Normalizar a exactamente 4 números
            numbers = draw.get('numbers', [])
            while len(numbers) < 4:
                numbers.append(random.randint(1, 99999))
            numbers = sorted(numbers)[:4]
            draw['numbers'] = numbers
            training_sequences.append(draw)

        # Crear secuencias para entrenamiento
        X_features = []
        y_positions = [[], [], [], []]  # 4 posiciones

        for i in range(len(training_sequences) - 1):
            current_draw = training_sequences[i]
            next_draw = training_sequences[i + 1]

            # Features del sorteo actual
            features = self._extract_enhanced_features(current_draw, training_sequences[:i+1])
            X_features.append(features)

            # Targets (4 números del próximo sorteo)
            for pos in range(4):
                y_positions[pos].append(next_draw['numbers'][pos])

        X_features = np.array(X_features)

        # Escalar features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X_features)
        self.scalers['features'] = scaler

        # Entrenar modelo para cada una de las 4 posiciones
        for pos in range(4):
            y_pos = y_positions[pos]

            # Usar GradientBoosting para mejor precisión
            gb_model = GradientBoostingClassifier(
                n_estimators=100,  # Ajustado para números grandes
                max_depth=5,      # Profundidad moderada
                learning_rate=0.05,
                min_samples_split=3,
                subsample=0.8,
                random_state=42
            )

            gb_model.fit(X_scaled, y_pos)
            self.sklearn_models[f'position_{pos}'] = gb_model

            logger.info(f"  Position {pos} model trained - {len(set(y_pos))} unique values")

        logger.info("✅ All 4 sklearn models trained for Nacional")

    def _extract_enhanced_features(self, draw: dict, historical_context: List[dict] = None) -> List[float]:
        """Extraer features mejorados para sklearn"""
        numbers = sorted(draw.get('numbers', []))

        # Features básicos
        basic = [
            len(numbers),  # Cantidad de números (debería ser 4)
            sum(numbers) if numbers else 0,  # Suma
            np.mean(numbers) if numbers else 0,  # Media
            np.std(numbers) if len(numbers) > 1 else 0,  # Desviación
            min(numbers) if numbers else 0,  # Mínimo
            max(numbers) if numbers else 0,  # Máximo
            (max(numbers) - min(numbers)) if numbers else 0,  # Rango
        ]

        # Features de posición (para 4 números)
        if len(numbers) >= 4:
            position_features = [
                numbers[0] if len(numbers) > 0 else 0,  # Posición 1
                numbers[1] if len(numbers) > 1 else 0,  # Posición 2
                numbers[2] if len(numbers) > 2 else 0,  # Posición 3
                numbers[3] if len(numbers) > 3 else 0,  # Posición 4
                numbers[0] % 10 if len(numbers) > 0 else 0,  # Último dígito posición 1
                numbers[1] % 10 if len(numbers) > 1 else 0,  # Último dígito posición 2
                numbers[2] % 10 if len(numbers) > 2 else 0,  # Último dígito posición 3
                numbers[3] % 10 if len(numbers) > 3 else 0,  # Último dígito posición 4
            ]
        else:
            position_features = [0] * 8

        # Features temporales
        date = draw.get('date')
        temporal = [
            date.weekday() if date else 3,  # Día de la semana (jueves=3)
            date.month if date else 8,  # Mes
            date.day if date else 1,   # Día del mes
        ]

        # Features contextuales si hay historial
        context = []
        if historical_context and len(historical_context) > 1:
            recent_numbers = []
            for h in historical_context[-10:]:
                recent_numbers.extend(h.get('numbers', []))

            if recent_numbers:
                freq = Counter(recent_numbers)
                overlap = sum([1 for n in numbers if freq.get(n, 0) >= 2])
                context.extend([
                    overlap,  # Números frecuentes que se repiten
                    len(set(numbers) & set(recent_numbers[-4:] if len(recent_numbers) >= 4 else recent_numbers)),  # Overlap reciente
                ])
            else:
                context = [0, 0]
        else:
            context = [0, 0]

        # Features de serie y fracción
        serie_features = [
            draw.get('serie', 0),  # Serie
            draw.get('fraccion', 1),  # Fracción
        ]

        return basic + position_features + temporal + context + serie_features

    def _predict_with_sklearn(self, historical_data: List[DrawResult]) -> List[int]:
        """Predecir usando modelos sklearn - siempre 4 números"""
        try:
            # Preparar datos del último sorteo
            internal_data = []
            for draw in historical_data:
                internal_data.append({
                    'date': draw.draw_date,
                    'numbers': draw.numbers,
                    'serie': draw.additional_numbers[0] if draw.additional_numbers else 0,
                    'fraccion': draw.additional_numbers[1] if len(draw.additional_numbers) > 1 else 1
                })

            last_draw = internal_data[-1]

            # Extraer features
            features = np.array([self._extract_enhanced_features(last_draw, internal_data[:-1])])

            # Escalar si está disponible
            if 'features' in self.scalers:
                features = self.scalers['features'].transform(features)

            # Predecir 4 números
            predicted_numbers = []
            for pos in range(4):
                model = self.sklearn_models.get(f'position_{pos}')
                if model:
                    pred = model.predict(features)[0]
                    predicted_numbers.append(int(pred))
                else:
                    predicted_numbers.append(random.randint(1, 99999))

            return sorted(predicted_numbers)

        except Exception as e:
            logger.error(f"Error in sklearn prediction: {e}")
            return self._predict_decimos_enhanced(historical_data)

    def _predict_decimos_enhanced(self, historical_data: List[DrawResult]) -> List[int]:
        """Predicción estadística mejorada - siempre 4 números"""
        # Analizar frecuencias de números en últimos 100 sorteos
        recent_numbers = []
        for draw in historical_data[-100:]:
            recent_numbers.extend(draw.numbers)

        freq = Counter(recent_numbers)

        # Estrategia mejorada: 2 calientes + 1 medio + 1 estratégico
        hot = [num for num, _ in freq.most_common(20)]
        cold = [num for num, _ in freq.most_common()[-20:]]

        selected = []

        # 2 números calientes
        if len(hot) >= 2:
            selected.extend(random.sample(hot[:10], 2))
        else:
            selected.extend([random.randint(1, 99999) for _ in range(2)])

        # 1 número medio del rango
        selected.append(random.randint(10000, 90000))

        # 1 número estratégico (frío pero no extremo)
        if cold and len(cold) > 5:
            selected.append(random.choice(cold[5:15]))  # Fríos medios
        else:
            selected.append(random.randint(20000, 80000))

        # SIEMPRE retornar exactamente 4 números
        result = sorted(selected)[:4]

        # Asegurar que tengamos 4 números
        while len(result) < 4:
            result.append(random.randint(1, 99999))

        return result

    def _calculate_confidence_enhanced(self, predicted_numbers: List[int], historical_data: List[DrawResult]) -> float:
        """Calcular confianza mejorada para 4 números"""
        if not historical_data:
            return 0.35

        # Verificar cuántos números predichos son frecuentes
        recent_numbers = []
        for draw in historical_data[-50:]:
            recent_numbers.extend(draw.numbers)

        freq = Counter(recent_numbers)
        high_freq_count = sum([1 for n in predicted_numbers if freq.get(n, 0) >= 2])

        # Base confidence + bonus por frecuencia + bonus por 4 números
        confidence = 0.45 + (high_freq_count * 0.04) + 0.05  # Bonus por 4 números

        # Ajustar según distribución de rangos
        range_distribution = [
            sum([1 for n in predicted_numbers if n <= 25000]),
            sum([1 for n in predicted_numbers if 25000 < n <= 50000]),
            sum([1 for n in predicted_numbers if 50000 < n <= 75000]),
            sum([1 for n in predicted_numbers if n > 75000])
        ]

        # Bonificación si está bien distribuido en rangos
        if all([c >= 1 for c in range_distribution]) and sum(range_distribution) == 4:
            confidence += 0.08

        return min(confidence, 0.72)  # Máximo 72% para 4 números

    def _fallback_prediction(self) -> PredictionResult:
        """Predicción de fallback - siempre 4 números"""
        # Generar 4 números aleatorios optimizados
        predicted_numbers = sorted([random.randint(1, 99999) for _ in range(4)])

        return PredictionResult(
            lottery_type=self.lottery_type,
            prediction_date=self.get_next_draw_date(),
            predicted_numbers=predicted_numbers,  # SIEMPRE 4 números
            additional_predictions=[random.randint(1, 10), random.randint(1, 100)],
            confidence=0.30,
            model_used="fallback",
            strategy_used="random_4_numbers",
            analysis={
                'prediction_count': 4,
                'target_numbers': 4,
                'note': 'Fallback prediction with exactly 4 numbers'
            }
        )