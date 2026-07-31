"""
API unificada para todos los tipos de lotería
Endpoints genéricos que funcionan con cualquier tipo de lotería
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict
from loguru import logger

from app.domain.lottery import LotteryType, PredictionResult, LotterySchedule
from app.application.primitiva_predictor import PrimitivaPredictor
from app.application.nacional_predictor import NacionalPredictor

router = APIRouter()

# Registry de predictores (singleton)
_predictors = {
    LotteryType.PRIMITIVA: PrimitivaPredictor(),
    LotteryType.NACIONAL: NacionalPredictor(),
}


def get_predictor(lottery_type: LotteryType):
    """Obtener predictor para un tipo de lotería"""
    predictor = _predictors.get(lottery_type)
    if not predictor:
        raise HTTPException(
            status_code=400,
            detail=f"Lottery type '{lottery_type}' not supported"
        )
    return predictor


@router.get("/lotteries", response_model=List[Dict])
async def get_supported_lotteries():
    """Obtener lista de loterías soportadas"""
    return [
        {
            "type": LotteryType.PRIMITIVA,
            "name": "El Gordo de la Primitiva",
            "description": "Lotería nacional dominical (5 números + clave)",
            "draw_day": "sunday",
            "enabled": True
        },
        {
            "type": LotteryType.NACIONAL,
            "name": "Sorteo Nacional",
            "description": "Sorteo del jueves (décimos, series y fracciones)",
            "draw_day": "thursday",
            "enabled": True
        }
    ]


@router.get("/lotteries/{lottery_type}/schedule", response_model=LotterySchedule)
async def get_lottery_schedule(lottery_type: LotteryType):
    """Obtener horario de sorteos para una lotería específica"""
    try:
        predictor = get_predictor(lottery_type)
        return predictor.get_schedule()
    except Exception as e:
        logger.error(f"Error getting schedule for {lottery_type}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/lotteries/{lottery_type}/predict", response_model=PredictionResult)
async def predict_lottery(
    lottery_type: LotteryType,
    count: int = Query(default=200, ge=1, le=500, description="Número de sorteos históricos a usar")
):
    """
    Obtener predicción para una lotería específica

    - **lottery_type**: Tipo de lotería (primitiva, nacional)
    - **count**: Número de sorteos históricos a usar para entrenamiento (default: 200)
    """
    try:
        predictor = get_predictor(lottery_type)

        # Obtener datos históricos
        logger.info(f"Fetching historical data for {lottery_type}...")
        historical_data = predictor.get_historical_data(count=count)

        if not historical_data:
            raise HTTPException(
                status_code=500,
                detail=f"No historical data available for {lottery_type}"
            )

        logger.info(f"Got {len(historical_data)} historical draws for {lottery_type}")

        # Realizar predicción
        prediction = predictor.predict(historical_data)

        logger.info(f"Prediction generated for {lottery_type}: {prediction.predicted_numbers}")
        return prediction

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error predicting {lottery_type}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating prediction: {str(e)}"
        )


@router.get("/lotteries/{lottery_type}/history")
async def get_lottery_history(
    lottery_type: LotteryType,
    count: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0)
):
    """Obtener historial de sorteos para una lotería específica"""
    try:
        predictor = get_predictor(lottery_type)
        historical_data = predictor.get_historical_data(count=count + offset)

        # Aplicar offset
        historical_data = historical_data[offset:offset + count]

        return {
            "lottery_type": lottery_type,
            "total": len(historical_data),
            "count": len(historical_data),
            "offset": offset,
            "draws": [
                {
                    "draw_date": draw.draw_date.isoformat(),
                    "numbers": draw.numbers,
                    "additional_numbers": draw.additional_numbers,
                    "metadata": draw.metadata
                }
                for draw in historical_data
            ]
        }

    except Exception as e:
        logger.error(f"Error fetching history for {lottery_type}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching history: {str(e)}"
        )


@router.post("/predictions/all")
async def get_all_predictions(
    count: int = Query(default=200, ge=1, le=500)
):
    """
    Obtener predicciones para todas las loterías activas

    Útil para dashboard con predicciones de múltiples loterías
    """
    predictions = {}

    for lottery_type, predictor in _predictors.items():
        try:
            logger.info(f"Generating prediction for {lottery_type}...")

            # Obtener datos históricos
            historical_data = predictor.get_historical_data(count=count)

            if historical_data:
                # Realizar predicción
                prediction = predictor.predict(historical_data)
                predictions[lottery_type] = prediction
            else:
                logger.warning(f"No historical data for {lottery_type}")
                predictions[lottery_type] = {
                    "error": "No historical data available",
                    "lottery_type": lottery_type
                }

        except Exception as e:
            logger.error(f"Error predicting {lottery_type}: {e}")
            predictions[lottery_type] = {
                "error": str(e),
                "lottery_type": lottery_type
            }

    return {
        "timestamp": predictor.get_next_draw_date().isoformat(),
        "predictions": predictions,
        "total_lotteries": len(_predictors)
    }


@router.get("/predictions/comparison")
async def compare_predictions(
    count: int = Query(default=200, ge=1, le=500)
):
    """
    Comparar predicciones entre diferentes loterías

    Útil para análisis comparativo y estadísticas
    """
    comparison = {}

    for lottery_type, predictor in _predictors.items():
        try:
            historical_data = predictor.get_historical_data(count=count)

            if historical_data:
                prediction = predictor.predict(historical_data)
                schedule = predictor.get_schedule()

                comparison[lottery_type] = {
                    "name": lottery_type,
                    "next_draw": schedule.next_draw_date.isoformat() if schedule.next_draw_date else None,
                    "draw_day": schedule.draw_day,
                    "prediction": {
                        "numbers": prediction.predicted_numbers,
                        "additional": prediction.additional_predictions,
                        "confidence": prediction.confidence,
                        "model": prediction.model_used,
                        "strategy": prediction.strategy_used
                    },
                    "analysis": prediction.analysis
                }

        except Exception as e:
            logger.error(f"Error in comparison for {lottery_type}: {e}")

    return {
        "comparison": comparison,
        "total_compared": len(comparison)
    }


@router.get("/health/lotteries")
async def health_check_lotteries():
    """Health check específico para loterías"""
    health_status = {}

    for lottery_type, predictor in _predictors.items():
        try:
            # Verificar que podemos obtener datos históricos
            historical_data = predictor.get_historical_data(count=10)

            health_status[lottery_type] = {
                "status": "healthy" if historical_data else "no_data",
                "model_trained": predictor.is_trained,
                "available_draws": len(historical_data) if historical_data else 0
            }

        except Exception as e:
            health_status[lottery_type] = {
                "status": "error",
                "error": str(e)
            }

    return {
        "overall_status": "healthy" if all(
            h.get("status") == "healthy" for h in health_status.values()
        ) else "degraded",
        "lotteries": health_status
    }