from fastapi import APIRouter

from app.api.routes import backtest, meta, paper, predictions

api_router = APIRouter(prefix="/api")
for module in (meta, backtest, paper, predictions):
    api_router.include_router(module.router)
