import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.errors import PaperError
from app.services.backtest import BacktestService
from app.services.market import load_market
from app.services.model_review import ModelReview
from app.services.scheduler import refresh_loop


@asynccontextmanager
async def lifespan(app: FastAPI):
    market = load_market()
    app.state.backtest = BacktestService(market)
    app.state.review = ModelReview(market)
    refresher = asyncio.create_task(refresh_loop()) if os.environ.get("AUTO_REFRESH", "1") == "1" else None
    yield
    if refresher:
        refresher.cancel()


app = FastAPI(title="Stock ML API", lifespan=lifespan)
app.include_router(api_router)


@app.exception_handler(PaperError)
def paper_error_handler(_: Request, error: PaperError) -> JSONResponse:
    return JSONResponse({"detail": error.code}, status_code=409)
