from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.services.catalog import BLEND, BLEND_MEMBERS, STRATEGY_IDS
from app.services.engine import Params


class PortfolioParams(BaseModel):
    top_fraction: float = Field(0.2, ge=0.1, le=0.5)
    buffer: float = Field(2.0, ge=1.0, le=3.0)
    min_hold: int = Field(2, ge=1, le=5)
    min_score: float | None = None
    sizing: Literal["equal", "score"] = "equal"
    sell_score: float | None = Field(None, ge=-1, le=1)

    def to_engine(self) -> Params:
        kwargs = {} if self.min_score is None else {"min_score": self.min_score}
        return Params(self.top_fraction, self.buffer, self.min_hold, sizing=self.sizing, sell_score=self.sell_score, **kwargs)


def check_strategies(strategies: list[str], blend_weights: dict[str, float]) -> None:
    if set(strategies) - set(STRATEGY_IDS):
        raise ValueError(f"unknown strategies: {sorted(set(strategies) - set(STRATEGY_IDS))}")
    if set(blend_weights) - set(BLEND_MEMBERS):
        raise ValueError(f"unknown blend members: {sorted(set(blend_weights) - set(BLEND_MEMBERS))}")
    if any(not 0 <= weight <= 2 for weight in blend_weights.values()):
        raise ValueError("blend weights must be between 0 and 2")
    if BLEND in strategies and not any(blend_weights.values()):
        raise ValueError("blend needs at least one non-zero weight")
