from fastapi import APIRouter, HTTPException, Query

from app.schemas.predictions import LatestPredictions, SymbolPredictions
from app.services import predictions

router = APIRouter(prefix="/predictions", tags=["predictions"])


@router.get("")
def latest() -> LatestPredictions:
    return predictions.latest_predictions()


@router.get("/{symbol}")
def for_symbol(symbol: str, days: int = Query(120, ge=30, le=400)) -> SymbolPredictions:
    if symbol not in predictions.known_symbols():
        raise HTTPException(404, "unknown_symbol")
    return predictions.symbol_predictions(symbol, days)
