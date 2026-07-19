"""
Modelos ligeros para Raspberry Pi (sin PyTorch)
Usa scikit-learn y XGBoost en lugar de PyTorch
"""

import numpy as np
from typing import List, Dict
from loguru import logger
from collections import Counter
import random

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

    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.is_trained = False

    def train(self, historical_data: List[dict]):
        """Entrenar con datos históricos"""
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
        return True

    def _prepare_training_data(self, historical_data: List[dict]):
        """Preparar datos para entrenamiento"""
        X_numbers = []
        X_keys = []
        y_numbers = []
        y_keys = []

        # Crear secuencias para entrenamiento
        for i in range(len(historical_data) - 1):
            current_draw = historical_data[i]
            next_draw = historical_data[i + 1]

            # Features del sorteo actual
            features = self._extract_features(current_draw)

            # Targets (próximo sorteo)
            targets_numbers = next_draw['numbers']
            target_key = next_draw['key_number']

            X_numbers.append(features)
            X_keys.append(features)
            y_numbers.append(targets_numbers)
            y_keys.append(target_key)

        return np.array(X_numbers), np.array(X_keys), np.array(y_numbers), np.array(y_keys)

    def _extract_features(self, draw: dict) -> List[float]:
        """Extraer features de un sorteo"""
        numbers = draw['numbers']
        return [
            sum(numbers),  # Suma
            np.mean(numbers),  # Media
            np.std(numbers),  # Desviación estándar
            min(numbers),  # Mínimo
            max(numbers),  # Máximo
            max(numbers) - min(numbers),  # Rango
            len([n for n in numbers if n % 2 == 1]),  # Números impares
            draw['key_number'],  # Número clave anterior
            draw['date'].weekday(),  # Día de la semana
            draw['date'].month  # Mes
        ]

    def _train_sklearn_models(self, X_numbers, X_keys, y_numbers, y_keys):
        """Entrenar modelos scikit-learn"""
        logger.info("Training scikit-learn models...")

        # Escalar features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X_numbers)
        self.scalers['features'] = scaler

        # Para cada posición de número (1-5)
        for i in range(5):
            y_pos = [nums[i] for nums in y_numbers]
            rf = RandomForestClassifier(n_estimators=50, max_depth=10, random_state=42)
            rf.fit(X_scaled, y_pos)
            self.models[f'number_{i}'] = rf

        # Para número clave
        rf_key = RandomForestClassifier(n_estimators=30, max_depth=8, random_state=42)
        rf_key.fit(X_scaled, y_keys)
        self.models['key_number'] = rf_key

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
        """Predicción usando modelos ML"""
        # Extraer features del último sorteo
        last_draw = {'numbers': sequence[-1][:5], 'key_number': sequence[-1][5], 'date': None}
        features = np.array([self._extract_features(last_draw)])

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

        return {
            'predicted_numbers': sorted(predicted_numbers),
            'predicted_key_number': key_number,
            'confidence': 0.55,  # Confianza moderada para modelos ligeros
            'model_used': 'sklearn' if SKLEARN_AVAILABLE else 'xgboost',
            'alternative_combinations': self._generate_alternatives(predicted_numbers, key_number)
        }

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
