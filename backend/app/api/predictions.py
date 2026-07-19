from fastapi import APIRouter, HTTPException, Depends
from typing import List
from datetime import datetime, timedelta
from loguru import logger

from app.models.schemas import PredictionResult, HealthCheck
from app.services.data_sources import create_data_manager
from app.core.model_loader import get_predictor, get_model_info
from app.core.config import settings

# Importación dinámica según disponibilidad de PyTorch
try:
    from app.ml.models import StatisticalPredictor
except ImportError:
    from app.ml.lightweight_models import StatisticalPredictor

router = APIRouter()

# Global models (lazy loading)
predictor = None
statistical_model = None
data_manager = None


def get_models():
    """Obtener modelos (lazy loading)"""
    global predictor, statistical_model, data_manager

    if predictor is None:
        logger.info("Loading ML models...")
        # Usar loader dinámico que detecta arquitectura
        predictor = get_predictor()

    if statistical_model is None:
        statistical_model = StatisticalPredictor()

    if data_manager is None:
        data_manager = create_data_manager()

    return predictor, statistical_model, data_manager


@router.post("/predict", response_model=PredictionResult)
async def predict_next_draw():
    """
    Obtener predicción para el próximo sorteo del domingo
    """
    try:
        predictor, statistical, data_manager = get_models()

        # Obtener datos históricos
        logger.info("Fetching historical data for prediction...")
        historical_data = data_manager.get_historical_data(force_refresh=False)

        if not historical_data:
            raise HTTPException(
                status_code=500,
                detail="No historical data available"
            )

        # Entrenar modelo predictor si es necesario
        if hasattr(predictor, 'train') and (not hasattr(predictor, 'is_trained') or not predictor.is_trained):
            logger.info("Training predictor model...")
            predictor.train(historical_data)

        # Entrenar modelo estadístico si no está entrenado
        if statistical.total_draws == 0:
            statistical.train(historical_data)

        # Preparar secuencia para modelos ML
        sequence = []
        for draw in sorted(historical_data, key=lambda x: x['date'])[-settings.MAX_HISTORY_LENGTH:]:
            sequence.append(draw['numbers'] + [draw['key_number']])

        # Realizar predicción según el tipo de modelo
        logger.info("Running prediction...")
        if hasattr(predictor, 'predict'):
            prediction = predictor.predict(sequence)
        else:
            # Fallback para modelos antiguos
            prediction = predictor.predict(sequence)

        # Calcular fecha del próximo domingo (actualizado 2026-07-16)
        today = datetime.now()
        days_until_sunday = (6 - today.weekday()) % 7
        if days_until_sunday == 0:
            days_until_sunday = 7  # Si es hoy domingo, próximo domingo
        next_sunday = today + timedelta(days=days_until_sunday)

        logger.info(f"Today: {today.strftime('%Y-%m-%d')} (day {today.strftime('%A')})")
        logger.info(f"Next draw: {next_sunday.strftime('%Y-%m-%d')} ({days_until_sunday} days from now)")

        # Enriquecer análisis
        prediction['analysis'] = {
            'hot_numbers': statistical.number_frequencies.most_common(10),
            'cold_numbers': list(reversed(statistical.number_frequencies.most_common()))[-10:],
            'total_historical_draws': len(historical_data),
            'date_range': {
                'from': min(d['date'] for d in historical_data).strftime('%Y-%m-%d'),
                'to': max(d['date'] for d in historical_data).strftime('%Y-%m-%d')
            }
        }

        # Formatear respuesta
        response = PredictionResult(
            prediction_date=next_sunday,
            predicted_numbers=prediction['predicted_numbers'],
            predicted_key_number=prediction['predicted_key_number'],
            confidence=prediction['confidence'],
            model_used=prediction['model_used'],
            alternative_combinations=prediction.get('alternative_combinations', []),
            analysis=prediction.get('analysis')
        )

        logger.info(f"Prediction generated for {next_sunday}: {response.predicted_numbers} + {response.predicted_key_number}")
        return response

    except Exception as e:
        logger.error(f"Error generating prediction: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating prediction: {str(e)}"
        )


@router.get("/models/status", response_model=dict)
async def get_models_status():
    """Obtener estado de los modelos"""
    try:
        predictor, statistical, data_manager = get_models()
        model_info = get_model_info()

        status = {
            "architecture": model_info['architecture'],
            "model_type": model_info['model_type'],
            "pytorch_available": model_info['pytorch_available'],
            "sklearn_available": model_info['sklearn_available'],
            "predictor_loaded": predictor is not None,
            "statistical_loaded": statistical is not None,
            "statistical_trained": statistical.total_draws > 0 if statistical else False,
            "data_manager_available": data_manager is not None,
            "max_history_length": settings.MAX_HISTORY_LENGTH
        }

        # Información específica según tipo de modelo
        if hasattr(predictor, 'models'):
            if hasattr(predictor, 'is_trained'):
                status['predictor_trained'] = predictor.is_trained

            # Contar modelos si es EnsemblePredictor
            if hasattr(predictor, 'models') and isinstance(predictor.models, list):
                status['predictor_models_count'] = len(predictor.models)

        return status

    except Exception as e:
        logger.error(f"Error getting models status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting models status: {str(e)}"
        )


@router.post("/predict/statistical", response_model=PredictionResult)
async def predict_statistical():
    """
    Obtener predicción usando solo modelo estadístico
    """
    try:
        ensemble, statistical, data_manager = get_models()

        # Obtener datos históricos
        historical_data = data_manager.get_historical_data(force_refresh=False)

        if not historical_data:
            raise HTTPException(
                status_code=500,
                detail="No historical data available"
            )

        # Entrenar si es necesario
        if statistical.total_draws == 0:
            statistical.train(historical_data)

        # Predecir
        prediction = statistical.predict(datetime.now())

        # Calcular próximo domingo
        today = datetime.now()
        days_until_sunday = (6 - today.weekday()) % 7
        if days_until_sunday == 0:
            days_until_sunday = 7
        next_sunday = today + timedelta(days=days_until_sunday)

        return PredictionResult(
            prediction_date=next_sunday,
            predicted_numbers=prediction['predicted_numbers'],
            predicted_key_number=prediction['predicted_key_number'],
            confidence=prediction['confidence'],
            model_used=prediction['model_used'],
            alternative_combinations=prediction.get('alternative_combinations', []),
            analysis={
                'hot_numbers': prediction.get('hot_numbers', []),
                'cold_numbers': prediction.get('cold_numbers', []),
                'total_historical_draws': len(historical_data)
            }
        )

    except Exception as e:
        logger.error(f"Error generating statistical prediction: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating statistical prediction: {str(e)}"
        )
