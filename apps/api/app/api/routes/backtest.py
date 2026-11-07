from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_backtest_service, get_review
from app.schemas.backtest import BacktestRequest, BacktestResponse, MetricsRow
from app.schemas.predictions import ReviewList, SymbolPredictions
from app.services.backtest import BacktestService
from app.services.model_review import ModelReview

router = APIRouter(prefix="/backtest", tags=["backtest"])


@router.post("")
def run_backtest(request: BacktestRequest, service: Annotated[BacktestService, Depends(get_backtest_service)]) -> BacktestResponse:
    return service.run(request)


@router.post("/random")
def run_random_baseline(request: BacktestRequest, service: Annotated[BacktestService, Depends(get_backtest_service)]) -> MetricsRow:
    return service.random_baseline(request)


Span = Annotated[Literal["week", "month", "year"] | None, Query()]
Day = Annotated[str | None, Query(pattern=r"^\d{4}-\d{2}-\d{2}$")]
Review = Annotated[ModelReview, Depends(get_review)]


@router.get("/predictions")
def review_list(review: Review, span: Span = None, start: Day = None, end: Day = None) -> ReviewList:
    try:
        return review.listing(span, start, end)
    except ValueError as error:
        raise HTTPException(422, "empty_window") from error


@router.get("/predictions/{symbol}")
def review_symbol(symbol: str, review: Review, span: Span = None, start: Day = None, end: Day = None) -> SymbolPredictions:
    if symbol not in review.market.candles:
        raise HTTPException(404, "unknown_symbol")
    try:
        return review.detail(symbol, span, start, end)
    except ValueError as error:
        raise HTTPException(422, "empty_window") from error
