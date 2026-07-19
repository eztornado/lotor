from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime
from loguru import logger

from app.models.schemas import DrawResult
from app.services.data_sources import create_data_manager
from app.services.validator import create_validator

router = APIRouter()

data_manager = None


def get_data_manager():
    """Obtener data manager (lazy loading)"""
    global data_manager
    if data_manager is None:
        data_manager = create_data_manager()
    return data_manager


@router.get("/recent", response_model=List[DrawResult])
async def get_recent_draws(
    limit: int = Query(default=52, ge=1, le=200, description="Número de sorteos a obtener")
):
    """
    Obtener los últimos N sorteos
    Por defecto, las últimas 52 semanas (1 año)
    """
    try:
        manager = get_data_manager()
        draws = manager.get_historical_data(force_refresh=False)

        # Limitar resultados
        draws = draws[:limit]

        # Convertir a formato de respuesta
        results = []
        for draw in draws:
            result = DrawResult(
                date=draw['date'],
                numbers=draw['numbers'],
                key_number=draw['key_number'],
                source=draw.get('source', 'loteriasyapuestas.es')
            )
            results.append(result)

        logger.info(f"Retrieved {len(results)} recent draws")
        return results

    except Exception as e:
        logger.error(f"Error retrieving recent draws: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving recent draws: {str(e)}"
        )


@router.get("/refresh", response_model=dict)
async def refresh_historical_data():
    """
    Forzar actualización de datos históricos desde la fuente
    """
    try:
        manager = get_data_manager()
        draws = manager.get_historical_data(force_refresh=True)

        return {
            "status": "success",
            "message": "Historical data refreshed successfully",
            "total_draws": len(draws),
            "date_range": {
                "from": min(d['date'] for d in draws).strftime('%Y-%m-%d'),
                "to": max(d['date'] for d in draws).strftime('%Y-%m-%d')
            }
        }

    except Exception as e:
        logger.error(f"Error refreshing historical data: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error refreshing historical data: {str(e)}"
        )


@router.get("/date/{date_str}", response_model=DrawResult)
async def get_draw_by_date(date_str: str):
    """
    Obtener un sorteo específico por fecha (formato: YYYY-MM-DD)
    """
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')

        manager = get_data_manager()
        draws = manager.get_historical_data(force_refresh=False)

        # Buscar sorteo específico
        for draw in draws:
            if draw['date'].date() == date_obj.date():
                return DrawResult(
                    date=draw['date'],
                    numbers=draw['numbers'],
                    key_number=draw['key_number'],
                    source=draw.get('source', 'loteriasyapuestas.es')
                )

        raise HTTPException(
            status_code=404,
            detail=f"No draw found for date {date_str}"
        )

    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid date format. Use YYYY-MM-DD"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving draw by date: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving draw by date: {str(e)}"
        )


@router.get("/range")
async def get_draws_by_range(
    start_date: str = Query(..., description="Fecha inicio (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Fecha fin (YYYY-MM-DD)")
):
    """
    Obtener sorteos en un rango de fechas
    """
    try:
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d') if end_date else datetime.now()

        if start > end:
            raise HTTPException(
                status_code=400,
                detail="start_date must be before end_date"
            )

        manager = get_data_manager()
        draws = manager.get_historical_data(force_refresh=False)

        # Filtrar por rango
        filtered_draws = []
        for draw in draws:
            if start <= draw['date'] <= end:
                filtered_draws.append(DrawResult(
                    date=draw['date'],
                    numbers=draw['numbers'],
                    key_number=draw['key_number'],
                    source=draw.get('source', 'loteriasyapuestas.es')
                ))

        return {
            "count": len(filtered_draws),
            "range": {
                "start": start_date,
                "end": end_date or datetime.now().strftime('%Y-%m-%d')
            },
            "draws": filtered_draws
        }

    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid date format. Use YYYY-MM-DD"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving draws by range: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving draws by range: {str(e)}"
        )


@router.get("/validate")
async def validate_current_data():
    """
    Validar que los datos están actualizados a la fecha actual
    """
    try:
        manager = get_data_manager()
        validator = create_validator()

        draws = manager.get_historical_data(force_refresh=False)

        # Validar dataset
        validation_result = validator.validate_dataset_freshness(draws)

        # Limpiar dataset
        clean_draws = validator.clean_and_validate_dataset(draws)

        # Obtener próximo sorteo
        next_draw = validator.get_next_draw_date()

        return {
            "validation": validation_result,
            "next_draw_date": next_draw.strftime('%Y-%m-%d'),
            "dataset_info": {
                "total_draws": len(draws),
                "valid_draws": len(clean_draws),
                "invalid_draws": len(draws) - len(clean_draws)
            }
        }

    except Exception as e:
        logger.error(f"Error validating data: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error validating data: {str(e)}"
        )
