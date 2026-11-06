from __future__ import annotations

import json
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from market import MODEL_DIR, ROOT, alpha_scores, blend, wide_prices
from paper import DEFAULT_SLIPPAGE_BPS, STATE_PATH, advance, load_account, new_account, next_orders, save_account
from crawl import VN, fetch
from predict_daily import CANDLE_COLUMNS, crawl_universe, load_cleaned_universe, score_latest, update_log
from train_final_model import load_bundle
from ui import STRATEGY_LABELS, portfolio_params, strategy_weights

LIVE_DIR = ROOT / "data" / "live" / "raw" / "1D"
INDEX_PATH = ROOT / "data" / "live" / "raw" / "index" / "1D" / "VNINDEX.csv"
LOG_PATH = ROOT / "results" / "live" / "predictions_log.csv"
CRAWL_DAYS = 700
MIN_SCORED_DAYS = 5


def trained_until() -> pd.Timestamp:
    return pd.Timestamp(json.loads((MODEL_DIR / "metadata.json").read_text())["trained_until"])


def load_live():
    symbols = json.loads((MODEL_DIR / "metadata.json").read_text())["symbols"]
    if not all((LIVE_DIR / f"{s}.csv").is_file() for s in symbols):
        return None
    return load_cleaned_universe(symbols, LIVE_DIR)


def refresh_live() -> None:
    bundle = load_bundle(MODEL_DIR)
    symbols = bundle["metadata"]["symbols"]
    crawl_universe(symbols, LIVE_DIR, CRAWL_DAYS)
    end = datetime.now(VN)
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(fetch("VNINDEX", "1D", end - timedelta(days=CRAWL_DAYS), end, "index"), columns=CANDLE_COLUMNS).to_csv(
        INDEX_PATH, index=False)
    universe = load_cleaned_universe(symbols, LIVE_DIR)
    last_logged = pd.read_csv(LOG_PATH, parse_dates=["time"])["time"].max() if LOG_PATH.is_file() else None
    latest = max(frame["time"].max() for frame in universe.values())
    days = MIN_SCORED_DAYS if last_logged is None else max(MIN_SCORED_DAYS, (latest - last_logged).days + 3)
    update_log(LOG_PATH, score_latest(bundle, universe, days))


def live_score(universe: dict, weights: dict[str, float]) -> pd.DataFrame:
    signals = alpha_scores(universe)
    if LOG_PATH.is_file():
        log = pd.read_csv(LOG_PATH, parse_dates=["time"])
        model = log.pivot(index="time", columns="symbol", values="score")
        signals["model"] = model[model.index > trained_until()].reindex(index=signals["low_volatility"].index,
                                                                         columns=signals["low_volatility"].columns)
    if "model" in weights and weights["model"] and "model" not in signals:
        return pd.DataFrame()
    return blend(signals, weights)


st.title("Paper trading")
universe = load_live()
account = load_account()

head, action = st.columns([3, 1])
with head:
    st.caption(f"Mô hình huấn luyện đến {trained_until().date()}; chỉ dùng tín hiệu của các phiên sau ngày này (trước đó là trong mẫu). "
               "Lệnh khớp ở giá mở cửa phiên kế tiếp cộng trượt giá, lô 100, mua tối đa 10% khối lượng trung bình 20 phiên, "
               "không mua mã kịch trần và không bán mã kịch sàn, phí mua 0,15% và bán 0,25%, khoá T+2 theo số phiên giữ tối thiểu.")
with action:
    refresh = st.button("Cập nhật dữ liệu và chạy phiên mới", type="primary", width="stretch")

if refresh:
    try:
        with st.spinner("Tải nến và chấm điểm 19 mã..."):
            refresh_live()
        universe = load_live()
        if account:
            prices = wide_prices(universe)
            sessions = advance(account, live_score(universe, account["weights"]), prices)
            save_account(account)
            st.success(f"Đã xử lý {sessions} phiên mới.")
        else:
            st.success("Đã cập nhật dữ liệu.")
    except Exception as error:
        st.error(f"Cập nhật thất bại: {error}")

if universe is None:
    st.info("Chưa có dữ liệu trực tiếp. Bấm nút cập nhật ở trên (cần mạng).")
    st.stop()

prices = wide_prices(universe)
latest = prices.close.index[-1]

if account is None:
    st.subheader("Tạo tài khoản giả lập")
    strategy = st.selectbox("Chiến thuật", list(STRATEGY_LABELS), format_func=STRATEGY_LABELS.get)
    weights = strategy_weights(strategy, "pt")
    params = portfolio_params("pt", 2)
    capital = st.number_input("Vốn ban đầu (VND)", 10_000_000, 100_000_000_000, 1_000_000_000, 100_000_000)
    slippage = st.slider("Trượt giá mỗi chiều (bps)", 0.0, 50.0, DEFAULT_SLIPPAGE_BPS, 5.0, key="pt_slippage")
    uses_model = bool(weights.get("model"))
    if not any(weights.values()):
        st.warning("Cần ít nhất một trọng số khác 0.")
    elif uses_model and latest <= trained_until():
        st.warning(f"Phiên mới nhất {latest.date()} chưa sau ngày huấn luyện {trained_until().date()}. "
                   "Chờ phiên đóng cửa kế tiếp hoặc chọn chiến thuật alpha không dùng mô hình.")
    elif st.button(f"Bắt đầu từ phiên {latest.date()} (lệnh đầu vào phiên kế tiếp)"):
        save_account(new_account(weights, params, float(capital), str(latest.date()), slippage))
        st.rerun()
    st.stop()

weights = account["weights"]
score = live_score(universe, weights)
if score.empty:
    st.warning("Thiếu nhật ký dự đoán của mô hình. Bấm nút cập nhật.")
    st.stop()
signal_date = score.dropna(how="all").index.max()
if signal_date < latest:
    st.warning(f"Tín hiệu mới nhất là {signal_date.date()}, nến mới nhất là {latest.date()}. Bấm cập nhật để chấm điểm phiên còn thiếu.")

strategy_name = " + ".join(f"{STRATEGY_LABELS[n]} ×{w:g}" for n, w in weights.items() if w)
st.write(f"**Chiến thuật:** {strategy_name} · bắt đầu {account['start_date']} · vốn {account['initial_capital']:,.0f} VND")

equity = pd.DataFrame(account["equity"])
if equity.empty:
    st.info("Chưa có phiên nào được xử lý. Phiên kế tiếp sau khi có nến mới, bấm cập nhật.")
else:
    equity["date"] = pd.to_datetime(equity["date"])
    equity = equity.set_index("date")
    benchmark = prices.close.pct_change().mean(axis=1).loc[equity.index].add(1).cumprod()
    vnindex = None
    if INDEX_PATH.is_file():
        index_close = pd.read_csv(INDEX_PATH, parse_dates=["time"]).set_index("time")["close"]
        vnindex = index_close.pct_change().reindex(equity.index).fillna(0.0).add(1).cumprod()
    last = equity.iloc[-1]
    cols = st.columns(5)
    cols[0].metric("Giá trị tài khoản", f"{last['equity']:,.0f}", f"{last['equity'] / account['initial_capital'] - 1:+.2%}")
    cols[1].metric("Tiền mặt", f"{last['cash']:,.0f}")
    cols[2].metric("Cân bằng đều 19 mã cùng kỳ", f"{benchmark.iloc[-1] - 1:+.2%}")
    cols[3].metric("VN-Index cùng kỳ", "-" if vnindex is None else f"{vnindex.iloc[-1] - 1:+.2%}")
    cols[4].metric("Phiên cuối đã xử lý", account["last_date"])
    fig = go.Figure()
    fig.add_scatter(x=equity.index, y=equity["equity"] / account["initial_capital"], name="Tài khoản")
    fig.add_scatter(x=benchmark.index, y=benchmark, name="Cân bằng đều 19 mã", line=dict(color="gray", dash="dash"))
    if vnindex is not None:
        fig.add_scatter(x=vnindex.index, y=vnindex, name="VN-Index", line=dict(color="black", dash="dot"))
    fig.update_layout(title="Giá trị tài khoản (bắt đầu 1,0)", height=360, hovermode="x unified")
    st.plotly_chart(fig, width="stretch")

left, right = st.columns(2)
with left:
    st.subheader("Vị thế hiện tại")
    last_close = prices.close.ffill().iloc[-1]
    positions = pd.DataFrame(
        [{"Mã": s, "Số CP": p["shares"], "Giá vốn": p["cost"], "Giá đóng cửa": last_close[s],
          "Lãi lỗ": last_close[s] / p["cost"] - 1, "Số phiên giữ": p["held"]} for s, p in account["positions"].items()]
    )
    st.dataframe(positions.style.format({"Số CP": "{:,.0f}", "Giá vốn": "{:.2f}", "Giá đóng cửa": "{:.2f}", "Lãi lỗ": "{:+.1%}"})
                 if len(positions) else positions, width="stretch", hide_index=True)
with right:
    st.subheader("Lệnh dự kiến cho phiên kế tiếp")
    orders = next_orders(account, score, prices)
    st.dataframe(orders.rename(columns={"symbol": "Mã", "action": "Lệnh", "shares": "Số CP", "est_price": "Giá ước tính"}),
                 width="stretch", hide_index=True)

st.subheader(f"Tín hiệu của phiên {signal_date.date()}")
signals = score.loc[signal_date].dropna().sort_values(ascending=False).rename("Điểm").to_frame()
signals.insert(0, "Hạng", range(1, len(signals) + 1))
st.dataframe(signals.style.format({"Điểm": "{:.3f}"}), width="stretch")

with st.expander("Lịch sử lệnh"):
    trades = pd.DataFrame(account["trades"])
    st.dataframe(trades, width="stretch", hide_index=True)
    if len(trades):
        st.download_button("Tải CSV", trades.to_csv(index=False), "paper_trades.csv", "text/csv")
with st.expander("Xoá tài khoản"):
    if st.checkbox("Xác nhận xoá toàn bộ lịch sử tài khoản giả lập") and st.button("Xoá"):
        STATE_PATH.unlink()
        st.rerun()
