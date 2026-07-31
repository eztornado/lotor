"""
Dominio core para todos los tipos de lotería
Define las entidades base y abstracciones compartidas
"""

from enum import Enum
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel
from abc import ABC, abstractmethod


class LotteryType(str, Enum):
    """Tipos de lotería soportados"""
    PRIMITIVA = "primitiva"  # El Gordo de la Primitiva (domingos)
    NACIONAL = "nacional"    # Sorteo Nacional (jueves)
    BONOLOTO = "bonoloto"    # Bonoloto (diario - futuro)
    EUROMILLONES = "euromillones"  # Euromillones (martes/viernes - futuro)


class DrawResult(BaseModel):
    """Resultado de un sorteo - genérico para cualquier tipo de lotería"""
    lottery_type: LotteryType
    draw_date: datetime
    numbers: List[int]           # Números principales (5 para Primitiva, 1-3 para Nacional)
    additional_numbers: List[int] = []  # Números adicionales (key, reintegros, etc)
    metadata: Dict[str, Any] = {}       # Datos específicos por lotería

    class Config:
        use_enum_values = True


class PredictionResult(BaseModel):
    """Resultado de predicción genérico"""
    lottery_type: LotteryType
    prediction_date: datetime
    predicted_numbers: List[int]
    additional_predictions: List[int] = []
    confidence: float
    model_used: str
    strategy_used: str
    analysis: Dict[str, Any] = {}
    alternative_combinations: List[Dict[str, Any]] = []

    class Config:
        use_enum_values = True


class LotterySchedule(BaseModel):
    """Horario de sorteos para cada tipo de lotería"""
    lottery_type: LotteryType
    draw_day: str              # "sunday", "thursday", etc
    draw_frequency: str        # "weekly", "daily"
    next_draw_date: Optional[datetime] = None
    draw_count: int = 1        # Sorteos por frecuencia (1 para semanal, 7 para diario)

    class Config:
        use_enum_values = True


class LotteryPredictor(ABC):
    """Clase base abstracta para todos los predictores de lotería"""

    def __init__(self):
        self.lottery_type: LotteryType = None
        self.is_trained: bool = False
        self.model_path: str = None

    @abstractmethod
    def predict(self, historical_data: List[DrawResult]) -> PredictionResult:
        """
        Realizar predicción para el próximo sorteo

        Args:
            historical_data: Lista de sorteos históricos

        Returns:
            PredictionResult con la predicción generada
        """
        pass

    @abstractmethod
    def get_schedule(self) -> LotterySchedule:
        """Obtener información sobre horario de sorteos"""
        pass

    @abstractmethod
    def train(self, historical_data: List[DrawResult]) -> bool:
        """Entrenar modelo con datos históricos"""
        pass

    @abstractmethod
    def get_historical_data(self, count: int = 200) -> List[DrawResult]:
        """Obtener datos históricos para esta lotería"""
        pass

    def get_next_draw_date(self) -> datetime:
        """Calcular fecha del próximo sorteo - implementación genérica"""
        from datetime import timedelta, datetime as dt

        # Las subclases deben implementar get_schedule() sin llamar a este método
        # Este método es un helper, no debe ser llamado desde get_schedule()
        today = dt.now()

        # Implementación por defecto: cada domingo
        # Las subclases pueden sobrescribir esto si es necesario
        days_until = (6 - today.weekday()) % 7
        if days_until == 0:
            days_until = 7  # Si hoy es domingo, próximo domingo

        return today + timedelta(days=days_until)


class DataSource(ABC):
    """Clase base abstracta para fuentes de datos"""

    @abstractmethod
    def fetch_draws(self, count: int = 200) -> List[DrawResult]:
        """Obtener sorteos históricos"""
        pass

    @abstractmethod
    def parse_draw(self, raw_data: Any) -> DrawResult:
        """Parsear datos crudos a DrawResult"""
        pass


class MLModel(ABC):
    """Clase base para modelos ML compartidos"""

    def __init__(self):
        self.model = None
        self.scaler = None
        self.is_trained = False
        self.features_count = 0

    @abstractmethod
    def train(self, X, y) -> bool:
        """Entrenar modelo"""
        pass

    @abstractmethod
    def predict(self, X) -> List[int]:
        """Realizar predicción"""
        pass

    @abstractmethod
    def extract_features(self, draw_result: DrawResult) -> List[float]:
        """Extraer features de un sorteo"""
        pass