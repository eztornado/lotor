"""Endpoints de La Quiniela: predicciones, generación, estadísticas e histórico."""

from __future__ import annotations

import datetime as dt
import threading
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from loguru import logger

from app.models.quiniela_schemas import (
    QuinielaGenerateRequest,
    QuinielaGenerateResponse,
    QuinielaHistoryMatch,
    QuinielaJornadaResponse,
    QuinielaMetaResponse,
    QuinielaStatsResponse,
    QuinielaTeamResponse,
)
from app.services.quiniela_data import get_quiniela_data_manager
from app.services.quiniela_generator import (
    DEFAULT_BUDGET_EUR,
    GAME_INFO,
    STRATEGIES,
    generate_quiniela,
    get_jornada_predictions,
    list_jornadas,
)
from app.services.quiniela_model import (
    backtest_model,
    clear_quiniela_model_cache,
    get_quiniela_model,
)

router = APIRouter()

_backtest_cache: Optional[dict] = None
_backtest_lock = threading.Lock()


def _strategies_payload() -> dict[str, dict[str, object]]:
    return {
        name: {
            "label": value["label"],
            "description": value["description"],
        }
        for name, value in STRATEGIES.items()
    }


def _quick_backtest() -> dict:
    """Backtest ligero y cacheado para la página de estadísticas."""
    global _backtest_cache
    if _backtest_cache is not None:
        return _backtest_cache
    with _backtest_lock:
        if _backtest_cache is not None:
            return _backtest_cache
        try:
            manager = get_quiniela_data_manager()
            _backtest_cache = backtest_model(manager.load_matches(), limit=400)
        except Exception as exc:  # pragma: no cover - defensivo
            logger.warning(f"No se pudo calcular el backtest de La Quiniela: {exc}")
            _backtest_cache = {"matches": 0, "error": str(exc)}
        return _backtest_cache


@router.get("/meta", response_model=QuinielaMetaResponse)
def get_meta():
    """Reglas del juego, estado del dataset y estrategias disponibles."""
    manager = get_quiniela_data_manager()
    summary = manager.summary()
    return {
        "game": GAME_INFO,
        "dataset": summary,
        "strategies": _strategies_payload(),
        "next_jornada": summary.get("next_jornada"),
    }


@router.get("/jornadas")
def get_jornadas():
    """Jornadas disponibles en el calendario local."""
    return list_jornadas()


@router.get("/jornada", response_model=QuinielaJornadaResponse)
def get_jornada(
    jornada: Optional[int] = Query(default=None, ge=1, le=99),
    season: Optional[str] = Query(default=None),
):
    """Predicciones de la jornada indicada (o de la próxima completa)."""
    try:
        return get_jornada_predictions(jornada, season)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.exception(f"Error obteniendo la jornada de La Quiniela: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo la jornada de La Quiniela: {exc}",
        )


@router.get("/jornada/{jornada}", response_model=QuinielaJornadaResponse)
def get_jornada_by_number(
    jornada: int,
    season: Optional[str] = Query(default=None),
):
    """Alias de `/jornada` con el número en la ruta."""
    return get_jornada(jornada, season)


def _generate(request: QuinielaGenerateRequest) -> dict:
    try:
        return generate_quiniela(
            jornada=request.jornada,
            season=request.season,
            mode=request.mode,
            budget=request.budget,
            max_doubles=request.max_doubles,
            max_triples=request.max_triples,
            count=request.count,
            strategy=request.strategy,
            seed=request.seed,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(f"Error generando boletos de La Quiniela: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generando boletos de La Quiniela: {exc}",
        )


@router.post("/generate", response_model=QuinielaGenerateResponse)
def generate(request: QuinielaGenerateRequest):
    """
    Genera un boleto múltiple optimizado o una cartera de columnas simples.

    En modo `multiple` se eligen dobles y triples dentro del presupuesto y de
    los límites indicados. En modo `simple` se seleccionan columnas que
    maximizan la probabilidad de que al menos una alcance premio.
    """
    return _generate(request)


@router.get("/generate", response_model=QuinielaGenerateResponse)
def generate_get(
    jornada: Optional[int] = Query(default=None, ge=1, le=99),
    season: Optional[str] = Query(default=None),
    mode: str = Query(default="multiple", pattern="^(multiple|simple)$"),
    budget: float = Query(default=DEFAULT_BUDGET_EUR, ge=0.75, le=1_000),
    max_doubles: int = Query(default=4, ge=0, le=7),
    max_triples: int = Query(default=2, ge=0, le=4),
    count: int = Query(default=1, ge=1, le=10),
    strategy: str = Query(default="balanced"),
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
    request = QuinielaGenerateRequest(
        jornada=jornada,
        season=season,
        mode=mode,  # type: ignore[arg-type]
        budget=budget,
        max_doubles=max_doubles,
        max_triples=max_triples,
        count=count,
        strategy=strategy,  # type: ignore[arg-type]
        seed=seed,
    )
    return _generate(request)


@router.get("/stats", response_model=QuinielaStatsResponse)
def get_stats():
    """Estado del modelo, ligas, mejores equipos y backtest."""
    try:
        manager = get_quiniela_data_manager()
        model = get_quiniela_model()
        return {
            "dataset": model.dataset_summary(),
            "model": {
                "type": "dixon-coles-poisson + elo",
                "version": "1.0",
                "config": {
                    "max_age_days": model.config.max_age_days,
                    "half_life_days": model.config.half_life_days,
                    "regularization": model.config.regularization,
                    "draw_rho": model.config.draw_rho,
                    "elo_k": model.config.elo_k,
                    "elo_home_advantage": model.config.elo_home_advantage,
                },
                "strategies": _strategies_payload(),
                "home_advantage": round(model.home_advantage, 4),
                "global_base": {
                    key: round(value, 4) for key, value in model.global_base.items()
                },
                "next_jornada": manager.summary().get("next_jornada"),
                "explanation": (
                    "Poisson Dixon-Coles con pesos temporales y regularización "
                    "para estimar goles esperados; Elo con diferencia de goles "
                    "para mezclar equipos de ligas distintas; priors de liga "
                    "para equipos sin histórico. La distribución de marcadores "
                    "0-8 por equipo produce P(1), P(X), P(2) y el pleno."
                ),
            },
            "leagues": model.league_stats(),
            "top_teams": model.top_teams(15),
            "backtest": _quick_backtest(),
        }
    except Exception as exc:
        logger.exception(f"Error obteniendo estadísticas de La Quiniela: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo estadísticas de La Quiniela: {exc}",
        )


@router.get("/backtest")
def get_backtest(
    limit: int = Query(default=400, ge=50, le=2_000),
):
    """Evalúa el modelo sobre partidos posteriores al corte de entrenamiento."""
    try:
        matches = get_quiniela_data_manager().load_matches()
        return backtest_model(matches, limit=limit)
    except Exception as exc:
        logger.exception(f"Error calculando el backtest de La Quiniela: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Error calculando el backtest de La Quiniela: {exc}",
        )


@router.get("/history", response_model=list[QuinielaHistoryMatch])
def get_history(
    limit: int = Query(default=50, ge=1, le=500),
):
    """Últimos partidos del histórico usado por el modelo."""
    return get_quiniela_data_manager().history(limit)


@router.get("/teams/{name}", response_model=QuinielaTeamResponse)
def get_team(name: str):
    """Perfil de un equipo: fuerza estimada, forma y últimos partidos."""
    try:
        profile = get_quiniela_model().team_profile(name)
    except Exception as exc:
        logger.exception(f"Error obteniendo el equipo {name}: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo el equipo {name}: {exc}",
        )
    if profile is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No hay histórico suficiente para '{name}'. Puede ser un "
                "equipo de división inferior o de una liga sin datos."
            ),
        )
    recent = profile.pop("recent", [])
    return {"team": profile, "recent": recent}


@router.get("/refresh")
@router.post("/refresh")
def refresh_data(
    scope: str = Query(
        default="fixtures",
        pattern="^(fixtures|matches|all)$",
        description="fixtures: calendario; matches: resultados; all: ambos",
    ),
):
    """Actualiza el calendario y/o los resultados desde fuentes públicas."""
    global _backtest_cache
    manager = get_quiniela_data_manager()
    result: dict[str, object] = {
        "status": "success",
        "updated_at": dt.datetime.now().isoformat(timespec="seconds"),
    }
    try:
        if scope in {"fixtures", "all"}:
            result["fixtures"] = manager.refresh_fixtures()
        if scope in {"matches", "all"}:
            result["matches"] = manager.refresh_matches()
            if result["matches"].get("status") == "success":
                # El histórico cambió: modelo y backtest cacheados ya no valen.
                clear_quiniela_model_cache()
                with _backtest_lock:
                    _backtest_cache = None
        return result
    except Exception as exc:
        logger.error(f"Error actualizando La Quiniela: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Error actualizando La Quiniela: {exc}",
        )
