"""Endpoints de Bonoloto: generación, estadísticas, histórico y actualización."""

from __future__ import annotations

import datetime as dt
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from loguru import logger

from app.models.bonoloto_schemas import (
    BonolotoGenerateRequest,
    BonolotoGenerateResponse,
    BonolotoHistoryDraw,
    BonolotoMetaResponse,
    BonolotoStatsResponse,
)
from app.services.bonoloto_data import get_bonoloto_data_manager, next_bonoloto_date
from app.services.bonoloto_generator import (
    GAME_INFO,
    STRATEGIES,
    generate_bonoloto,
    get_bonoloto_model,
)

router = APIRouter()


def _strategies_payload() -> dict[str, dict[str, str]]:
    return {
        name: {
            "label": value["label"],
            "description": value["description"],
        }
        for name, value in STRATEGIES.items()
    }


@router.get("/meta", response_model=BonolotoMetaResponse)
def get_meta():
    """Reglas del juego, estado del dataset y estrategias disponibles."""
    manager = get_bonoloto_data_manager()
    summary = manager.summary()
    return {
        "game": GAME_INFO,
        "dataset": summary,
        "strategies": _strategies_payload(),
        "next_draw": summary.get("next_draw"),
    }


@router.get("/next-draw")
def get_next_draw():
    """Fecha del próximo sorteo de Bonoloto."""
    manager = get_bonoloto_data_manager()
    draws = manager.load()
    last_draw = draws[0].date if draws else None
    return {
        "next_draw": next_bonoloto_date(last_draw).isoformat(),
        "last_draw": last_draw.isoformat() if last_draw else None,
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
    }


@router.get("/history", response_model=list[BonolotoHistoryDraw])
def get_history(
    limit: int = Query(
        default=50, ge=1, le=500, description="Número de sorteos a devolver"
    ),
):
    """Últimos sorteos de Bonoloto, del más reciente al más antiguo."""
    manager = get_bonoloto_data_manager()
    draws = manager.load()[:limit]
    return [
        {
            "date": draw.date.isoformat(),
            "numbers": list(draw.numbers),
            "complementario": draw.complementario,
            "reintegro": draw.reintegro,
            "source": draw.source,
        }
        for draw in draws
    ]


@router.get("/stats", response_model=BonolotoStatsResponse)
def get_stats():
    """Estadísticas del histórico: frecuentes, calientes, fríos y retrasados."""
    try:
        model = get_bonoloto_model()
        return {
            "dataset": model.dataset_summary(),
            "analysis": model.analysis(),
            "model": {
                "type": "statistical-portfolio-optimizer",
                "version": "1.0",
                "ticket_odds": {
                    "6": 1 / 13_983_816,
                    "5_plus_complementario": 6 / 13_983_816,
                    "5": 252 / 13_983_816,
                    "4": 13_545 / 13_983_816,
                    "3": 246_820 / 13_983_816,
                    "3_plus": 260_624 / 13_983_816,
                },
                "strategies": _strategies_payload(),
            },
        }
    except Exception as exc:
        logger.error(f"Error obteniendo estadísticas de Bonoloto: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo estadísticas de Bonoloto: {exc}",
        )


def _generate(
    count: int,
    strategy: str,
    seed: Optional[int],
) -> dict:
    try:
        return generate_bonoloto(count=count, strategy=strategy, seed=seed)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(f"Error generando combinaciones de Bonoloto: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generando combinaciones de Bonoloto: {exc}",
        )


@router.post("/generate", response_model=BonolotoGenerateResponse)
def generate(request: BonolotoGenerateRequest):
    """
    Genera una cartera optimizada de 1 a 10 combinaciones de Bonoloto.

    La estrategia `big_prize` (por defecto) prioriza cobertura de pares y
    tríos, baja popularidad de las combinaciones y calidad estadística.
    """
    return _generate(request.count, request.strategy, request.seed)


@router.get("/generate", response_model=BonolotoGenerateResponse)
def generate_get(
    count: int = Query(default=10, ge=1, le=10),
    strategy: str = Query(default="big_prize"),
    seed: Optional[int] = Query(default=None, ge=0),
):
    """Alias GET de `/generate` para pruebas rápidas."""
    if strategy not in STRATEGIES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Estrategia no válida: {strategy}. "
                f"Opciones: {', '.join(STRATEGIES)}"
            ),
        )
    return _generate(count, strategy, seed)


@router.get("/refresh")
@router.post("/refresh")
def refresh_data():
    """Actualiza el histórico desde las hojas públicas de Lotoideas/SELAE."""
    try:
        result = get_bonoloto_data_manager().refresh()
        if result.get("status") == "error":
            raise HTTPException(
                status_code=502,
                detail=(
                    "No se pudo actualizar el histórico de Bonoloto. "
                    f"Errores: {result.get('errors')}"
                ),
            )
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error actualizando Bonoloto: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Error actualizando Bonoloto: {exc}",
        )
