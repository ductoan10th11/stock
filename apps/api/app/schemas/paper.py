from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.common import PortfolioParams, check_strategies


class PaperCreateRequest(BaseModel):
    strategy: str
    blend_weights: dict[str, float] = Field(default_factory=dict)
    capital: float = Field(1e9, ge=1e7, le=1e11)
    slippage_bps: float = Field(10.0, ge=0, le=50)
    params: PortfolioParams = Field(default_factory=PortfolioParams)
    replay: bool = False

    @model_validator(mode="after")
    def check(self):
        check_strategies([self.strategy], self.blend_weights)
        return self


class AccountInfo(BaseModel):
    id: int
    replay: bool
    weights: dict[str, float]
    params: PortfolioParams
    initial_capital: float
    slippage_bps: float
    start_date: str
    last_date: str


class Summary(BaseModel):
    equity: float
    cash: float
    gain: float
    gain_pct: float
    cash_pct: float
    equal_weight_return: float | None
    vnindex_return: float | None


class EquityCurve(BaseModel):
    dates: list[str]
    account: list[float]
    equal_weight: list[float]
    vnindex: list[float] | None


class Order(BaseModel):
    symbol: str
    action: Literal["buy", "sell", "hold"]
    shares: int
    price: float
    value: float


class Position(BaseModel):
    symbol: str
    shares: int
    cost: float
    price: float
    pnl_pct: float
    value: float
    held: int


class RankingRow(BaseModel):
    rank: int
    symbol: str
    score: float
    held: bool


class Trade(BaseModel):
    date: str
    symbol: str
    side: Literal["buy", "sell"]
    shares: int
    price: float
    value: float
    fee: float
    entry_price: float | None = None
    entry_value: float | None = None
    pnl: float | None = None
    pnl_pct: float | None = None


class PaperState(BaseModel):
    data_ready: bool
    trained_until: str
    latest_candle: str | None = None
    replay_start: str | None = None
    account: AccountInfo | None = None
    score_ready: bool = False
    signal_date: str | None = None
    summary: Summary | None = None
    equity: EquityCurve | None = None
    orders: list[Order] = []
    positions: list[Position] = []
    ranking: list[RankingRow] = []
    trades: list[Trade] = []


class RefreshResult(BaseModel):
    sessions: int
