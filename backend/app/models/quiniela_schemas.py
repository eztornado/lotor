"""Esquemas Pydantic para la API de La Quiniela."""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class QuinielaGenerateRequest(BaseModel):
    jornada: Optional[int] = Field(
        default=None,
        ge=1,
        le=99,
        description="Número de jornada. Si se omite, se usa la próxima completa.",
    )
    season: Optional[str] = Field(
        default=None,
        description="Temporada, por ejemplo 2026/27. Opcional.",
    )
    mode: Literal["multiple", "simple"] = Field(
        default="multiple",
        description=(
            "multiple: un boleto con dobles/triples; "
            "simple: varias columnas simples independientes."
        ),
    )
    budget: float = Field(
        default=20.0,
        ge=0.75,
        le=1_000.0,
        description="Presupuesto máximo en euros.",
    )
    max_doubles: int = Field(
        default=4,
        ge=0,
        le=7,
        description="Máximo de dobles permitidos en el múltiple.",
    )
    max_triples: int = Field(
        default=2,
        ge=0,
        le=4,
        description="Máximo de triples permitidos en el múltiple.",
    )
    count: int = Field(
        default=1,
        ge=1,
        le=10,
        description="Número de columnas simples (solo en mode='simple').",
    )
    strategy: Literal[
        "balanced", "coverage", "max_probability", "jackpot"
    ] = Field(
        default="balanced",
        description=(
            "balanced: equilibrada; coverage: máxima cobertura; "
            "max_probability: máxima probabilidad; jackpot: caza del pleno."
        ),
    )
    seed: Optional[int] = Field(
        default=None,
        ge=0,
        le=2_147_483_647,
        description="Semilla opcional para reproducir la generación.",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "mode": "multiple",
                "budget": 20,
                "max_doubles": 4,
                "max_triples": 2,
                "strategy": "balanced",
            }
        }
    )


class QuinielaGameInfo(BaseModel):
    name: str
    matches: int
    sign_matches: int
    pleno_match: int
    ticket_price_eur: float
    max_doubles: int
    max_triples: int
    prize_categories: dict[str, str]


class QuinielaJornada(BaseModel):
    season: str
    jornada: int
    label: str
    start_date: str
    matches: int
    competition: str
    competitions: list[str] = Field(default_factory=list)


class QuinielaTicket(BaseModel):
    index: int
    signs: list[dict[str, Any]]
    pleno: dict[str, Any]
    columns: int
    cost: float
    doubles: int
    triples: int
    expected_hits: float
    expected_total_hits: float
    guaranteed_hits: int
    hits_14_distribution: list[float]
    hit_distribution: list[float]
    category_probabilities: dict[str, float]
    prize_estimate: dict[str, Any]
    coverage: list[float]
    expanded_columns: Optional[list[dict[str, Any]]] = None
    expanded_note: Optional[str] = None
    variant: Optional[str] = None


class QuinielaGenerateResponse(BaseModel):
    game: QuinielaGameInfo
    generated_at: str
    seed: int
    mode: str
    strategy: str
    strategy_label: str
    strategy_description: str
    jornada: QuinielaJornada
    budget: dict[str, Any]
    matches: list[dict[str, Any]]
    tickets: list[QuinielaTicket]
    portfolio: dict[str, Any]
    analysis: dict[str, Any]
    recommendations: list[str]
    disclaimer: str


class QuinielaPredictionResponse(QuinielaGenerateResponse):
    alternatives: list[QuinielaTicket]
    model: dict[str, Any]
    target: dict[str, Any]
    reasoning: list[str]


class QuinielaMetaResponse(BaseModel):
    game: QuinielaGameInfo
    dataset: dict[str, Any]
    strategies: dict[str, dict[str, Any]]
    next_jornada: Optional[dict[str, Any]] = None


class QuinielaJornadaResponse(BaseModel):
    jornada: QuinielaJornada
    matches: list[dict[str, Any]]
    pleno: dict[str, Any]
    generated_at: str


class QuinielaStatsResponse(BaseModel):
    dataset: dict[str, Any]
    model: dict[str, Any]
    leagues: list[dict[str, Any]]
    top_teams: list[dict[str, Any]]
    backtest: dict[str, Any]


class QuinielaHistoryMatch(BaseModel):
    date: str
    league: str
    league_name: str
    home_team: str
    away_team: str
    home_goals: int
    away_goals: int
    result: str
    odds: dict[str, Optional[float]] = Field(default_factory=dict)


class QuinielaTeamResponse(BaseModel):
    team: dict[str, Any]
    recent: list[dict[str, Any]]
