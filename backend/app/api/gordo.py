"""Endpoints de El Gordo: generación, estadísticas, histórico y actualización."""

from __future__ import annotations

import datetime as dt
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from loguru import logger

from app.models.gordo_schemas import (
    GordoGenerateRequest,
    GordoGenerateResponse,
    GordoHistoryDraw,
    GordoMetaResponse,
    GordoStatsResponse,
)
from app.services.gordo_data import get_gordo_data_manager, next_gordo_date
from app.services.gordo_generator import (
    GAME_INFO,
    PRIZE_COUNTS,
    PRIZE_PROBABILITIES,
    REINTEGRO_PROBABILITY,
    STRATEGIES,
    TICKET_PRICE_EUR,
    TOTAL_COMBINATIONS,
    generate_gordo,
    get_gordo_model,
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


@router.get("/meta", response_model=GordoMetaResponse)
def get_meta():
    """Reglas del juego, estado del dataset y estrategias disponibles."""
    manager = get_gordo_data_manager()
    summary = manager.summary()
    return {
        "game": GAME_INFO,
        "dataset": summary,
        "strategies": _strategies_payload(),
        "next_draw": summary.get("next_draw"),
    }


@router.get("/next-draw")
def get_next_draw():
    """Fecha del próximo sorteo de El Gordo (domingos)."""
    manager = get_gordo_data_manager()
    draws = manager.load()
    last_draw = draws[0].date if draws else None
    return {
        "next_draw": next_gordo_date(last_draw).isoformat(),
        "last_draw": last_draw.isoformat() if last_draw else None,
        "draw_days": "Domingos",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
    }


@router.get("/history", response_model=list[GordoHistoryDraw])
def get_history(
    limit: int = Query(
        default=50, ge=1, le=500, description="Número de sorteos a devolver"
    ),
):
    """Últimos sorteos de El Gordo, del más reciente al más antiguo."""
    manager = get_gordo_data_manager()
    draws = manager.load()[:limit]
    return [
        {
            "date": draw.date.isoformat(),
            "numbers": list(draw.numbers),
            "key_number": draw.key_number,
            "source": draw.source,
        }
        for draw in draws
    ]


@router.get("/stats", response_model=GordoStatsResponse)
def get_stats():
    """Estadísticas del histórico: frecuentes, calientes, fríos, claves y pares."""
    try:
        model = get_gordo_model()
        return {
            "dataset": model.dataset_summary(),
            "analysis": model.analysis(),
            "model": {
                "type": "statistical-portfolio-optimizer",
                "version": "1.0",
                "total_combinations": TOTAL_COMBINATIONS,
                "number_combinations": TOTAL_COMBINATIONS // 10,
                "ticket_odds": {
                    "1": PRIZE_PROBABILITIES["1"],
                    "2": PRIZE_PROBABILITIES["2"],
                    "3": PRIZE_PROBABILITIES["3"],
                    "4": PRIZE_PROBABILITIES["4"],
                    "5": PRIZE_PROBABILITIES["5"],
                    "6": PRIZE_PROBABILITIES["6"],
                    "7": PRIZE_PROBABILITIES["7"],
                    "8": PRIZE_PROBABILITIES["8"],
                    "any_prize": sum(PRIZE_PROBABILITIES.values()),
                    "reintegro": REINTEGRO_PROBABILITY,
                    "any_return": 1.0
                    - (1.0 - sum(PRIZE_PROBABILITIES.values()))
                    * (1.0 - REINTEGRO_PROBABILITY),
                },
                "prize_counts": PRIZE_COUNTS,
                "reintegro_plays": TOTAL_COMBINATIONS // 10,
                "ticket_price_eur": TICKET_PRICE_EUR,
                "strategies": _strategies_payload(),
            },
        }
    except Exception as exc:
        logger.error(f"Error obteniendo estadísticas de El Gordo: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo estadísticas de El Gordo: {exc}",
        )


def _generate(
    count: int,
    strategy: str,
    seed: Optional[int],
) -> dict:
    try:
        return generate_gordo(count=count, strategy=strategy, seed=seed)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(f"Error generando combinaciones de El Gordo: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generando combinaciones de El Gordo: {exc}",
        )


@router.post("/generate", response_model=GordoGenerateResponse)
def generate(request: GordoGenerateRequest):
    """
    Genera una cartera optimizada de 1 a 10 combinaciones de El Gordo.

    La estrategia `big_prize` (por defecto) prioriza cobertura de pares y
    tríos, baja popularidad de las combinaciones y calidad estadística.
    Las probabilidades de la respuesta son exactas para carteras disjuntas.
    """
    return _generate(request.count, request.strategy, request.seed)


@router.get("/generate", response_model=GordoGenerateResponse)
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
    """Actualiza el histórico desde la hoja pública de Lotoideas/SELAE."""
    try:
        result = get_gordo_data_manager().refresh()
        if result.get("status") == "error":
            raise HTTPException(
                status_code=502,
                detail=(
                    "No se pudo actualizar el histórico de El Gordo. "
                    f"Errores: {result.get('errors')}"
                ),
            )
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error actualizando El Gordo: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Error actualizando El Gordo: {exc}",
        )
