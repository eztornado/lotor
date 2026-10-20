"""Esquemas Pydantic para la API de El Gordo de la Primitiva."""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class GordoGenerateRequest(BaseModel):
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


class GordoGameInfo(BaseModel):
    name: str
    numbers_per_ticket: int
    max_number: int
    key_range: list[int]
    draw_days: str
    ticket_price_eur: float
    prize_categories: dict[str, str]


class GordoCombination(BaseModel):
    index: int
    numbers: list[int]
    key_number: int
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


class GordoDataset(BaseModel):
    total_draws: int
    date_range: dict[str, str]
    last_draw: dict[str, Any]
    source: str
    next_draw: str


class GordoGenerateResponse(BaseModel):
    game: GordoGameInfo
    generated_at: str
    seed: int
    strategy: str
    strategy_label: str
    strategy_description: str
    count: int
    dataset: GordoDataset
    combinations: list[GordoCombination]
    portfolio: dict[str, Any]
    analysis: dict[str, Any]
    model: dict[str, Any]
    recommendations: list[str]
    disclaimer: str


class GordoMetaResponse(BaseModel):
    game: dict[str, Any]
    dataset: dict[str, Any]
    strategies: dict[str, dict[str, str]]
    next_draw: str


class GordoStatsResponse(BaseModel):
    dataset: dict[str, Any]
    analysis: dict[str, Any]
    model: dict[str, Any]


class GordoHistoryDraw(BaseModel):
    date: str
    numbers: list[int]
    key_number: Optional[int] = None
    source: str = "local"
