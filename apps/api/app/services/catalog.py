"""Strategy catalog and execution presets: the single source for labels, help text and colors the web app shows."""

from __future__ import annotations

from dataclasses import dataclass

BLEND = "blend"
MODEL = "model"


@dataclass(frozen=True)
class Strategy:
    id: str
    label: str
    help: str
    color: str


STRATEGIES = (
    Strategy(MODEL, "Mô hình AI (ensemble3)",
             "Ba mô hình học máy (Logistic, Random Forest, XGBoost) chấm điểm khả năng tăng giá của từng mã. Điểm = xác suất tăng trừ xác suất giảm.",
             "#2a78d6"),
    Strategy("momentum_12_1", "Động lượng 12−1 tháng",
             "Mua các mã đã tăng mạnh nhất trong 12 tháng gần đây, bỏ qua tháng cuối.", "#eb6834"),
    Strategy("momentum_60d", "Động lượng 60 phiên",
             "Mua các mã đã tăng mạnh nhất trong 60 phiên gần đây.", "#6250d6"),
    Strategy("reversal_5d", "Đảo chiều 5 phiên",
             "Mua các mã vừa giảm mạnh nhất trong 5 phiên, kỳ vọng hồi phục.", "#e87ba4"),
    Strategy("low_volatility", "Biến động thấp",
             "Mua các mã có giá ít biến động nhất trong 60 phiên.", "#1baf7a"),
    Strategy("rsi_reversion", "Đảo chiều RSI14",
             "Mua các mã có chỉ báo RSI14 thấp nhất, tức đang bị bán quá đà.", "#008300"),
    Strategy("near_high_60d", "Gần đỉnh 60 phiên",
             "Mua các mã đang có giá gần đỉnh 60 phiên.", "#eda100"),
    Strategy("price_volume_corr", "Giá và khối lượng ngược pha (Alpha#6)",
             "Mua các mã có giá mở cửa và khối lượng ít đồng pha nhất trong 10 phiên.", "#e34948"),
    Strategy(BLEND, "Tổ hợp nhiều chiến thuật",
             "Cộng điểm đã chuẩn hoá của nhiều chiến thuật theo trọng số bạn chọn.", "#9a6b3f"),
)
STRATEGY_BY_ID = {strategy.id: strategy for strategy in STRATEGIES}
STRATEGY_IDS = tuple(STRATEGY_BY_ID)
BLEND_MEMBERS = tuple(s.id for s in STRATEGIES if s.id != BLEND)

EQUAL_WEIGHT_LABEL = "Cân bằng đều 19 mã"
EQUAL_WEIGHT_COLOR = "#8a8a85"
VNINDEX_LABEL = "VN-Index"
VNINDEX_COLOR = "#b3b3ad"
RANDOM_LABEL = "Chọn ngẫu nhiên (trung vị 30 lần)"

PRESETS = {
    "next_open": {
        "label": "Thực tế",
        "description": "Vào lệnh ở giá mở cửa phiên sau, giữ tối thiểu 2 phiên, có trượt giá, giá trần/sàn và giới hạn thanh khoản.",
        "min_hold": 2, "slippage_bps": 10.0, "limits": True,
    },
    "close": {
        "label": "Lý thuyết",
        "description": "Vào lệnh ở giá đóng cửa ngày có tín hiệu, không có ràng buộc nào (như final_backtest.py). Kết quả đẹp hơn thực tế.",
        "min_hold": 1, "slippage_bps": 0.0, "limits": False,
    },
}
PERIODS = {
    "all": "Toàn bộ walk-forward",
    "dev": "Phát triển (đến hết 2024)",
    "confirm": "Xác nhận (từ 2025)",
}
