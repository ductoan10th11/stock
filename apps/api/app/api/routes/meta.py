from fastapi import APIRouter, Request

from app.schemas.meta import Meta, Preset, StrategyInfo
from app.services.catalog import BLEND_MEMBERS, PERIODS, PRESETS, STRATEGIES
from app.services.live import trained_until

router = APIRouter(tags=["meta"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/meta")
def meta(request: Request) -> Meta:
    return Meta(
        strategies=[StrategyInfo(**vars(strategy)) for strategy in STRATEGIES],
        blend_members=list(BLEND_MEMBERS),
        presets=[Preset(id=key, **preset) for key, preset in PRESETS.items()],
        periods=PERIODS,
        backtest_ready=request.app.state.backtest.ready,
        trained_until=f"{trained_until():%Y-%m-%d}",
    )
