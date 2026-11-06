from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from engine import FEE_SCALES, Constraints, Params, benchmark_returns, evaluate, net, random_selection, simulate
from market import OOF_PATH, blend, execution_returns, fill_constraints, load_market
from panel_experiments import CONFIRM_START
from ui import BLEND, STRATEGY_LABELS, portfolio_params, strategy_weights

PRESETS = {
    "Thực tế: mở cửa phiên sau, khoá T+2": ("next_open", 2, 10.0, True),
    "Lý thuyết: đóng cửa, không T+2 (như final_backtest.py)": ("close", 1, 0.0, False),
}
PERIODS = {"Toàn bộ walk-forward": None, "Phát triển (đến hết 2024)": "dev", "Xác nhận (từ 2025)": "confirm"}


@st.cache_resource(show_spinner="Đang tải dữ liệu và dựng alpha...")
def market():
    return load_market()


def build_constraints(mkt, execution: str, capital: float, enabled: bool) -> Constraints | None:
    if not enabled:
        return None
    return Constraints(*fill_constraints(mkt.prices, execution, capital))


@st.cache_data(show_spinner=False)
def run_book(_market, weights: tuple, params: Params, execution: str, capital: float, limits: bool) -> pd.DataFrame:
    signals = _market.signals
    score = blend(signals, dict(weights))
    window = signals["model"].dropna(how="all").index
    returns = execution_returns(_market.prices.open, _market.prices.close, execution)
    score = score.loc[window].loc[returns.reindex(window).notna().any(axis=1)]
    return simulate(score, returns, params, build_constraints(_market, execution, capital, limits))


@st.cache_data(show_spinner=False)
def run_random(_market, params: Params, execution: str, fee_scale: float, slippage: float, capital: float,
               limits: bool, period: str | None) -> dict:
    window = _market.signals["model"].dropna(how="all").index
    returns = execution_returns(_market.prices.open, _market.prices.close, execution)
    availability = _market.signals["model"].loc[window].loc[returns.reindex(window).notna().any(axis=1)]
    return random_selection(returns, slice_period(availability, period), params, fee_scale, slippage,
                            build_constraints(_market, execution, capital, limits))


def slice_period(frame, period: str | None):
    if period == "dev":
        return frame[frame.index < CONFIRM_START]
    if period == "confirm":
        return frame[frame.index >= CONFIRM_START]
    return frame


def index_returns(mkt, execution: str) -> pd.Series:
    return execution_returns(mkt.index["open"], mkt.index["close"], execution)


def wealth(daily: pd.Series) -> pd.Series:
    return (1.0 + daily.fillna(0.0)).cumprod()


COLUMNS = {
    "return_ann": "Lợi suất năm", "total_return": "Tổng lợi suất", "sharpe": "Sharpe", "max_drawdown": "Sụt giảm tối đa",
    "alpha_ann": "Alpha năm", "alpha_ci_low": "Alpha CI thấp", "alpha_ci_high": "Alpha CI cao",
    "alpha_adj_low": "CI thấp (đa kiểm định)", "alpha_adj_high": "CI cao (đa kiểm định)", "beta": "Beta",
    "turnover_per_day": "Vòng quay mua/ngày", "avg_holdings": "Số mã TB",
}


def percent_table(table: pd.DataFrame):
    table = table[list(COLUMNS)].rename(columns=COLUMNS)
    percent = [COLUMNS[c] for c in COLUMNS if c not in ("sharpe", "beta", "avg_holdings")]
    return table.style.format({**{c: "{:.1%}" for c in percent}, "Sharpe": "{:.2f}", "Beta": "{:.2f}",
                               "Số mã TB": "{:.1f}"}, na_rep="-")


st.title("Backtest")
if not OOF_PATH.is_file():
    st.error("Thiếu `results/research/pooled_abs_full/oof.csv.gz`. Chạy: `python scripts/panel_data.py` rồi "
             "`python scripts/panel_experiments.py --name pooled_abs_full --mode pooled --label abs --features full`.")
    st.stop()
mkt = market()

with st.sidebar:
    st.header("Cấu hình backtest")
    preset = st.radio("Kiểu khớp lệnh", list(PRESETS))
    execution, default_hold, default_slippage, default_limits = PRESETS[preset]
    chosen = st.multiselect("Chiến thuật", list(STRATEGY_LABELS), default=["model", "momentum_12_1", "low_volatility"],
                            format_func=STRATEGY_LABELS.get)
    blend_weights = strategy_weights(BLEND, "bt") if BLEND in chosen else {}
    period = PERIODS[st.selectbox("Giai đoạn", list(PERIODS))]
    fee_scale = st.slider("Hệ số phí (1 = mua 0,15%, bán 0,25%)", 0.0, 2.0, 1.0, 0.25)
    slippage = st.slider("Trượt giá mỗi chiều (bps)", 0.0, 50.0, default_slippage, 5.0, key=f"slip_{execution}")
    limits = st.checkbox("Giá trần/sàn ±7% và giới hạn 10% thanh khoản (ADV20)", default_limits, key=f"lim_{execution}")
    capital = st.number_input("Vốn (VND), dùng cho giới hạn thanh khoản", 10_000_000, 100_000_000_000, 1_000_000_000,
                              100_000_000, disabled=not limits)
    params = portfolio_params(f"bt_{execution}", default_hold)

if not chosen:
    st.info("Chọn ít nhất một chiến thuật ở thanh bên.")
    st.stop()
if BLEND in chosen and not any(blend_weights.values()):
    st.warning("Tổ hợp cần ít nhất một trọng số khác 0.")
    st.stop()

books = {}
for name in chosen:
    weights = blend_weights if name == BLEND else {name: 1.0}
    books[name] = slice_period(run_book(mkt, tuple(sorted(weights.items())), params, execution, float(capital), limits), period)

first_book = next(iter(books.values()))
returns = execution_returns(mkt.prices.open, mkt.prices.close, execution)
benchmark = benchmark_returns(returns, first_book.index)
vnindex = index_returns(mkt, execution).reindex(first_book.index).fillna(0.0)

TRIALS = len(STRATEGY_LABELS)
rows = {STRATEGY_LABELS[name]: evaluate(book, benchmark, fee_scale, slippage, TRIALS) for name, book in books.items()}
rows["Cân bằng đều 19 mã (chuẩn so sánh)"] = evaluate(
    first_book.assign(gross=benchmark, buy_turnover=0.0, sell_turnover=0.0, holdings=19), benchmark, 0.0
)
rows["VN-Index mua và giữ"] = evaluate(
    first_book.assign(gross=vnindex, buy_turnover=0.0, sell_turnover=0.0, holdings=1), benchmark, 0.0
)
rows["Chọn ngẫu nhiên (trung vị 30 lần)"] = run_random(mkt, params, execution, fee_scale, slippage, float(capital), limits, period)
table = pd.DataFrame(rows).T.rename_axis("Chiến thuật")

st.caption(f"{first_book.index[0].date()} đến {first_book.index[-1].date()}, {len(first_book)} phiên. "
           f"Phí ×{fee_scale:g}, trượt giá {slippage:g} bps. Tín hiệu mô hình là dự đoán ngoài mẫu của walk-forward, không phải mô hình đã lưu trong `models/`.")
st.dataframe(percent_table(table), width="stretch")

fig = go.Figure()
for name, book in books.items():
    fig.add_scatter(x=book.index, y=wealth(pd.Series(net(book, fee_scale, slippage), index=book.index)),
                    name=STRATEGY_LABELS[name])
fig.add_scatter(x=benchmark.index, y=wealth(benchmark), name="Cân bằng đều 19 mã", line=dict(color="gray", dash="dash"))
fig.add_scatter(x=vnindex.index, y=wealth(vnindex), name="VN-Index", line=dict(color="black", dash="dot"))
fig.update_layout(title="Giá trị tài khoản (bắt đầu 1,0)", yaxis_type="log", height=460, hovermode="x unified")
st.plotly_chart(fig, width="stretch")

drawdown = go.Figure()
for name, book in books.items():
    curve = wealth(pd.Series(net(book, fee_scale, slippage), index=book.index))
    drawdown.add_scatter(x=curve.index, y=curve / curve.cummax() - 1.0, name=STRATEGY_LABELS[name])
drawdown.update_layout(title="Sụt giảm so với đỉnh", yaxis_tickformat=".0%", height=300, hovermode="x unified")
st.plotly_chart(drawdown, width="stretch")

left, right = st.columns(2)
with left:
    st.subheader("Nhạy cảm với phí (alpha ròng năm)")
    sensitivity = pd.DataFrame({
        STRATEGY_LABELS[name]: {f"×{scale:g}": evaluate(book, benchmark, scale, slippage)["alpha_ann"] for scale in FEE_SCALES}
        for name, book in books.items()
    }).T
    st.dataframe(sensitivity.style.format("{:.1%}"), width="stretch")
with right:
    st.subheader("Lợi suất theo năm")
    yearly = pd.DataFrame({
        STRATEGY_LABELS[name]: pd.Series(net(book, fee_scale, slippage), index=book.index).groupby(book.index.year)
        .apply(lambda r: np.prod(1.0 + r) - 1.0) for name, book in books.items()
    })
    yearly["Cân bằng đều 19 mã"] = benchmark.groupby(benchmark.index.year).apply(lambda r: np.prod(1.0 + r.fillna(0)) - 1.0)
    st.dataframe(yearly.T.style.format("{:.1%}"), width="stretch")

with st.expander("Giả định và giới hạn"):
    st.markdown(
        "- Mô hình: dự đoán ngoài mẫu của walk-forward (huấn luyện lại mỗi fold, bỏ 1 phiên giữa train và test), "
        "không phải gói `models/ensemble3_pooled_1D` (đã học cả giai đoạn này nên sẽ rò rỉ).\n"
        "- Alpha cổ điển không huấn luyện, nhưng danh sách chiến thuật đã xem trên cùng dữ liệu.\n"
        "- T+2 mô phỏng bằng số phiên giữ tối thiểu. Trượt giá là mức cố định mỗi chiều. Giá trần/sàn: mã mở cửa "
        "kịch trần thì không mua được, kịch sàn thì không bán được (chỉ ở kiểu khớp mở cửa). Thanh khoản: trọng số "
        "mỗi mã bị chặn ở 10% giá trị giao dịch trung bình 20 phiên so với vốn, phần thừa giữ tiền mặt. Chưa mô hình "
        "lô 100 và hàng đợi khớp lệnh.\n"
        "- Cột \"đa kiểm định\" là khoảng tin cậy Bonferroni cho số chiến thuật có sẵn (9). Alpha chỉ đáng tin khi "
        "khoảng này loại được 0.\n"
        "- 19 mã còn niêm yết và có dữ liệu đẹp nên có thiên lệch sống sót. Alpha tính so với trung bình đều 19 mã.\n"
        "- Danh mục cân bằng đều lại mỗi phiên (bỏ qua trôi trọng số), tiền mặt không sinh lãi."
    )
