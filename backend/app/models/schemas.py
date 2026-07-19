from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class DrawResult(BaseModel):
    """Modelo de resultado de un sorteo"""
    id: Optional[int] = None
    date: datetime
    numbers: List[int] = Field(..., min_length=5, max_length=5, description="5 números del 1 al 54")
    key_number: int = Field(..., ge=0, le=9, description="Número clave del 0 al 9")
    jackpot: Optional[float] = None
    winners: Optional[int] = None

    class Config:
        json_schema_extra = {
            "example": {
                "date": "2026-07-11T00:00:00",
                "numbers": [3, 15, 27, 38, 49],
                "key_number": 7,
                "jackpot": 1500000,
                "winners": 1
            }
        }


class PredictionResult(BaseModel):
    """Modelo de resultado de predicción"""
    prediction_date: datetime
    predicted_numbers: List[int] = Field(..., min_length=5, max_length=5, description="5 números predichos")
    predicted_key_number: int = Field(..., ge=0, le=9, description="Número clave predicho")
    confidence: float = Field(..., ge=0, le=1, description="Confianza de la predicción")
    model_used: str
    alternative_combinations: List[List[int]] = Field(default_factory=list, description="Combinaciones alternativas")
    analysis: Optional[dict] = None

    class Config:
        json_schema_extra = {
            "example": {
                "prediction_date": "2026-07-18T00:00:00",
                "predicted_numbers": [7, 21, 33, 41, 52],
                "predicted_key_number": 4,
                "confidence": 0.68,
                "model_used": "ensemble",
                "alternative_combinations": [[5, 19, 31, 39, 50], [8, 22, 34, 42, 53]],
                "analysis": {
                    "hot_numbers": [21, 33, 41],
                    "cold_numbers": [2, 18, 47],
                    "pattern_analysis": "Tendencia de números pares"
                }
            }
        }


class NumberStats(BaseModel):
    """Estadísticas de un número"""
    number: int
    frequency: int = Field(..., description="Número de veces que ha salido")
    percentage: float = Field(..., description="Porcentaje de apariciones")
    last_drawn: Optional[datetime] = Field(None, description="Última vez que salió")
    hot: bool = Field(..., description="Si es un número caliente")
    cold: bool = Field(..., description="Si es un número frío")


class KeyNumberStats(BaseModel):
    """Estadísticas del número clave"""
    key_number: int
    frequency: int
    percentage: float
    last_drawn: Optional[datetime] = None
    hot: bool = False
    cold: bool = False


class StatisticsResponse(BaseModel):
    """Respuesta de estadísticas generales"""
    total_draws: int
    number_stats: List[NumberStats]
    key_number_stats: List[KeyNumberStats]
    most_common_combinations: List[List[int]]
    patterns: dict
    next_draw_date: datetime


class HealthCheck(BaseModel):
    """Health check response"""
    status: str
    service: str
    models_loaded: bool = False
    database_connected: bool = False
