from fastapi import HTTPException, Request

from app.services.backtest import BacktestService
from app.services.model_review import ModelReview


def get_backtest_service(request: Request) -> BacktestService:
    service: BacktestService = request.app.state.backtest
    if not service.ready:
        raise HTTPException(503, "oof_missing")
    return service


def get_review(request: Request) -> ModelReview:
    return request.app.state.review
