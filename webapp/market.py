"""Loading prices, model scores and alpha signals shared by the backtest and paper-trading pages."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from panel_data import featurize, load_index, load_universe  # noqa: E402

OOF_PATH = ROOT / "results" / "research" / "pooled_abs_full" / "oof.csv.gz"
MODEL_DIR = ROOT / "models" / "ensemble3_pooled_1D"
MODEL_NAME = "ensemble3"

SIGNAL_LABELS = {
    "model": "Mô hình ensemble3 (p_up − p_down)",
    "momentum_12_1": "Động lượng 12−1 tháng",
    "momentum_60d": "Động lượng 60 phiên",
    "reversal_5d": "Đảo chiều 5 phiên",
    "low_volatility": "Biến động thấp (60 phiên)",
    "rsi_reversion": "Đảo chiều RSI14",
    "near_high_60d": "Gần đỉnh 60 phiên",
    "price_volume_corr": "Tương quan giá mở cửa và khối lượng (Alpha#6)",
}
PRICE_LIMIT = 0.07
ADV_WINDOW = 20
ADV_PARTICIPATION = 0.10
PRICE_UNIT = 1000
EXECUTION_MODES = {
    "next_open": "Thực tế: vào ở giá mở cửa phiên sau",
    "close": "Lý thuyết: vào ở giá đóng cửa hôm tín hiệu (như final_backtest.py)",
}


@dataclass
class Prices:
    open: pd.DataFrame
    close: pd.DataFrame
    volume: pd.DataFrame


def wide_prices(universe: dict[str, pd.DataFrame]) -> Prices:
    frames = {symbol: frame.set_index("time") for symbol, frame in universe.items()}
    return Prices(**{column: pd.DataFrame({s: f[column] for s, f in frames.items()}).sort_index()
                     for column in ("open", "close", "volume")})


def execution_returns(open_: pd.DataFrame, close: pd.DataFrame, mode: str) -> pd.DataFrame:
    if mode == "close":
        return close.shift(-1) / close - 1.0
    return open_.shift(-2) / open_.shift(-1) - 1.0


def tick_size(price):
    return np.where(price < 10, 0.01, np.where(price < 50, 0.05, 0.1))


def limit_band(reference):
    """HOSE daily price band (ceiling, floor) from the reference close, rounded to the tick size."""
    tick = tick_size(reference)
    return np.floor(reference * (1 + PRICE_LIMIT) / tick + 1e-9) * tick, np.ceil(reference * (1 - PRICE_LIMIT) / tick - 1e-9) * tick


def adv_shares(prices: Prices) -> pd.DataFrame:
    return prices.volume.rolling(ADV_WINDOW).mean()


def fill_constraints(prices: Prices, execution: str, capital: float, participation: float = ADV_PARTICIPATION):
    """Constraints indexed by signal date: price-limit locks on the next open and a per-name ADV capacity."""
    capacity = participation * adv_shares(prices) * prices.close * PRICE_UNIT / capital
    if execution != "next_open":
        return None, None, capacity
    ceiling, floor = limit_band(prices.close)
    next_open = prices.open.shift(-1)
    return next_open >= ceiling - 1e-6, next_open <= floor + 1e-6, capacity


def alpha_scores(universe: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Classic cross-sectional alphas; higher score means more attractive. Built on the repo's own features."""
    prices = wide_prices(universe)
    panel = featurize(universe)

    def feature(column: str, sign: float = 1.0) -> pd.DataFrame:
        return sign * panel.pivot(index="time", columns="symbol", values=column)

    signals = {
        "momentum_12_1": prices.close.shift(21) / prices.close.shift(252) - 1.0,
        "momentum_60d": feature("ret_60"),
        "reversal_5d": feature("ret_5", -1.0),
        "low_volatility": feature("volat_60", -1.0),
        "rsi_reversion": feature("rsi14", -1.0),
        "near_high_60d": feature("dist_high_60"),
        "price_volume_corr": -prices.open.rolling(10).corr(prices.volume),
    }
    return {name: frame.reindex(index=prices.close.index, columns=prices.close.columns) for name, frame in signals.items()}


def model_scores_from_oof(path: Path = OOF_PATH) -> pd.DataFrame:
    oof = pd.read_csv(path, parse_dates=["time"])
    frame = oof[oof["model"] == MODEL_NAME]
    return (frame["p_up"] - frame["p_down"]).groupby([frame["time"], frame["symbol"]]).first().unstack("symbol")


def blend(signals: dict[str, pd.DataFrame], weights: dict[str, float]) -> pd.DataFrame:
    active = {name: weight for name, weight in weights.items() if weight}
    if len(active) == 1:
        return signals[next(iter(active))]
    total, available = 0.0, 0
    for name, weight in active.items():
        frame = signals[name]
        zscore = frame.sub(frame.mean(axis=1), axis=0).div(frame.std(axis=1, ddof=0), axis=0)
        total = total + weight * zscore.fillna(0.0)
        available = available + frame.notna().astype(int)
    return total.where(available > 0)


@dataclass
class Market:
    prices: Prices
    signals: dict[str, pd.DataFrame]
    index: pd.DataFrame


def load_market() -> Market:
    universe = load_universe()
    prices = wide_prices(universe)
    signals = alpha_scores(universe)
    if OOF_PATH.is_file():
        signals["model"] = model_scores_from_oof().reindex(index=prices.close.index, columns=prices.close.columns)
    index = load_index().set_index("time")
    return Market(prices, signals, index)
