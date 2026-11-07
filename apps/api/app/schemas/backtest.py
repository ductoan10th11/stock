from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.common import PortfolioParams, check_strategies


class BacktestRequest(BaseModel):
    strategies: list[str] = Field(min_length=1)
    blend_weights: dict[str, float] = Field(default_factory=dict)
    execution: Literal["next_open", "close"] = "next_open"
    period: Literal["all", "dev", "confirm"] = "all"
    fee_scale: float = Field(1.0, ge=0, le=2)
    slippage_bps: float = Field(10.0, ge=0, le=50)
    limits: bool = True
    capital: float = Field(1e9, ge=1e7, le=1e11)
    params: PortfolioParams = Field(default_factory=PortfolioParams)

    @model_validator(mode="after")
    def check(self):
        check_strategies(self.strategies, self.blend_weights)
        return self


class MetricsRow(BaseModel):
    key: str
    label: str
    kind: Literal["strategy", "benchmark", "random"]
    verdict: Literal["significant", "insufficient", "unknown"] | None = None
    return_ann: float | None = None
    total_return: float | None = None
    sharpe: float | None = None
    max_drawdown: float | None = None
    alpha_ann: float | None = None
    alpha_ci_low: float | None = None
    alpha_ci_high: float | None = None
    alpha_adj_low: float | None = None
    alpha_adj_high: float | None = None
    beta: float | None = None
    avg_holdings: float | None = None
    turnover_per_day: float | None = None


class Curve(BaseModel):
    key: str
    label: str
    color: str
    dash: Literal["solid", "dash", "dot"]
    wealth: list[float | None]
    drawdown: list[float | None]


class TableRow(BaseModel):
    label: str
    values: list[float | None]


class Table(BaseModel):
    columns: list[str]
    rows: list[TableRow]


class BacktestResponse(BaseModel):
    start: str
    end: str
    sessions: int
    dates: list[str]
    metrics: list[MetricsRow]
    curves: list[Curve]
    yearly: Table
    fee_sensitivity: Table
