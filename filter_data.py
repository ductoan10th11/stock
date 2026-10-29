"""Filter Vietnamese bank stocks and create leak-free model data."""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
DEFAULT_SYMBOLS = ("TCB", "CTG", "VNM", "ACB")
BANK_SYMBOLS = {
    "VCB", "BID", "CTG", "TCB", "MBB", "VPB", "ACB", "STB", "HDB", "TPB", "VIB", "SHB"
}
PRICE_COLUMNS = ("open", "high", "low", "close")
NUMERIC_COLUMNS = (*PRICE_COLUMNS, "volume")


def load_raw_files(input_dir: Path, symbols: tuple[str, ...]) -> tuple[pd.DataFrame, dict[str, int]]:
    frames = []
    source_rows = {}

    for symbol in symbols:
        path = input_dir / f"{symbol}.csv"
        if not path.is_file():
            raise FileNotFoundError(f"Input file not found: {path}")

        data = pd.read_csv(path)
        data.columns = data.columns.str.strip().str.lower()
        data = data.rename(columns={"time": "date"})
        required = {"date", *NUMERIC_COLUMNS}
        missing = sorted(required - set(data.columns))
        if missing:
            raise ValueError(f"{path} is missing columns: {', '.join(missing)}")

        data = data.loc[:, ["date", *NUMERIC_COLUMNS]].copy()
        data.insert(0, "ticker", symbol)
        frames.append(data)
        source_rows[symbol] = len(data)

    return pd.concat(frames, ignore_index=True), source_rows


def rsi_wilder(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    loss = -delta.clip(upper=0).ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    relative_strength = gain / loss.replace(0, np.nan)
    rsi = 100 - 100 / (1 + relative_strength)
    return rsi.fillna(100).where(gain.notna()) / 100


def add_features(data: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    featured = data.copy()
    grouped = featured.groupby("ticker", sort=False, group_keys=False)

    for period in (1, 5, 20):
        featured[f"ret_{period}d"] = grouped["close"].transform(
            lambda values, lag=period: np.log(values / values.shift(lag))
        )

    featured["volatility_10"] = grouped["ret_1d"].transform(
        lambda values: values.rolling(10, min_periods=10).std()
    )
    featured["volatility_20"] = grouped["ret_1d"].transform(
        lambda values: values.rolling(20, min_periods=20).std()
    )

    for period in (5, 10, 20, 60):
        moving_average = grouped["close"].transform(
            lambda values, window=period: values.rolling(window, min_periods=window).mean()
        )
        featured[f"close_ma{period}"] = featured["close"] / moving_average - 1

    featured["rsi14"] = grouped["close"].transform(rsi_wilder)
    ema12 = grouped["close"].transform(lambda values: values.ewm(span=12, adjust=False).mean())
    ema26 = grouped["close"].transform(lambda values: values.ewm(span=26, adjust=False).mean())
    featured["macd"] = (ema12 - ema26) / featured["close"]
    featured["macd_signal"] = featured.groupby("ticker", sort=False)["macd"].transform(
        lambda values: values.ewm(span=9, adjust=False).mean()
    )
    volume_ma20 = grouped["volume"].transform(
        lambda values: values.rolling(20, min_periods=20).mean()
    )
    featured["volume_ma20"] = featured["volume"] / volume_ma20
    featured["hl_range"] = (featured["high"] - featured["low"]) / featured["close"]

    next_close = grouped["close"].shift(-1)
    featured["target"] = (next_close > featured["close"]).astype("Int8").where(next_close.notna())

    feature_columns = [
        "ret_1d", "ret_5d", "ret_20d", "volatility_10", "volatility_20",
        "close_ma5", "close_ma10", "close_ma20", "close_ma60", "rsi14",
        "macd", "macd_signal", "volume_ma20", "hl_range",
    ]
    return featured, feature_columns


def filter_bank_data(
    raw: pd.DataFrame,
    minimum_sessions: int = 250,
) -> tuple[pd.DataFrame, dict[str, object]]:
    data = raw.copy()
    rows_before = len(data)
    source_last_date = pd.to_datetime(data["date"], errors="coerce").max().strftime("%Y-%m-%d")
    requested_symbols = list(dict.fromkeys(data["ticker"]))
    excluded_non_bank = [symbol for symbol in requested_symbols if symbol not in BANK_SYMBOLS]
    data = data.loc[data["ticker"].isin(BANK_SYMBOLS)].copy()
    rows_after_bank_filter = len(data)

    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    data[list(NUMERIC_COLUMNS)] = data[list(NUMERIC_COLUMNS)].apply(pd.to_numeric, errors="coerce")
    data = data.sort_values(["ticker", "date"], kind="stable")

    symbol_sizes = data.groupby("ticker").size()
    excluded_short = symbol_sizes[symbol_sizes < minimum_sessions].index.tolist()
    data = data.loc[~data["ticker"].isin(excluded_short)].copy()

    duplicate_rows_removed = int(data.duplicated(["ticker", "date"]).sum())
    data = data.drop_duplicates(["ticker", "date"], keep="last")

    missing_cells_before = int(data[["date", *NUMERIC_COLUMNS]].isna().sum().sum())
    data[list(NUMERIC_COLUMNS)] = data.groupby("ticker", sort=False)[list(NUMERIC_COLUMNS)].ffill(limit=2)
    invalid_required = data[["date", *NUMERIC_COLUMNS]].isna().any(axis=1)
    missing_rows_removed = int(invalid_required.sum())
    data = data.loc[~invalid_required].copy()

    invalid_price = (data[list(PRICE_COLUMNS)] <= 0).any(axis=1)
    invalid_price_rows_removed = int(invalid_price.sum())
    data = data.loc[~invalid_price].copy()

    no_trade = data["volume"] <= 0
    no_trade_rows_removed = int(no_trade.sum())
    data = data.loc[~no_trade].copy()
    data = data.sort_values(["ticker", "date"], kind="stable").reset_index(drop=True)

    grouped = data.groupby("ticker", sort=False, group_keys=False)
    daily_return = grouped["close"].pct_change(fill_method=None)
    acb_hnx = (data["ticker"] == "ACB") & (data["date"] < pd.Timestamp("2021-01-01"))
    price_limit = pd.Series(np.where(acb_hnx, 0.10, 0.07), index=data.index)
    data["ohlc_invalid"] = (
        (data["high"] < data["low"])
        | (data["open"] > data["high"])
        | (data["close"] > data["high"])
        | (data["open"] < data["low"])
        | (data["close"] < data["low"])
    )
    data["limit_hit"] = daily_return.abs() >= price_limit - 0.0005
    data["outlier"] = data["ohlc_invalid"] | (daily_return.abs() > price_limit + 0.0005)

    featured, feature_columns = add_features(data)
    ready = featured[feature_columns].replace([np.inf, -np.inf], np.nan).notna().all(axis=1)
    ready &= featured["target"].notna()
    warmup_rows_removed = int((~ready).sum())
    final = featured.loc[ready].copy()
    final["target"] = final["target"].astype("int8")
    final["volume"] = final["volume"].astype("int64")
    final["date"] = final["date"].dt.strftime("%Y-%m-%d")
    final = final.reset_index(drop=True)

    report = {
        "rows_before": rows_before,
        "source_last_date": source_last_date,
        "rows_after_bank_filter": rows_after_bank_filter,
        "requested_symbols": requested_symbols,
        "excluded_non_bank": excluded_non_bank,
        "excluded_short": excluded_short,
        "duplicate_rows_removed": duplicate_rows_removed,
        "missing_cells_before": missing_cells_before,
        "missing_rows_removed": missing_rows_removed,
        "invalid_price_rows_removed": invalid_price_rows_removed,
        "no_trade_rows_removed": no_trade_rows_removed,
        "warmup_rows_removed": warmup_rows_removed,
        "rows_after": len(final),
        "feature_columns": feature_columns,
    }
    return final, report


def write_report(
    output_path: Path,
    data: pd.DataFrame,
    report: dict[str, object],
    source_rows: dict[str, int],
) -> None:
    symbol_summary = data.groupby("ticker").agg(
        rows=("target", "size"),
        first_date=("date", "min"),
        last_date=("date", "max"),
        outliers=("outlier", "sum"),
        limit_hits=("limit_hit", "sum"),
    )
    label_summary = (
        data.groupby(["ticker", "target"]).size().unstack(fill_value=0).rename(columns={0: "giảm", 1: "tăng"})
    )
    yearly_labels = data.assign(year=data["date"].str[:4]).groupby(["ticker", "year", "target"]).size()
    yearly_labels = yearly_labels.unstack(fill_value=0).rename(columns={0: "giảm", 1: "tăng"})

    lines = [
        "# Báo cáo lọc dữ liệu cổ phiếu ngân hàng",
        "",
        "## Phạm vi và nguồn dữ liệu",
        "",
        "- Nguồn: API biểu đồ DNSE (Entrade), được lưu trong `data/raw/1D`.",
        f"- Ngày cuối của dữ liệu nguồn: {report['source_last_date']}.",
        f"- Ngày cuối có thể gán nhãn: {max(data['date'])}.",
        f"- Mã đầu vào: {', '.join(report['requested_symbols'])}.",
        f"- Mã bị loại vì không phải ngân hàng: {', '.join(report['excluded_non_bank']) or 'Không có'}.",
        f"- Mã bị loại vì có dưới 250 phiên: {', '.join(report['excluded_short']) or 'Không có'}.",
        "- Đơn vị giá được giữ nguyên theo nguồn: nghìn đồng.",
        "- Trạng thái điều chỉnh cổ tức/chia tách chưa được DNSE xác nhận chính thức; cần xác nhận trước khi diễn giải lợi suất dài hạn.",
        "",
        "## Kết quả lọc",
        "",
        f"- Tổng số dòng thô: {report['rows_before']}.",
        f"- Số dòng sau khi chỉ giữ mã ngân hàng: {report['rows_after_bank_filter']}.",
        f"- Số dòng theo tệp nguồn: {', '.join(f'{key}: {value}' for key, value in source_rows.items())}.",
        f"- Dòng trùng (`ticker`, `date`) đã loại: {report['duplicate_rows_removed']}.",
        f"- Ô thiếu trước forward fill: {report['missing_cells_before']}; dòng còn thiếu sau forward fill tối đa 2 phiên và đã loại: {report['missing_rows_removed']}.",
        f"- Dòng giá không dương đã loại: {report['invalid_price_rows_removed']}.",
        f"- Phiên volume không dương đã loại: {report['no_trade_rows_removed']}.",
        f"- Dòng warm-up hoặc không có nhãn đã loại: {report['warmup_rows_removed']}.",
        f"- Tổng số dòng cuối cùng: {report['rows_after']}.",
        "- Ngoại lai và phiên chạm biên độ được giữ lại, đánh dấu bằng `outlier`, `ohlc_invalid` và `limit_hit`.",
        "",
        "## Thống kê theo mã",
        "",
        "```text",
        symbol_summary.to_string(),
        "```",
        "",
        "## Phân phối nhãn theo mã",
        "",
        "```text",
        label_summary.to_string(),
        "```",
        "",
        "## Phân phối nhãn theo mã và năm",
        "",
        "```text",
        yearly_labels.to_string(),
        "```",
        "",
        "## Kiểm tra rò rỉ",
        "",
        "- Các đặc trưng tại ngày `t` chỉ dùng dữ liệu đến hết ngày `t`.",
        "- `target` dùng giá đóng cửa ngày kế tiếp và không thuộc danh sách đặc trưng.",
        "- `ticker` và `date` chỉ là cột định danh, không tự động đưa vào ma trận đặc trưng.",
        "- Việc chia train/validation/test và fit scaler phải được thực hiện ở bước huấn luyện theo thời gian.",
        "",
        "Kết quả mô hình dự đoán tăng/giảm có độ không chắc chắn cao và không phải khuyến nghị đầu tư.",
    ]
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=ROOT / "data" / "raw" / "1D")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data" / "filtered")
    parser.add_argument("--symbols", nargs="+", default=list(DEFAULT_SYMBOLS))
    parser.add_argument("--minimum-sessions", type=int, default=250)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    raw, source_rows = load_raw_files(args.input_dir, tuple(args.symbols))
    filtered, report = filter_bank_data(raw, args.minimum_sessions)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_path = args.output_dir / "bank_stocks_clean.csv"
    filtered.to_csv(output_path, index=False)
    write_report(args.output_dir / "data_report.md", filtered, report, source_rows)
    print(
        f"Saved {len(filtered)} rows for {filtered['ticker'].nunique()} bank symbols to {output_path}"
    )


if __name__ == "__main__":
    main()
