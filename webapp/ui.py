"""Widgets shared by both pages."""

from __future__ import annotations

import numpy as np
import streamlit as st

from engine import Params
from market import SIGNAL_LABELS

BLEND = "blend"
STRATEGY_LABELS = {**{name: label for name, label in SIGNAL_LABELS.items()}, BLEND: "Tổ hợp (z-score có trọng số)"}


def strategy_weights(strategy: str, key: str) -> dict[str, float]:
    if strategy != BLEND:
        return {strategy: 1.0}
    weights = {}
    with st.expander("Trọng số tổ hợp", expanded=True):
        for name, label in SIGNAL_LABELS.items():
            weights[name] = st.slider(label, 0.0, 2.0, 1.0, 0.25, key=f"{key}_{name}")
    return weights


def portfolio_params(key: str, default_min_hold: int) -> Params:
    top_fraction = st.slider("Tỷ lệ số mã nắm giữ", 0.10, 0.50, 0.20, 0.05, key=f"{key}_top")
    buffer = st.slider("Vùng đệm giữ vị thế (1 = chọn lại mỗi ngày)", 1.0, 3.0, 2.0, 0.5, key=f"{key}_buffer")
    min_hold = st.slider("Số phiên giữ tối thiểu (T+2 = 2)", 1, 5, default_min_hold, key=f"{key}_hold")
    use_threshold = st.checkbox("Chỉ mua khi điểm vượt ngưỡng (còn lại giữ tiền mặt)", key=f"{key}_use_threshold")
    min_score = st.slider("Ngưỡng điểm (mô hình: p_up − p_down; còn lại: z-score)", 0.0, 1.5, 0.1, 0.05,
                          key=f"{key}_threshold", disabled=not use_threshold)
    return Params(top_fraction, buffer, min_hold, min_score if use_threshold else -np.inf)
