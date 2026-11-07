from pydantic import BaseModel


class StrategyInfo(BaseModel):
    id: str
    label: str
    help: str
    color: str


class Preset(BaseModel):
    id: str
    label: str
    description: str
    min_hold: int
    slippage_bps: float
    limits: bool


class Meta(BaseModel):
    strategies: list[StrategyInfo]
    blend_members: list[str]
    presets: list[Preset]
    periods: dict[str, str]
    backtest_ready: bool
    trained_until: str | None
