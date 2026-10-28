# Tiền xử lý dữ liệu

Tài liệu mô tả cách biến dữ liệu nến thô thành bộ đặc trưng và nhãn để huấn luyện mô hình phân loại xu hướng giá (xem đề bài tại [idea.md](idea.md)).

**Phạm vi đã chốt**

| Hạng mục | Lựa chọn |
|---|---|
| Mã cổ phiếu | TCB, CTG, VNM, ACB |
| Khung nến chính | 1D (khung 1H là mở rộng, xem mục 9) |
| Nhãn | 3 lớp: `-1` giảm, `0` ngang, `1` tăng |
| Cách huấn luyện | Mô hình riêng cho từng mã |
| Kiểm định | Walk-forward, cửa sổ mở rộng |

---

## 1. Dữ liệu thô

- **Nguồn:** API biểu đồ của DNSE (Entrade), cùng nguồn với trang `banggia.dnse.com.vn`. Script crawl dữ liệu là [crawl.py](../crawl.py).
- **Vị trí:** `data/raw/1D/<MÃ>.csv`, gồm các cột `time, open, high, low, close, volume`.
- **Đơn vị:** giá tính bằng nghìn đồng, volume tính bằng số cổ phiếu.
- **Giá đã điều chỉnh:** giá có vẻ đã được điều chỉnh theo chia tách và cổ tức, vì không thấy bước nhảy bất thường vượt biên độ sàn.

Phạm vi của tập crawl ngày 2026-10-23:

| Mã | Số nến | Từ | Đến | Ghi chú |
|---|---|---|---|---|
| TCB | 2098 | 2018-06-04 | 2026-10-23 | Niêm yết HOSE từ 06/2018 |
| CTG | 2495 | 2016-10-26 | 2026-10-23 | |
| VNM | 2495 | 2016-10-26 | 2026-10-23 | |
| ACB | 2492 | 2016-10-26 | 2026-10-23 | Trên HNX (biên độ ±10%) đến cuối 2020 |

Đề bài gợi ý 6 tháng dữ liệu. Ta dùng toàn bộ lịch sử khoảng 8–10 năm vì 6 tháng chỉ có ~126 mẫu, quá ít để huấn luyện và kiểm định walk-forward.

## 2. Làm sạch

Các lỗi đã kiểm tra trên dữ liệu thực tế và cách xử lý:

| Kiểm tra | Kết quả | Cách xử lý |
|---|---|---|
| Thứ tự thời gian | Đã tăng dần | Vẫn sắp xếp lại theo `time` để đảm bảo |
| Ngày trùng | Ngày 2022-12-27 bị tách thành 2 nến (lỗi nguồn) ở cả 4 mã | Gộp các nến cùng ngày: `open` của nến đầu, `high` lớn nhất, `low` nhỏ nhất, `close` của nến cuối, `volume` cộng dồn |
| OHLC sai logic (`open`/`close` ngoài khoảng `[low, high]`) | TCB 2019-07-18; VNM 2019-07-15 và 2019-08-30 | Kẹp lại: `high = max(o, h, c)`, `low = min(o, l, c)` |
| Volume bằng 0 | Không có | Nếu có thì bỏ dòng đó (ngày không giao dịch) |
| Giá trị thiếu | Không có | Nếu có thì bỏ dòng, không nội suy |
| Biến động bất thường (vượt biên độ sàn) | ACB có 12 phiên >7.5% đến 06/2020, đều nằm trong biên ±10% của HNX | Giữ nguyên |
| Nến chưa đóng | Nến ngày hiện tại khi crawl trong giờ giao dịch | Bỏ nến của ngày hiện tại nếu crawl trước 15:00 |

## 3. Nhãn

Lợi suất log của phiên kế tiếp:

```
r_next(t) = ln(close[t+1] / close[t])
```

Gán nhãn với ngưỡng θ = 0.5%:

```
label(t) =  1   nếu r_next(t) >  θ
label(t) = -1   nếu r_next(t) < -θ
label(t) =  0   còn lại
```

**Lý do chọn θ = 0.5%:** độ lệch chuẩn lợi suất ngày của 4 mã là 1.5–2.1%. Với θ = 0.5%, ba lớp gần cân bằng như bảng dưới. Ngưỡng này cũng xấp xỉ chi phí một vòng mua bán (phí và thuế), nên lớp "ngang" tương ứng với những biến động không đủ để có lãi.

| Mã | Giảm | Ngang | Tăng |
|---|---|---|---|
| TCB | 34% | 30% | 36% |
| CTG | 36% | 28% | 36% |
| VNM | 33% | 37% | 30% |
| ACB | 31% | 34% | 34% |

So sánh: θ = 0.3% làm lớp "ngang" chỉ còn ~20%, còn θ = 0.2% thì còn ~15%.

**Lưu ý:**
- Dòng cuối cùng không có `close[t+1]` nên không có nhãn và bị loại.
- XGBoost yêu cầu nhãn là `0..K-1`, nên khi huấn luyện phải ánh xạ `y + 1` (thành `0, 1, 2`) rồi đổi ngược lại khi dự đoán.
- Cột `r_next` được giữ lại trong file đã xử lý để tính backtest, nhưng **không được đưa vào đặc trưng**.

## 4. Đặc trưng

**Nguyên tắc:**
- Không dùng giá thô (`open`, `high`, `low`, `close`) làm đặc trưng. Giá không dừng nên mô hình sẽ học theo mức giá thay vì học hình thái biến động. Mọi đặc trưng đều được chuẩn hoá về dạng tỷ lệ so với giá.
- Đặc trưng tại phiên `t` chỉ dùng dữ liệu đến hết phiên `t`.

### 4.1 Nhóm lõi: các chỉ báo kỹ thuật theo đề bài

| Đặc trưng | Công thức | Tham số |
|---|---|---|
| `close_sma5`, `close_sma10`, `close_sma20` | `close / SMA(close, n) - 1` | n = 5, 10, 20 |
| `sma5_sma20` | `SMA5 / SMA20 - 1` | Tín hiệu giao cắt |
| `close_ema12`, `close_ema26` | `close / EMA(close, n) - 1` | n = 12, 26 |
| `macd` | `(EMA12 - EMA26) / close` | |
| `macd_signal` | `EMA(macd, 9)` | |
| `macd_hist` | `macd - macd_signal` | |
| `rsi14` | RSI theo cách làm mượt Wilder, chia 100 để về khoảng [0, 1] | n = 14 |
| `bb_pctb` | `(close - BB_lower) / (BB_upper - BB_lower)` | SMA20 ± 2σ |
| `bb_width` | `(BB_upper - BB_lower) / SMA20` | |

### 4.2 Nhóm bổ trợ

| Đặc trưng | Công thức |
|---|---|
| `ret_1`, `ret_2`, `ret_3`, `ret_5` | `ln(close[t] / close[t-k])` |
| `body` | `(close - open) / open` |
| `upper_shadow` | `(high - max(open, close)) / close` |
| `lower_shadow` | `(min(open, close) - low) / close` |
| `hl_range` | `(high - low) / close` |
| `volat_5`, `volat_20` | Độ lệch chuẩn của `ret_1` trên cửa sổ 5 và 20 phiên |
| `vol_ratio` | `volume / SMA(volume, 20)` |
| `vol_chg` | `ln(volume[t] / volume[t-1])` |

Tổng cộng có **25 đặc trưng**: 12 thuộc nhóm lõi và 13 thuộc nhóm bổ trợ. Nhóm lõi đáp ứng yêu cầu của đề. Nhóm bổ trợ được đánh giá riêng trong một thí nghiệm so sánh "chỉ nhóm lõi" với "lõi + bổ trợ".

### 4.3 Giai đoạn khởi động (warm-up)

Chỉ báo có cửa sổ dài nhất là `macd_signal`: cần EMA26 rồi thêm EMA9 trên kết quả. Vì vậy **bỏ 35 phiên đầu** của mỗi mã. Sau đó kiểm tra lại để chắc chắn không còn NaN hoặc giá trị vô cực, ví dụ khi `vol_chg` gặp volume bằng 0.

### 4.4 Lọc đặc trưng (tuỳ chọn)

- Bỏ một trong hai đặc trưng có tương quan Pearson > 0.95 trên tập train. Ví dụ `close_sma20` và `bb_pctb` thường tương quan cao.
- Ghi lại feature importance của Random Forest và XGBoost để phân tích trong báo cáo, **không** dùng nó để lọc đặc trưng trên toàn bộ dữ liệu vì như vậy sẽ gây rò rỉ.

## 5. Chia dữ liệu: walk-forward

Mỗi mã được chia riêng, theo cửa sổ mở rộng (expanding window):

```
fold 1: [====== train 750 ======][test 63]
fold 2: [========= train 813 =========][test 63]
fold 3: [============ train 876 ============][test 63]
...
```

| Tham số | Giá trị | Ý nghĩa |
|---|---|---|
| Train ban đầu | 750 phiên | Khoảng 3 năm |
| Khối test | 63 phiên | Khoảng 1 quý |
| Bước dịch | 63 phiên | Các khối test liền nhau, không chồng lấn |
| Khoảng cách (purge) | 1 phiên | Bỏ phiên cuối của train, vì nhãn của nó dùng `close` của phiên test đầu tiên |

Ước tính số fold: TCB khoảng 20, ba mã còn lại khoảng 27.

**Tinh chỉnh siêu tham số:** trong mỗi fold, lấy 20% cuối của tập train (theo thời gian) làm validation. Chọn siêu tham số trên phần này, sau đó huấn luyện lại trên toàn bộ tập train của fold rồi mới dự đoán khối test. Tập test không bao giờ được dùng để chọn bất cứ thứ gì.

## 6. Chuẩn hoá

- **Logistic Regression và SVM:** dùng `StandardScaler`, **fit trên tập train của từng fold** rồi transform tập test của fold đó.
- **Random Forest và XGBoost:** không cần chuẩn hoá.
- Nên đóng gói bằng `sklearn.pipeline.Pipeline` để scaler luôn được fit lại trong từng fold.

## 7. Đầu ra

```
data/processed/1D/<MÃ>.csv
```

| Cột | Vai trò |
|---|---|
| `time` | Chỉ mục thời gian |
| `close` | Dùng cho backtest và vẽ biểu đồ, **không phải đặc trưng** |
| 25 cột đặc trưng (mục 4) | `X` |
| `r_next` | Dùng cho backtest, **không phải đặc trưng** |
| `label` | `y` ∈ {-1, 0, 1} |

Việc chia fold được thực hiện lúc huấn luyện, không lưu sẵn thành file. Cách này giúp thay đổi tham số walk-forward mà không phải chạy lại bước tiền xử lý.

## 8. Liên hệ với bước đánh giá

Bước tiền xử lý phải giữ đủ thông tin để tính các chỉ số mà đề bài yêu cầu:

- **Accuracy, F1:** F1 tính theo macro trên 3 lớp.
- **ROC-AUC:** tính theo one-vs-rest rồi lấy trung bình macro. Cách này cần mô hình xuất xác suất (`predict_proba`). Với SVM thì bật `probability=True`.
- **Backtest:** dùng `label` dự đoán và `r_next`. Quy tắc giao dịch:
  - Dự đoán `1` thì mua hoặc tiếp tục giữ.
  - Dự đoán `-1` thì bán và đứng ngoài.
  - Dự đoán `0` thì giữ nguyên trạng thái hiện tại.

  Đây là chiến lược chỉ mua (long-only), vì thị trường cơ sở Việt Nam không cho bán khống. Chi phí giả định: phí 0.15% mỗi chiều, cộng thuế 0.1% khi bán.
- **Chiến lược cơ sở:**
  - Mua và nắm giữ trên đúng các khối test.
  - Dự đoán ngẫu nhiên theo tỷ lệ lớp của tập train, lặp nhiều lần với các seed khác nhau và lấy trung bình.

## 9. Mở rộng: khung 1H

Áp dụng cùng quy trình cho `data/raw/1H/` (khoảng 2480 nến mỗi mã, 2 năm), với các khác biệt sau:

- Ngưỡng nhãn **θ = 0.2%**, vì độ lệch chuẩn lợi suất giờ chỉ khoảng 0.7–0.8%. Tỷ lệ các lớp xấp xỉ 34% / 38% / 28%.
- Thêm đặc trưng giờ trong ngày và thứ trong tuần, mã hoá dạng sin/cos.
- Thêm cờ `is_first_bar` cho nến đầu phiên. Khi đó `ret_1` của nến đầu phiên chứa cả khoảng gap qua đêm.
- Walk-forward: train ban đầu khoảng 1000 nến, mỗi khối test khoảng 125 nến (khoảng 1 tháng).

## 10. Checklist chống rò rỉ dữ liệu

- [ ] Đặc trưng tại `t` chỉ dùng dữ liệu đến hết phiên `t`. Không có `shift(-k)` nào trong phần tạo đặc trưng.
- [ ] Nhãn và `r_next` là hai cột duy nhất nhìn về tương lai, và cả hai không nằm trong `X`.
- [ ] Mọi phép chia đều theo thời gian. Không xáo trộn dữ liệu, không dùng `train_test_split` ngẫu nhiên.
- [ ] Scaler, lọc đặc trưng và siêu tham số chỉ được fit hoặc chọn trên tập train của từng fold.
- [ ] Có purge 1 phiên giữa train và test.
- [ ] Bỏ nến chưa đóng của ngày hiện tại.
