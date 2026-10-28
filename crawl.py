"""Crawl nến các mã trong docs/idea.md từ API biểu đồ DNSE (Entrade).

Mỗi khung nến lấy tối đa độ sâu API cho phép (1D từ 2018, 1H ~2 năm, phút ~3 tháng).
Kết quả: data/raw/<khung>/<mã>.csv
"""
import csv
import json
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

SYMBOLS = ["TCB", "CTG", "VNM", "ACB"]
# khung nến -> số ngày lùi lại (vượt độ sâu tối đa thì API tự cắt)
RESOLUTIONS = {"1D": 3650, "1H": 730, "30": 365, "15": 365, "5": 365, "1": 365}
URL = (
    "https://services.entrade.com.vn/chart-api/v2/ohlcs/stock"
    "?from={f}&to={t}&symbol={s}&resolution={r}"
)
OUT = Path(__file__).parent / "data" / "raw"
VN = timezone(timedelta(hours=7))


def fetch(symbol, resolution, start, end):
    url = URL.format(
        f=int(start.timestamp()), t=int(end.timestamp()), s=symbol, r=resolution
    )
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                d = json.load(r)
            break
        except OSError:
            if attempt == 4:
                raise
            time.sleep(3)
    fmt = "%Y-%m-%d" if resolution == "1D" else "%Y-%m-%d %H:%M"
    rows = []
    for i, t in enumerate(d["t"]):
        ts = datetime.fromtimestamp(t, VN).strftime(fmt)
        rows.append([ts, d["o"][i], d["h"][i], d["l"][i], d["c"][i], d["v"][i]])
    return rows


def main():
    end = datetime.now(VN)
    for res, days in RESOLUTIONS.items():
        folder = OUT / res
        folder.mkdir(parents=True, exist_ok=True)
        for s in SYMBOLS:
            rows = fetch(s, res, end - timedelta(days=days), end)
            with open(folder / f"{s}.csv", "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["time", "open", "high", "low", "close", "volume"])
                w.writerows(rows)
            print(f"{res:>3} {s}: {len(rows):6d} nến {rows[0][0]} -> {rows[-1][0]}")


if __name__ == "__main__":
    main()
