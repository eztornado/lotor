"""Esquemas Pydantic para la API de Bonoloto."""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class BonolotoGenerateRequest(BaseModel):
    count: int = Field(
        default=10,
        ge=1,
        le=10,
        description="Número de combinaciones a generar (1-10)",
    )
    strategy: Literal[
        "big_prize", "balanced", "coverage", "statistical"
    ] = Field(
        default="big_prize",
        description=(
            "big_prize: máximo premio; balanced: equilibrada; "
            "coverage: máxima cobertura; statistical: estadística pura"
        ),
    )
    seed: Optional[int] = Field(
        default=None,
        ge=0,
        le=2_147_483_647,
        description="Semilla opcional para reproducir la generación",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "count": 10,
                "strategy": "big_prize",
                "seed": None,
            }
        }
    )


class BonolotoGameInfo(BaseModel):
    name: str
    numbers_per_ticket: int
    max_number: int
    reintegro_range: list[int]
    draw_days: str
    ticket_price_eur: float
    prize_categories: dict[str, str]


class BonolotoCombination(BaseModel):
    index: int
    numbers: list[int]
    reintegro: int
    quality: float
    total_score: float
    popularity: float
    sum: int
    odd: int
    even: int
    low: int
    high: int
    consecutive_pairs: int
    decades: list[int]
    tags: list[str]
    theoretical: dict[str, float]
    quality_grade: str


class BonolotoDataset(BaseModel):
    total_draws: int
    date_range: dict[str, str]
    last_draw: dict[str, Any]
    source: str
    next_draw: str


class BonolotoGenerateResponse(BaseModel):
    game: BonolotoGameInfo
    generated_at: str
    seed: int
    strategy: str
    strategy_label: str
    strategy_description: str
    count: int
    dataset: BonolotoDataset
    combinations: list[BonolotoCombination]
    portfolio: dict[str, Any]
    analysis: dict[str, Any]
    model: dict[str, Any]
    recommendations: list[str]
    disclaimer: str


class BonolotoMetaResponse(BaseModel):
    game: dict[str, Any]
    dataset: dict[str, Any]
    strategies: dict[str, dict[str, str]]
    next_draw: str


class BonolotoStatsResponse(BaseModel):
    dataset: dict[str, Any]
    analysis: dict[str, Any]
    model: dict[str, Any]


class BonolotoHistoryDraw(BaseModel):
    date: str
    numbers: list[int]
    complementario: Optional[int] = None
    reintegro: Optional[int] = None
    source: str = "local"
