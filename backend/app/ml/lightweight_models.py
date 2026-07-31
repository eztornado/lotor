"""
Modelos ligeros para Raspberry Pi (sin PyTorch)
Usa scikit-learn y XGBoost en lugar de PyTorch
"""

import numpy as np
from typing import List, Dict, Optional
from loguru import logger
from collections import Counter
import random
from pathlib import Path
import hashlib
import joblib

try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    logger.warning("XGBoost not available, using fallback")

try:
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("Scikit-learn not available, using statistical fallback")


class LightweightPredictor:
    """Predictor ligero sin PyTorch para dispositivos ARM"""

    def __init__(self, model_path: Optional[str] = None):
        self.models = {}
        self.scalers = {}
        self.is_trained = False
        self.model_path = model_path or "/app/data/processed/lightweight_model.joblib"
        self.training_data_hash = None

        # Intentar cargar modelo existente
        self._load_model()

    def _get_data_hash(self, historical_data: List[dict]) -> str:
        """Calcular hash de los datos para detectar cambios"""
        # Usar fecha del último sorteo como identificador
        if historical_data:
            last_date = str(max([d['date'] for d in historical_data if d.get('date')]))
            count = len(historical_data)
            return hashlib.md5(f"{last_date}_{count}".encode()).hexdigest()
        return ""

    def _save_model(self):
        """Guardar modelo entrenado a disco"""
        try:
            model_dir = Path(self.model_path).parent
            model_dir.mkdir(parents=True, exist_ok=True)

            model_data = {
                'models': self.models,
                'scalers': self.scalers,
                'is_trained': self.is_trained,
                'training_data_hash': self.training_data_hash,
                'sklearn_version': SKLEARN_AVAILABLE
            }

            joblib.dump(model_data, self.model_path)
            logger.info(f"Model saved to {self.model_path}")
        except Exception as e:
            logger.warning(f"Could not save model: {e}")

    def _load_model(self):
        """Cargar modelo entrenado desde disco"""
        try:
            if not Path(self.model_path).exists():
                logger.info("No saved model found, will train from scratch")
                return False

            model_data = joblib.load(self.model_path)

            # Verificar compatibilidad
            if model_data.get('sklearn_version') != SKLEARN_AVAILABLE:
                logger.warning("Saved model incompatible, will retrain")
                return False

            self.models = model_data['models']
            self.scalers = model_data['scalers']
            self.is_trained = model_data['is_trained']
            self.training_data_hash = model_data.get('training_data_hash')

            logger.info(f"Model loaded from {self.model_path}")
            return True
        except Exception as e:
            logger.warning(f"Could not load model: {e}")
            return False

    def train(self, historical_data: List[dict], force_retrain: bool = False):
        """Entrenar con datos históricos"""
        # Verificar si necesitamos reentrenar
        new_data_hash = self._get_data_hash(historical_data)

        if not force_retrain and self.is_trained and self.training_data_hash == new_data_hash:
            logger.info("Model already trained with current data, skipping training")
            return True

        logger.info("Training lightweight ML models...")

        if not historical_data:
            logger.error("No historical data available")
            return False

        # Preparar datos para entrenamiento
        X_numbers, X_keys, y_numbers, y_keys = self._prepare_training_data(historical_data)

        if SKLEARN_AVAILABLE:
            self._train_sklearn_models(X_numbers, X_keys, y_numbers, y_keys)
        elif XGBOOST_AVAILABLE:
            self._train_xgboost_models(X_numbers, X_keys, y_numbers, y_keys)
        else:
            logger.warning("No ML libraries available, using statistical models only")
            self._train_statistical_models(historical_data)

        self.is_trained = True
        self.training_data_hash = new_data_hash

        # Guardar modelo entrenado
        self._save_model()

        return True

    def _prepare_training_data(self, historical_data: List[dict]):
        """Preparar datos para entrenamiento con features mejorados"""
        X_numbers = []
        X_keys = []
        y_numbers = []
        y_keys = []

        # Crear secuencias para entrenamiento
        for i in range(len(historical_data) - 1):
            current_draw = historical_data[i]
            next_draw = historical_data[i + 1]

            # Features del sorteo actual con contexto
            features = self._extract_features(current_draw, historical_data[:i+1])

            # Targets (próximo sorteo)
            targets_numbers = next_draw['numbers']
            target_key = next_draw['key_number']

            X_numbers.append(features)
            X_keys.append(features)
            y_numbers.append(targets_numbers)
            y_keys.append(target_key)

        return np.array(X_numbers), np.array(X_keys), np.array(y_numbers), np.array(y_keys)

    def _extract_features(self, draw: dict, historical_context: List[dict] = None) -> List[float]:
        """Extraer features avanzados de un sorteo"""
        numbers = sorted(draw['numbers'])  # Ordenar para análisis posicional
        date = draw.get('date')

        # Features básicos
        basic = [
            sum(numbers),  # Suma
            np.mean(numbers),  # Media
            np.std(numbers),  # Desviación estándar
            min(numbers),  # Mínimo
            max(numbers),  # Máximo
            max(numbers) - min(numbers),  # Rango
            len([n for n in numbers if n % 2 == 1]),  # Números impares
            len([n for n in numbers if n <= 18]),  # Números en rango bajo (1-18)
            len([n for n in numbers if 19 <= n <= 36]),  # Números en rango medio (19-36)
            len([n for n in numbers if n >= 37]),  # Números en rango alto (37-54)
        ]

        # Features de consecutivos
        consecutive = 0
        for i in range(len(numbers) - 1):
            if numbers[i+1] - numbers[i] == 1:
                consecutive += 1

        # Features de patrones
        pattern = [
            consecutive,  # Pares consecutivos
            len(set([n % 10 for n in numbers])),  # Últimos dígitos únicos
            sum([n % 3 == 0 for n in numbers]),  # Múltiplos de 3
            sum([n % 5 == 0 for n in numbers]),  # Múltiplos de 5
        ]

        # Features temporales
        temporal = [
            date.weekday() if date else 0,  # Día de la semana
            date.month if date else 1,  # Mes
            date.day if date else 1,  # Día del mes
        ]

        # Features contextuales (si hay historial)
        context = []
        if historical_context and len(historical_context) > 1:
            # Frecuencia de números recientes
            recent_numbers = []
            for h in historical_context[-10:]:
                recent_numbers.extend(h['numbers'])

            freq = Counter(recent_numbers)
            overlap = sum([1 for n in numbers if freq.get(n, 0) >= 2])
            context.extend([
                overlap,  # Números que aparecen frecuentemente
                len(set(numbers) & set(recent_numbers[-5:] if len(recent_numbers) >= 5 else recent_numbers)),  # Overlap con sorteo anterior
            ])
        else:
            context = [0, 0]

        return basic + pattern + temporal + context + [draw['key_number']]

    def _train_sklearn_models(self, X_numbers, X_keys, y_numbers, y_keys):
        """Entrenar modelos scikit-learn mejorados"""
        logger.info("Training scikit-learn models with improved architecture...")

        # Escalar features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X_numbers)
        self.scalers['features'] = scaler

        # Para cada posición de número (1-5) con modelo más potente
        for i in range(5):
            y_pos = [nums[i] for nums in y_numbers]

            # Usar GradientBoosting en lugar de RandomForest para mejor precisión
            gb = GradientBoostingClassifier(
                n_estimators=150,  # Aumentado de 50
                max_depth=7,  # Aumentado de 10
                learning_rate=0.05,  # Learning rate bajo para mejor generalización
                min_samples_split=5,
                min_samples_leaf=2,
                subsample=0.8,  # Stochastic gradient boosting
                random_state=42
            )
            gb.fit(X_scaled, y_pos)
            self.models[f'number_{i}'] = gb

            logger.info(f"  Model for position {i} trained - {len(set(y_pos))} unique values")

        # Para número clave con GradientBoosting también
        gb_key = GradientBoostingClassifier(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.05,
            min_samples_split=3,
            subsample=0.8,
            random_state=42
        )
        gb_key.fit(X_scaled, y_keys)
        self.models['key_number'] = gb_key

        logger.info(f"  Key number model trained - {len(set(y_keys))} unique values")

    def _train_xgboost_models(self, X_numbers, X_keys, y_numbers, y_keys):
        """Entrenar modelos XGBoost"""
        logger.info("Training XGBoost models...")

        # Para cada posición de número
        for i in range(5):
            y_pos = [nums[i] for nums in y_numbers]
            model = xgb.XGBClassifier(
                n_estimators=30,
                max_depth=6,
                learning_rate=0.1,
                objective='multi:softmax',
                num_class=55,
                random_state=42
            )
            model.fit(X_numbers, y_pos)
            self.models[f'number_{i}'] = model

        # Para número clave
        key_model = xgb.XGBClassifier(
            n_estimators=20,
            max_depth=4,
            learning_rate=0.1,
            objective='multi:softmax',
            num_class=10,
            random_state=42
        )
        key_model.fit(X_keys, y_keys)
        self.models['key_number'] = key_model

    def _train_statistical_models(self, historical_data: List[dict]):
        """Entrenar modelos estadísticos como fallback"""
        logger.info("Training statistical models...")

        # Contar frecuencias
        number_frequencies = Counter()
        key_frequencies = Counter()

        for draw in historical_data:
            for num in draw['numbers']:
                number_frequencies[num] += 1
            key_frequencies[draw['key_number']] += 1

        self.models['number_freq'] = number_frequencies
        self.models['key_freq'] = key_frequencies

    def predict(self, sequence: List[List[int]]) -> Dict:
        """Realizar predicción"""
        if not self.is_trained:
            logger.error("Models not trained yet")
            return self._fallback_prediction(sequence)

        try:
            if SKLEARN_AVAILABLE or XGBOOST_AVAILABLE:
                return self._ml_prediction(sequence)
            else:
                return self._statistical_prediction(sequence)
        except Exception as e:
            logger.error(f"Error in prediction: {e}")
            return self._fallback_prediction(sequence)

    def _ml_prediction(self, sequence: List[List[int]]) -> Dict:
        """Predicción usando modelos ML con features mejorados"""
        # Extraer features del último sorteo con contexto
        last_draw = {'numbers': sequence[-1][:5], 'key_number': sequence[-1][5], 'date': None}

        # Crear contexto histórico para features
        historical_context = []
        for seq in sequence[-10:]:  # Últimos 10 sorteos como contexto
            historical_context.append({'numbers': seq[:5], 'key_number': seq[5], 'date': None})

        features = np.array([self._extract_features(last_draw, historical_context)])

        # Escalar si está disponible
        if 'features' in self.scalers:
            features = self.scalers['features'].transform(features)

        # Predecir cada número
        predicted_numbers = []
        for i in range(5):
            model = self.models.get(f'number_{i}')
            if model:
                pred = model.predict(features)[0]
                predicted_numbers.append(int(pred))
            else:
                predicted_numbers.append(random.randint(1, 54))

        # Predecir número clave
        key_model = self.models.get('key_number')
        if key_model:
            key_number = int(key_model.predict(features)[0])
        else:
            key_number = random.randint(0, 9)

        # Calcular confianza basada en predicciones (más sofisticado)
        confidence = self._calculate_prediction_confidence(predicted_numbers, sequence)

        return {
            'predicted_numbers': sorted(predicted_numbers),
            'predicted_key_number': key_number,
            'confidence': confidence,
            'model_used': 'sklearn' if SKLEARN_AVAILABLE else 'xgboost',
            'number_probabilities': self._calculate_number_probabilities(predicted_numbers, sequence),
            'alternative_combinations': self._generate_alternatives(predicted_numbers, key_number)
        }

    def _calculate_prediction_confidence(self, predicted_numbers: List[int], sequence: List[List[int]]) -> float:
        """Calcular confianza basada en análisis estadístico"""
        if not sequence:
            return 0.5

        # Analizar últimos 20 sorteos
        recent_numbers = []
        for seq in sequence[-20:]:
            recent_numbers.extend(seq[:5])

        freq = Counter(recent_numbers)

        # Verificar cuántos números predichos son frecuentes
        high_freq_count = sum([1 for n in predicted_numbers if freq.get(n, 0) >= 3])
        confidence_base = 0.4 + (high_freq_count * 0.05)

        # Ajustar según patrón de rango
        range_distribution = [
            sum([1 for n in predicted_numbers if n <= 18]),
            sum([1 for n in predicted_numbers if 19 <= n <= 36]),
            sum([1 for n in predicted_numbers if n >= 37])
        ]

        # Bonificación si está bien distribuido
        if all([c >= 1 for c in range_distribution]):
            confidence_base += 0.1

        return min(confidence_base, 0.75)

    def _calculate_number_probabilities(self, predicted_numbers: List[int], sequence: List[List[int]]) -> List[float]:
        """Calcular probabilidades para todos los números"""
        if not sequence:
            return [1.0/54] * 54

        # Analizar frecuencias recientes
        recent_numbers = []
        for seq in sequence[-30:]:
            recent_numbers.extend(seq[:5])

        freq = Counter(recent_numbers)
        total_count = len(recent_numbers)

        # Calcular probabilidades basadas en frecuencia
        probabilities = []
        for num in range(1, 55):
            prob = freq.get(num, 0) / total_count if total_count > 0 else 1.0/54
            # Suavizar con uniforme para evitar extremos
            probabilities.append(0.7 * prob + 0.3 * (1.0/54))

        # Normalizar
        total = sum(probabilities)
        probabilities = [p/total for p in probabilities]

        return probabilities

    def _statistical_prediction(self, sequence: List[List[int]]) -> Dict:
        """Predicción usando modelos estadísticos"""
        number_freq = self.models.get('number_freq', Counter())
        key_freq = self.models.get('key_freq', Counter())

        # Seleccionar 5 números más probables
        top_numbers = [num for num, _ in number_freq.most_common(15)]
        predicted_numbers = random.sample(top_numbers, 5) if len(top_numbers) >= 5 else top_numbers

        # Número clave más frecuente
        key_number = key_freq.most_common(1)[0][0] if key_freq else random.randint(0, 9)

        return {
            'predicted_numbers': sorted(predicted_numbers),
            'predicted_key_number': key_number,
            'confidence': 0.45,
            'model_used': 'statistical',
            'number_probabilities': [0.2] * 54,  # Probabilidades uniformes para compatibilidad
            'alternative_combinations': self._generate_alternatives(predicted_numbers, key_number)
        }

    def _fallback_prediction(self, sequence: List[List[int]]) -> Dict:
        """Predicción de fallback si todo falla"""
        logger.warning("Using fallback prediction")

        # Generar combinación aleatoria optimizada
        predicted_numbers = sorted(random.sample(range(1, 55), 5))
        key_number = random.randint(0, 9)

        return {
            'predicted_numbers': predicted_numbers,
            'predicted_key_number': key_number,
            'confidence': 0.30,
            'model_used': 'fallback',
            'number_probabilities': [0.2] * 54,  # Probabilidades uniformes para compatibilidad
            'alternative_combinations': []
        }

    def _generate_alternatives(self, main_numbers: List[int], key_number: int, n: int = 3) -> List[List[int]]:
        """Generar combinaciones alternativas"""
        alternatives = []

        for _ in range(n):
            # Variación aleatoria de los números principales
            alternative = main_numbers.copy()
            for _ in range(2):  # Cambiar 2 números
                idx = random.randint(0, 4)
                new_num = random.randint(1, 54)
                while new_num in alternative:
                    new_num = random.randint(1, 54)
                alternative[idx] = new_num

            alternatives.append(sorted(alternative))

        return alternatives


class StatisticalPredictor:
    """Predictor estadístico (sin dependencias ML)"""

    def __init__(self):
        self.number_frequencies = Counter()
        self.key_frequencies = Counter()
        self.total_draws = 0

    def train(self, historical_data: List[dict]):
        """Entrenar con datos históricos"""
        self.total_draws = len(historical_data)

        for draw in historical_data:
            for num in draw['numbers']:
                self.number_frequencies[num] += 1
            self.key_frequencies[draw['key_number']] += 1

        logger.info(f"Statistical model trained on {self.total_draws} draws")

    def predict(self, current_date) -> Dict:
        """Realizar predicción basada en estadísticas"""
        # Números calientes (frecuencia alta)
        hot_numbers = [num for num, freq in self.number_frequencies.most_common(20)]

        # Números fríos (frecuencia baja)
        cold_numbers = [num for num, freq in self.number_frequencies.most_common()[-20:]]

        # Mezcla: 2 calientes, 2 medios, 1 frío
        mid_numbers = hot_numbers[5:15]
        predicted = [
            hot_numbers[0],
            hot_numbers[1],
            random.choice(mid_numbers) if len(mid_numbers) > 0 else hot_numbers[2],
            random.choice(mid_numbers) if len(mid_numbers) > 0 else hot_numbers[3],
            random.choice(cold_numbers) if len(cold_numbers) > 0 else hot_numbers[4]
        ]

        # Número clave más frecuente
        key_number = self.key_frequencies.most_common(1)[0][0] if self.key_frequencies else 0

        return {
            'predicted_numbers': sorted(predicted),
            'predicted_key_number': key_number,
            'confidence': 0.45,
            'model_used': 'statistical',
            'number_probabilities': [0.2] * 54,  # Probabilidades uniformes para compatibilidad
            'hot_numbers': hot_numbers[:10],
            'cold_numbers': cold_numbers[:10],
            'alternative_combinations': []
        }


def create_lightweight_models():
    """Crear modelos ligeros para Raspberry Pi"""
    return LightweightPredictor()


def create_statistical_model():
    """Crear modelo estadístico"""
    return StatisticalPredictor()
