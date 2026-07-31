"""
API endpoints para gestión de actualizaciones de datos
"""

from fastapi import APIRouter, HTTPException
from typing import Optional
from loguru import logger
from datetime import datetime

from app.domain.lottery import LotteryType
from app.services.data_updater import get_data_updater

router = APIRouter()


@router.post("/data-update/force")
async def force_data_update(
    lottery_type: Optional[LotteryType] = None
):
    """
    Forzar actualización inmediata de datos

    - **lottery_type**: Tipo específico de lotería (primitiva, nacional), o None para todas
    """
    try:
        updater = get_data_updater()

        logger.info(f"Force update requested for {lottery_type or 'all lotteries'}")

        result = updater.force_update(lottery_type)

        return {
            "status": "completed",
            "timestamp": datetime.now().isoformat(),
            "result": result
        }

    except Exception as e:
        logger.error(f"Error in force update: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error forcing update: {str(e)}"
        )


@router.get("/data-update/status")
async def get_update_status():
    """Obtener estado de actualizaciones automáticas"""
    try:
        updater = get_data_updater()
        status = updater.get_update_status()

        # Agregar información calculada
        status["should_update_now"] = updater.should_update()
        status["next_update_time"] = updater.get_next_update_time().isoformat()
        status["update_interval_hours"] = 6

        return status

    except Exception as e:
        logger.error(f"Error getting update status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting status: {str(e)}"
        )


@router.post("/data-update/run")
async def run_data_update():
    """
    Ejecutar actualización de datos ahora
    Equivalente a force-update pero con nombre más claro
    """
    return await force_data_update()