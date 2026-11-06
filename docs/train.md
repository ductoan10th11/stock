# Huấn luyện và đánh giá

Ghi lại những gì đã làm ở bước huấn luyện (B6 trong [flow.md](flow.md)), kèm số liệu lấy từ `results/1D/`, để dùng viết mục 3.5 và 3.6 của báo cáo. Mọi số liệu dưới đây do `scripts/train_models.py` tạo ra, `random_state = 42`.

Trạng thái: **mô hình ban đầu với siêu tham số cố định** (B6) và **phân tích kết quả** (B7, mục 9). Chưa tinh chỉnh siêu tham số.

## 1. Chạy lại

```bash
.venv/bin/pip install -r requirements.txt
brew install libomp
.venv/bin/python scripts/train_models.py
.venv/bin/python scripts/analyze_results.py
```

`train_models.py` huấn luyện và ghi `results/`. `analyze_results.py` đọc `results/` rồi vẽ hình vào `docs/project-report/bao-cao/images/` và in các bảng ở mục 9.

`libomp` chỉ cần trên macOS, vì XGBoost phụ thuộc vào thư viện này. Thời gian chạy khoảng 3 phút trên máy phát triển. Tham số `--resolution` chọn khung nến, mặc định `1D`.

Đầu ra trong `results/1D/`:

| Tệp | Nội dung |
|---|---|
| `fold_metrics.csv` | Accuracy, F1 macro, ROC-AUC trên tập test và tập train, số phiên train, thời gian huấn luyện của từng mã, mô hình, fold |
| `predictions.csv` | Nhãn thật, nhãn dự đoán, ba xác suất và `r_next` trên từng phiên test |
| `feature_importance.csv` | Độ quan trọng đặc trưng của Random Forest và XGBoost trong từng fold |
| `backtest.csv` | Lợi nhuận, Sharpe, số giao dịch của từng mã và mô hình |
| `summary.csv` | Trung bình và độ lệch chuẩn theo mã và mô hình, kèm dòng `ALL` gộp bốn mã |

## 2. Dữ liệu và chia fold

- Dữ liệu: `data/processed/1D/<mã>.csv`, 25 đặc trưng (12 nhóm lõi, 13 nhóm bổ trợ), nhãn ba lớp với ngưỡng 0,5%.
- Mỗi mã huấn luyện riêng. Chia walk-forward cửa sổ mở rộng bằng hàm `walk_forward_splits` của `preprocess_data.py`: train đầu 750 phiên, mỗi khối test 63 phiên, các khối test liền nhau, bỏ 1 phiên giữa train và test.
- Nhãn mã hóa `label + 1` thành `0, 1, 2` (giảm, ngang, tăng) vì XGBoost yêu cầu nhãn bắt đầu từ 0.

| Mã | Số fold | Khối test đầu | Khối test cuối |
|---|---:|---|---|
| TCB | 20 | 2021-07-22 | 2026-08-10 |
| CTG | 27 | 2019-12-18 | 2026-10-14 |
| VNM | 27 | 2019-12-18 | 2026-10-14 |
| ACB | 27 | 2019-12-16 | 2026-10-19 |

## 3. Mô hình và baseline

| Tên | Cấu hình |
|---|---|
| `logistic` | `StandardScaler` rồi `LogisticRegression(max_iter=1000)`, đóng gói trong `Pipeline`, scaler fit lại trong từng fold |
| `random_forest` | `RandomForestClassifier(n_estimators=300)`, các tham số khác mặc định |
| `xgboost` | `XGBClassifier(n_estimators=300, objective="multi:softprob")`, các tham số khác mặc định |
| `majority` | `DummyClassifier(strategy="most_frequent")`: luôn dự đoán lớp đa số của tập train |
| `random` | Rút nhãn ngẫu nhiên theo tỷ lệ lớp của tập train, lặp 100 lần với seed khác nhau, lấy trung bình |
| `buy_and_hold` | Mua ở đầu giai đoạn test, giữ đến hết. Chỉ có trong backtest |

Các tham số mặc định của Random Forest (cây không giới hạn độ sâu) và XGBoost (`max_depth=6`, `learning_rate=0.3`) chưa được chọn theo dữ liệu. Đây là điểm xuất phát cho mục tối ưu hóa.

## 4. Chỉ số đánh giá

- Accuracy, F1 macro (trung bình ba lớp, tránh bị lớp đông chi phối), ROC-AUC one-vs-rest macro (từ `predict_proba`). Mỗi chỉ số tính trên từng khối test, rồi lấy trung bình và độ lệch chuẩn qua các fold.
- ROC-AUC không định nghĩa cho `random` (không có xác suất), nên để trống. `majority` luôn có ROC-AUC bằng 0,5 vì điểm số không đổi.
- Backtest long-only trên toàn bộ các khối test ghép liền nhau của từng mã:
  - Dự đoán tăng thì mua hoặc giữ, dự đoán giảm thì bán và đứng ngoài, dự đoán ngang thì giữ nguyên trạng thái.
  - Quyết định cuối phiên `t` ăn lợi suất log `r_next` của phiên `t+1`.
  - Phí 0,15% mỗi chiều, thuế 0,1% khi bán. Vị thế còn mở ở cuối giai đoạn được đóng và tính phí bán.
  - Sharpe tính từ lợi suất ngày, nhân căn 252, không trừ lãi suất phi rủi ro.
  - Mua và nắm giữ trả phí một lần mua và một lần bán. Dự đoán ngẫu nhiên lấy trung bình lợi nhuận của 100 lần rút.

## 5. Kết quả

Giá trị trung bình ± độ lệch chuẩn qua các fold. Thời gian là giây huấn luyện trung bình mỗi fold.

### 5.1 Gộp bốn mã

| Mô hình | Accuracy | F1 macro | ROC-AUC | Thời gian (s) |
|---|---|---|---|---:|
| majority | 0,348 ± 0,086 | 0,170 ± 0,032 | 0,500 ± 0,000 | 0,00 |
| random | 0,335 ± 0,010 | 0,324 ± 0,009 | – | 0,00 |
| logistic | 0,388 ± 0,079 | 0,322 ± 0,055 | 0,530 ± 0,059 | 0,01 |
| random_forest | 0,386 ± 0,071 | 0,347 ± 0,060 | 0,538 ± 0,060 | 0,36 |
| xgboost | 0,365 ± 0,068 | 0,342 ± 0,065 | 0,523 ± 0,060 | 1,20 |

### 5.2 Theo từng mã

**TCB**

| Mô hình | Accuracy | F1 macro | ROC-AUC |
|---|---|---|---|
| majority | 0,345 ± 0,063 | 0,170 ± 0,024 | 0,500 ± 0,000 |
| random | 0,334 ± 0,007 | 0,326 ± 0,007 | – |
| logistic | 0,363 ± 0,069 | 0,327 ± 0,055 | 0,521 ± 0,055 |
| random_forest | 0,361 ± 0,061 | 0,336 ± 0,055 | 0,520 ± 0,058 |
| xgboost | 0,340 ± 0,049 | 0,326 ± 0,047 | 0,495 ± 0,059 |

**CTG**

| Mô hình | Accuracy | F1 macro | ROC-AUC |
|---|---|---|---|
| majority | 0,347 ± 0,066 | 0,171 ± 0,023 | 0,500 ± 0,000 |
| random | 0,338 ± 0,013 | 0,325 ± 0,006 | – |
| logistic | 0,387 ± 0,079 | 0,329 ± 0,067 | 0,548 ± 0,060 |
| random_forest | 0,390 ± 0,073 | 0,349 ± 0,049 | 0,555 ± 0,056 |
| xgboost | 0,389 ± 0,074 | 0,363 ± 0,070 | 0,534 ± 0,055 |

**VNM**

| Mô hình | Accuracy | F1 macro | ROC-AUC |
|---|---|---|---|
| majority | 0,365 ± 0,117 | 0,175 ± 0,043 | 0,500 ± 0,000 |
| random | 0,334 ± 0,008 | 0,323 ± 0,009 | – |
| logistic | 0,399 ± 0,081 | 0,322 ± 0,053 | 0,537 ± 0,056 |
| random_forest | 0,412 ± 0,060 | 0,363 ± 0,066 | 0,540 ± 0,049 |
| xgboost | 0,381 ± 0,058 | 0,352 ± 0,058 | 0,537 ± 0,057 |

**ACB**

| Mô hình | Accuracy | F1 macro | ROC-AUC |
|---|---|---|---|
| majority | 0,335 ± 0,083 | 0,165 ± 0,032 | 0,500 ± 0,000 |
| random | 0,333 ± 0,008 | 0,323 ± 0,011 | – |
| logistic | 0,396 ± 0,082 | 0,312 ± 0,046 | 0,513 ± 0,061 |
| random_forest | 0,376 ± 0,081 | 0,337 ± 0,068 | 0,533 ± 0,073 |
| xgboost | 0,345 ± 0,075 | 0,323 ± 0,074 | 0,519 ± 0,063 |

### 5.3 Backtest

Lợi nhuận tích lũy trên toàn bộ giai đoạn test của từng mã / Sharpe / số lần mua. Giai đoạn test của mỗi mã khác nhau (bảng ở mục 2), nên không cộng được giữa các mã.

| Mã | Mua và nắm giữ | majority | random | logistic | random_forest | xgboost |
|---|---|---|---|---|---|---|
| TCB | 30,6% / 0,17 / 1 | -3,5% / -0,02 / 2 | -51,9% / -0,71 / 221 | 5,7% / 0,05 / 138 | -43,1% / -0,43 / 182 | -69,7% / -0,97 / 199 |
| CTG | 226,9% / 0,53 / 1 | 36,4% / 0,23 / 2 | -43,3% / -0,42 / 316 | -41,2% / -0,34 / 268 | 2,1% / 0,01 / 303 | 57,2% / 0,28 / 297 |
| VNM | -18,1% / -0,12 / 1 | 0,0% / – / 0 | -68,3% / -1,01 / 266 | -24,2% / -0,22 / 138 | -12,0% / -0,11 / 177 | -58,1% / -0,72 / 236 |
| ACB | 252,6% / 0,65 / 1 | 252,6% / 0,65 / 1 | -31,8% / -0,34 / 293 | -39,5% / -0,32 / 203 | 27,5% / 0,16 / 215 | -28,0% / -0,22 / 234 |

Với `majority` ở ACB, mô hình luôn dự đoán "tăng" nên giống hệt mua và nắm giữ. Ở VNM, `majority` luôn dự đoán "ngang" nên không bao giờ vào thị trường.

## 6. Nhận xét

Các nhận xét dưới đây chỉ dựa trên số liệu ở mục 5. Phần giải thích nguyên nhân là giả thuyết, cần kiểm tra ở B7.

1. **Khả năng dự đoán yếu.** F1 macro của Random Forest (0,347) và XGBoost (0,342) cao hơn dự đoán ngẫu nhiên (0,324) khoảng 0,02, ROC-AUC chỉ 0,52 đến 0,54. Logistic có F1 macro bằng ngẫu nhiên (0,322) dù Accuracy cao hơn (0,388 so với 0,335). Điều này gợi ý Logistic dự đoán lệch về một vài lớp; cần xem ma trận nhầm lẫn để xác nhận.
2. **Chênh lệch nhỏ so với độ dao động.** Độ lệch chuẩn giữa các fold (khoảng 0,06) lớn hơn khoảng cách giữa mô hình và ngẫu nhiên (khoảng 0,02). Tỷ lệ fold mà F1 macro cao hơn ngẫu nhiên: Random Forest 66%, XGBoost 59%, Logistic 51%. Tỷ lệ fold có ROC-AUC trên 0,5: Random Forest 75%, Logistic 69%, XGBoost 63%. Chưa chạy kiểm định thống kê.
3. **Mô hình ít khác biệt giữa các mã.** CTG và VNM cho kết quả tốt hơn TCB và ACB đôi chút. XGBoost ở TCB có ROC-AUC 0,495, tức không tốt hơn đoán mò.
4. **Backtest không ủng hộ các mô hình.** Ba mô hình học máy giao dịch 138 đến 303 lần trong giai đoạn test, nên phí và thuế ăn phần lớn lợi nhuận, và không mô hình nào trong ba mô hình này thắng mua và nắm giữ ở TCB, CTG và ACB. Ở VNM (thị trường đi xuống, mua và nắm giữ -18,1%) chỉ `majority` (đứng ngoài, 0%) và Random Forest (-12,0%) tốt hơn. Dự đoán ngẫu nhiên lỗ nặng ở cả bốn mã (-32% đến -68%), cho thấy chi phí giao dịch tự nó đã rất lớn với tần suất giao dịch này.
5. **Thời gian huấn luyện** không đáng kể: Logistic 0,01 s, Random Forest 0,36 s, XGBoost 1,20 s mỗi fold.

## 7. Lưu ý khi viết báo cáo

- Đây là **một lần chạy** với siêu tham số mặc định, `random_state = 42`. Không kết luận "mô hình A tốt hơn mô hình B" khi chênh lệch nhỏ hơn độ lệch chuẩn giữa các fold.
- Giai đoạn test của CTG và ACB có xu hướng tăng mạnh (mua và nắm giữ +227% và +253%). Baseline này vì vậy rất khó thắng, và `majority` ở ACB trông tốt chỉ vì thị trường tăng.
- Backtest chưa tính trượt giá, thanh khoản hay quy định T+2 của thị trường Việt Nam. Chỉ nên trình bày như một mô phỏng đơn giản (đúng yêu cầu đề bài).
- Mỗi mã có giai đoạn test khác nhau và độ dài khác nhau (20 hoặc 27 fold), nên dòng "gộp bốn mã" là trung bình theo fold, mỗi fold một phiếu. Mã nhiều fold có trọng số lớn hơn.
- Đề bài yêu cầu thảo luận giới hạn của việc dự đoán giá và nguy cơ quá khớp. Số liệu về quá khớp nằm ở mục 9.

### Ghi chép chất lượng dữ liệu (cho mục 3.3)

Ghi lại các phát hiện khi kiểm tra dữ liệu trước khi huấn luyện:
- Khung 1D sạch. Hai chỗ thiếu phiên do nguồn: CTG và VNM thiếu 2018-01-23 và 2018-01-24; ACB thiếu 2020-12-02 đến 2020-12-08. Ảnh hưởng 3 nhãn, giữ nguyên.
- Khung 30 phút của API hỏng: nến buổi sáng chỉ chứa khoảng 0,5% khối lượng thật, tổng khối lượng cả ngày bằng khoảng 60% khung 1D. Đã dựng lại từ khung 5 phút, tổng khối lượng sau đó khớp 1D (sai lệch dưới 0,4%). Khung này chưa dùng trong huấn luyện.
- Các khung 1, 5, 15 phút chỉ có 63 phiên (2026-07-24 đến 2026-10-23), khung 1H có 497 phiên.

## 8. Chưa làm

Xem B8 đến B13 trong [flow.md](flow.md): ablation đặc trưng, tinh chỉnh siêu tham số, chọn mô hình cuối, thảo luận giới hạn, điền số liệu vào báo cáo.

## 9. Phân tích kết quả (B7)

Mọi số liệu do `scripts/analyze_results.py` in ra, gộp bốn mã, từ cùng một lần chạy ở mục 5. Hình lưu tại `docs/project-report/bao-cao/images/`.

### 9.1 Quá khớp: so sánh tập train và tập test

Hình `overfitting.png`. Trung bình qua các fold:

| Mô hình | F1 macro train | F1 macro test | Chênh | ROC-AUC train | ROC-AUC test | Chênh |
|---|---:|---:|---:|---:|---:|---:|
| Logistic | 0,408 | 0,322 | 0,085 | 0,609 | 0,530 | 0,078 |
| Random Forest | 1,000 | 0,347 | 0,653 | 1,000 | 0,538 | 0,462 |
| XGBoost | 1,000 | 0,342 | 0,658 | 1,000 | 0,523 | 0,477 |

- Random Forest và XGBoost đạt F1 macro và ROC-AUC bằng 1,000 trên tập train ở mọi fold: hai mô hình **thuộc lòng** tập train. Đây là hệ quả của cây không giới hạn độ sâu (Random Forest) và 300 cây với `max_depth=6` (XGBoost) trên dữ liệu có rất ít tín hiệu. Kết quả này là bằng chứng quá khớp nghiêm trọng, và là lý do chính để tinh chỉnh siêu tham số ở B8.
- Logistic có chênh lệch nhỏ (0,085), nhưng F1 macro trên train cũng chỉ 0,408, tức mô hình tuyến tính không học được nhiều từ các đặc trưng này. Đây là dấu hiệu thiếu khả năng biểu diễn hơn là quá khớp.

### 9.2 Ma trận nhầm lẫn

Hình `confusion_matrix.png`. Gộp bốn mã, 6.363 mẫu test. Tỷ lệ theo hàng (nhãn thật), trong ngoặc là số mẫu.

| Mô hình | Giảm đúng | Ngang đúng | Tăng đúng |
|---|---:|---:|---:|
| Logistic | 32,7% (691) | 48,6% (1022) | 35,2% (757) |
| Random Forest | 37,2% (785) | 36,0% (757) | 42,6% (915) |
| XGBoost | 36,4% (769) | 32,9% (692) | 40,2% (864) |

Tỷ lệ nhãn dự đoán so với nhãn thật (giảm / ngang / tăng):

| | Giảm | Ngang | Tăng |
|---|---:|---:|---:|
| Thực tế | 33,2% | 33,0% | 33,8% |
| Logistic | 30,8% | 38,6% | 30,6% |
| Random Forest | 34,8% | 28,1% | 37,1% |
| XGBoost | 34,7% | 27,6% | 37,7% |

- Giả thuyết ở mục 6 về Logistic được xác nhận một phần: Logistic dự đoán "ngang" nhiều hơn thực tế (38,6% so với 33,0%) và chỉ nhận ra lớp "ngang" tốt (48,6%). Hai lớp còn lại gần như đoán ngẫu nhiên (32,7% và 35,2%). Đó là lý do Accuracy cao hơn ngẫu nhiên nhưng F1 macro thì không.
- Random Forest và XGBoost thiên về dự đoán "tăng" (37%) và "giảm" (35%), ít dự đoán "ngang" (28%). Nhận diện "tăng" tốt nhất (42,6% và 40,2%), "ngang" kém nhất. Phần lớn nhầm lẫn là giữa các lớp kề nhau và cả hai hướng ngược nhau, nên mô hình không tách được hướng một cách đáng tin.

### 9.3 Đặc trưng quan trọng

Hình `feature_importance.png`. Độ quan trọng dựa trên mức giảm tạp chất (Random Forest) và độ lợi (XGBoost), chuẩn hóa tổng bằng 1 mỗi fold, rồi trung bình qua các fold và mã.

- Độ quan trọng gần như **phẳng**: 25 đặc trưng, nếu đều nhau thì mỗi đặc trưng 0,040; đặc trưng cao nhất chỉ 0,048 (`atr14` ở cả hai mô hình). Không có đặc trưng nào chi phối.
- Random Forest xếp trên cùng các đặc trưng về biến động và khối lượng: `atr14`, `volat_5`, `vol_chg`, `hl_range`, `vol_ratio`, `volat_20`, `bb_width`. XGBoost xếp `atr14` đầu, sau đó là các đặc trưng giá so với trung bình động (`close_sma20`, `close_sma5`, `close_ema12`, `close_sma10`) và `ret_5`.
- Tỷ trọng nhóm lõi (12 chỉ báo theo đề) so với nhóm bổ trợ (13): Random Forest 43,8% và 56,2%; XGBoost 48,1% và 51,9%. Nếu các đặc trưng đều nhau, nhóm lõi chiếm 12/25 = 48%. Vậy nhóm lõi không quan trọng hơn nhóm bổ trợ; thí nghiệm ablation ở B8 mới cho biết nhóm bổ trợ có thực sự giúp hay không.
- Lưu ý: độ quan trọng kiểu tạp chất thiên về đặc trưng liên tục, nên chỉ dùng để mô tả, không dùng để loại đặc trưng (đúng nguyên tắc chống rò rỉ).

### 9.4 Đường cong học tập

Hình `learning_curve.png`. Mỗi điểm là F1 macro trung bình (gộp mã) ở một fold, làm mượt bằng trung bình trượt 5 fold. Trục ngang là số phiên trong tập train (750 đến 2.400, các fold giống nhau giữa các mã, riêng các fold từ số 21 trở đi không có TCB).

- F1 macro trên train: Random Forest và XGBoost luôn bằng 1,0; Logistic khoảng 0,40 đến 0,42.
- F1 macro trên test **không tăng** khi có thêm dữ liệu huấn luyện: Logistic từ khoảng 0,35 xuống khoảng 0,31; Random Forest từ khoảng 0,37 xuống khoảng 0,34; XGBoost từ khoảng 0,36 xuống khoảng 0,30. Các đường test luôn gần mức ngẫu nhiên (0,324).
- Hiểu theo hướng thận trọng: giới hạn nằm ở lượng tín hiệu trong đặc trưng, không phải ở lượng dữ liệu. Có thể dữ liệu cũ (nhiều năm trước) kém liên quan đến giai đoạn test hơn, nhưng đây là giả thuyết chưa kiểm tra (ví dụ bằng cửa sổ trượt có độ dài cố định).

### 9.5 Ổn định theo thời gian

Hình `f1_by_year.png`. F1 macro trung bình theo năm của khối test (gộp bốn mã):

| Năm | Logistic | Random Forest | XGBoost | Ngẫu nhiên |
|---|---:|---:|---:|---:|
| 2019 | 0,410 | 0,385 | 0,371 | 0,329 |
| 2020 | 0,305 | 0,373 | 0,350 | 0,324 |
| 2021 | 0,344 | 0,337 | 0,345 | 0,326 |
| 2022 | 0,315 | 0,342 | 0,349 | 0,323 |
| 2023 | 0,308 | 0,351 | 0,354 | 0,324 |
| 2024 | 0,304 | 0,340 | 0,345 | 0,322 |
| 2025 | 0,344 | 0,343 | 0,333 | 0,323 |
| 2026 | 0,311 | 0,338 | 0,307 | 0,324 |

- Năm 2019 chỉ có 3 fold (một fold mỗi mã ACB, CTG, VNM, bắt đầu giữa tháng 12/2019), nên số cao ở 2019 không đáng tin. Năm 2026 chưa trọn năm.
- Random Forest cao hơn ngẫu nhiên ở cả bảy năm 2020 đến 2026, nhưng mức hơn chỉ 0,01 đến 0,05. XGBoost hơn ngẫu nhiên trừ 2026 (0,307, thấp hơn 0,324). Logistic thấp hơn ngẫu nhiên ở 2020, 2022, 2023, 2024 và 2026.
- Không thấy xu hướng cải thiện rõ ràng theo thời gian; hiệu năng của cả ba mô hình nằm gần mức ngẫu nhiên và dao động theo năm.

### 9.6 Kết luận cho B8

1. Random Forest và XGBoost cần giới hạn độ phức tạp (độ sâu, số mẫu tối thiểu ở lá, tốc độ học, số cây). Ứng viên đầu tiên cho tinh chỉnh.
2. Logistic cần thử điều chuẩn khác (`C`) và có thể thêm `class_weight`, vì nó lệch về lớp "ngang".
3. Thí nghiệm "chỉ nhóm lõi" so với "lõi + bổ trợ" cần làm vì độ quan trọng không cho thấy nhóm nào vượt trội.
4. Với tín hiệu yếu như vậy, kỳ vọng thực tế là chỉ cải thiện nhỏ. Báo cáo nên đo mức cải thiện bằng độ lệch chuẩn giữa các fold, không chỉ bằng giá trị trung bình.
